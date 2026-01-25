"""CLI for running ITSG-33 assessments."""

import asyncio
import sys
import argparse
from pathlib import Path
import httpx


async def create_assessment(
    base_url: str,
    client_id: str,
    project_name: str,
    conops_text: str = None,
) -> str:
    """Create a new assessment."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/assessment/create",
            json={
                "client_id": client_id,
                "project_name": project_name,
                "conops": conops_text,
            },
        )
        response.raise_for_status()
        result = response.json()
        return result["assessment_id"]


async def upload_documents(
    base_url: str,
    assessment_id: str,
    file_paths: list[Path],
) -> dict:
    """Upload documents to assessment."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        files = []
        for file_path in file_paths:
            if file_path.exists():
                files.append(("files", (file_path.name, open(file_path, "rb"))))

        if not files:
            return {"error": "No valid files to upload"}

        response = await client.post(
            f"{base_url}/assessment/{assessment_id}/upload",
            files=files,
        )

        # Close file handles
        for _, (_, fh) in files:
            fh.close()

        response.raise_for_status()
        return response.json()


async def run_assessment(base_url: str, assessment_id: str) -> dict:
    """Start assessment execution."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/assessment/{assessment_id}/run"
        )
        response.raise_for_status()
        return response.json()


async def get_status(base_url: str, assessment_id: str) -> dict:
    """Get assessment status."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/assessment/{assessment_id}/status"
        )
        response.raise_for_status()
        return response.json()


async def get_results(base_url: str, assessment_id: str) -> dict:
    """Get assessment results."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{base_url}/assessment/{assessment_id}/results"
        )
        response.raise_for_status()
        return response.json()


async def wait_for_completion(
    base_url: str,
    assessment_id: str,
    timeout: int = 300,
    poll_interval: int = 5,
) -> dict:
    """Wait for assessment to complete."""
    import time

    start_time = time.time()

    while time.time() - start_time < timeout:
        status = await get_status(base_url, assessment_id)

        if status.get("status") == "completed":
            return await get_results(base_url, assessment_id)
        elif status.get("status") == "error":
            raise Exception(f"Assessment failed: {status}")

        print(f"Status: {status.get('status', 'unknown')}... waiting")
        await asyncio.sleep(poll_interval)

    raise TimeoutError(f"Assessment did not complete within {timeout} seconds")


async def main_async(args):
    """Main async function."""
    base_url = f"http://{args.host}:{args.port}/api/v1"

    print(f"ITSG-33 Assessment CLI")
    print(f"Server: {base_url}")
    print("-" * 50)

    # Read CONOPS if provided
    conops_text = None
    if args.conops:
        conops_path = Path(args.conops)
        if conops_path.exists():
            conops_text = conops_path.read_text()
            print(f"Loaded CONOPS from: {args.conops}")

    # Create assessment
    print(f"\nCreating assessment for client: {args.client_id}")
    assessment_id = await create_assessment(
        base_url,
        args.client_id,
        args.project_name,
        conops_text,
    )
    print(f"Assessment ID: {assessment_id}")

    # Upload documents
    if args.documents:
        print(f"\nUploading {len(args.documents)} documents...")
        doc_paths = [Path(d) for d in args.documents]
        upload_result = await upload_documents(base_url, assessment_id, doc_paths)
        print(f"Uploaded: {upload_result.get('successful', 0)} files")

    # Run assessment
    print("\nStarting assessment...")
    run_result = await run_assessment(base_url, assessment_id)
    print(f"Status: {run_result.get('status', 'unknown')}")

    # Wait for completion if requested
    if args.wait:
        print(f"\nWaiting for completion (timeout: {args.timeout}s)...")
        try:
            results = await wait_for_completion(
                base_url,
                assessment_id,
                timeout=args.timeout,
            )
            print("\nAssessment completed!")
            print("-" * 50)

            # Print summary
            if "phases" in results:
                print("\nPhases completed:")
                for phase, data in results["phases"].items():
                    print(f"  - {phase}: OK")

            print(f"\nFull results available at:")
            print(f"  {base_url}/assessment/{assessment_id}/results")

        except TimeoutError as e:
            print(f"\nTimeout: {e}")
            print(f"Check status at: {base_url}/assessment/{assessment_id}/status")
    else:
        print(f"\nAssessment running in background.")
        print(f"Check status: {base_url}/assessment/{assessment_id}/status")
        print(f"Get results: {base_url}/assessment/{assessment_id}/results")

    return assessment_id


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ITSG-33 Assessment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run assessment with documents
  python run_assessment.py "GOV_DEPT_001" "New System" -c conops.pdf -d doc1.pdf doc2.docx

  # Run and wait for completion
  python run_assessment.py "CLIENT_001" "Project X" -d *.pdf --wait

  # Specify custom server
  python run_assessment.py "CLIENT" "Project" -d docs/ --host localhost --port 8000
        """,
    )

    parser.add_argument(
        "client_id",
        help="Client identifier",
    )
    parser.add_argument(
        "project_name",
        help="Project name",
    )
    parser.add_argument(
        "-c", "--conops",
        help="Path to CONOPS document",
    )
    parser.add_argument(
        "-d", "--documents",
        nargs="+",
        help="Paths to documents to upload",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for assessment to complete",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds when waiting (default: 300)",
    )

    args = parser.parse_args()

    if not args.documents and not args.conops:
        print("Warning: No documents or CONOPS provided. Assessment may be limited.")

    try:
        assessment_id = asyncio.run(main_async(args))
        print(f"\nAssessment ID: {assessment_id}")
    except httpx.ConnectError:
        print(f"\nError: Could not connect to server at {args.host}:{args.port}")
        print("Make sure the server is running: uv run uvicorn src.main:app")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
