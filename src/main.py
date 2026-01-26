"""FastAPI application for ITSG-33 Accreditation System."""

import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.coordinator.agent import ITSG33Coordinator
from src.utils.document_parser import DocumentParser
from src.utils.storage import StorageManager
from src.utils.word_generator import WordReportGenerator

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "static"

# Initialize FastAPI app
app = FastAPI(
    title="ITSG-33 Accreditation System",
    description="AI-powered ITSG-33 security accreditation using multi-agent system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
coordinator = ITSG33Coordinator()
doc_parser = DocumentParser()
storage = StorageManager()
word_generator = WordReportGenerator()


# Request/Response Models
class AssessmentRequest(BaseModel):
    """Assessment request model."""

    client_id: str
    project_name: str
    conops: Optional[str] = None


class AssessmentResponse(BaseModel):
    """Assessment response model."""

    assessment_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Status response model."""

    assessment_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    document_count: int = 0
    diagram_count: int = 0


# Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(content="""
        <html>
            <head><title>ITSG-33 Accreditation System</title></head>
            <body>
                <h1>ITSG-33 Accreditation System</h1>
                <p>Dashboard not found. API available at <a href="/docs">/docs</a></p>
            </body>
        </html>
    """)


@app.get("/api/v1/info")
async def api_info():
    """API info endpoint."""
    return {
        "service": "ITSG-33 Accreditation System",
        "version": "0.1.0",
        "status": "operational",
        "documentation": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "itsg33-accreditation"}


@app.get("/api/v1/status")
async def system_status():
    """Get system status including agent status."""
    coord_status = await coordinator.get_status()
    return {
        "system": "operational",
        "coordinator": coord_status,
        "storage": "operational",
    }


@app.post("/api/v1/assessment/create", response_model=AssessmentResponse)
async def create_assessment(request: AssessmentRequest):
    """Create new ITSG-33 assessment."""
    assessment_id = str(uuid.uuid4())

    await storage.create_assessment(
        assessment_id=assessment_id,
        client_id=request.client_id,
        project_name=request.project_name,
        conops=request.conops,
    )

    return AssessmentResponse(
        assessment_id=assessment_id,
        status="created",
        message="Assessment created successfully. Upload documents to continue.",
    )


@app.post("/api/v1/assessment/{assessment_id}/upload")
async def upload_documents(
    assessment_id: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Upload documents for assessment."""
    # Verify assessment exists
    assessment = await storage.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    uploaded_files = []
    new_documents = []

    for file in files:
        try:
            file_path = await storage.save_upload(assessment_id, file)

            # Parse document
            parsed_content = await doc_parser.parse(file_path)

            file_info = {
                "filename": file.filename,
                "path": str(file_path),
                "content_type": file.content_type,
                "parsed": parsed_content is not None,
                "type": "diagram" if file.content_type and file.content_type.startswith("image/") else "document",
            }

            if parsed_content and "full_text" in parsed_content:
                file_info["content"] = parsed_content["full_text"]
                new_documents.append(file_info)

            uploaded_files.append(file_info)
        except Exception as e:
            uploaded_files.append({
                "filename": file.filename,
                "error": str(e),
                "parsed": False,
            })

    # If assessment has existing results and new documents were added, trigger reassessment
    if assessment.get("results") and new_documents and background_tasks:
        background_tasks.add_task(reassess_with_documents, assessment_id, new_documents)

    return {
        "assessment_id": assessment_id,
        "uploaded_files": uploaded_files,
        "total": len(uploaded_files),
        "successful": len([f for f in uploaded_files if "error" not in f]),
        "will_reassess": bool(assessment.get("results") and new_documents),
    }


async def reassess_with_documents(assessment_id: str, new_documents: List[Dict[str, Any]]):
    """Background task to reassess with new documents."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data or not assessment_data.get("results"):
        return

    results = assessment_data["results"]

    for doc in new_documents:
        results = await coordinator.reassess_with_new_document(results, doc)

    await storage.store_results(assessment_id, results)


@app.post("/api/v1/assessment/{assessment_id}/conops")
async def upload_conops(
    assessment_id: str,
    conops: UploadFile = File(...),
):
    """Upload CONOPS document for assessment."""
    assessment = await storage.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Save and parse CONOPS
    file_path = await storage.save_upload(assessment_id, conops)
    parsed_content = await doc_parser.parse(file_path)

    if parsed_content and "full_text" in parsed_content:
        # Update assessment with CONOPS text
        assessment["conops"] = parsed_content["full_text"]

    return {
        "assessment_id": assessment_id,
        "conops_uploaded": True,
        "filename": conops.filename,
        "parsed": parsed_content is not None,
    }


async def run_assessment_task(assessment_id: str):
    """Background task to run assessment."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        return

    documents = await storage.get_documents(assessment_id)
    diagrams = await storage.get_diagrams(assessment_id)

    # Parse documents to get content
    parsed_docs = []
    for doc in documents:
        if "path" in doc:
            parsed = await doc_parser.parse(Path(doc["path"]))
            if parsed:
                doc["content"] = parsed.get("full_text", "")
        parsed_docs.append(doc)

    # Run assessment
    result = await coordinator.run_assessment(
        conops=assessment_data.get("conops", ""),
        documents=parsed_docs,
        diagrams=diagrams,
        client_id=assessment_data["client_id"],
    )

    # Store results
    await storage.store_results(assessment_id, result)


@app.post("/api/v1/assessment/{assessment_id}/run")
async def run_assessment(
    assessment_id: str,
    background_tasks: BackgroundTasks,
):
    """Execute ITSG-33 assessment."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check if documents uploaded
    documents = await storage.get_documents(assessment_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded. Please upload documents first.",
        )

    # Start assessment in background
    background_tasks.add_task(run_assessment_task, assessment_id)

    return {
        "assessment_id": assessment_id,
        "status": "running",
        "message": "Assessment started. Check status endpoint for progress.",
    }


@app.get("/api/v1/assessment/{assessment_id}/status", response_model=StatusResponse)
async def get_assessment_status(assessment_id: str):
    """Get assessment status."""
    status = await storage.get_status(assessment_id)

    if not status:
        raise HTTPException(status_code=404, detail="Assessment not found")

    return StatusResponse(**status)


@app.get("/api/v1/assessment/{assessment_id}/report")
async def get_assessment_report(assessment_id: str):
    """Get assessment report."""
    report = await storage.get_report(assessment_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found or assessment not completed")

    return report


@app.get("/api/v1/assessment/{assessment_id}/results")
async def get_assessment_results(assessment_id: str):
    """Get full assessment results."""
    assessment = await storage.get_assessment(assessment_id)

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment.get("results"):
        raise HTTPException(
            status_code=400,
            detail="Assessment not completed. Run the assessment first.",
        )

    return assessment["results"]


@app.get("/api/v1/assessments")
async def list_assessments():
    """List all assessments."""
    assessments = await storage.list_assessments()
    return {"assessments": assessments, "total": len(assessments)}


@app.delete("/api/v1/assessment/{assessment_id}")
async def delete_assessment(assessment_id: str):
    """Delete an assessment."""
    assessment = await storage.get_assessment(assessment_id)

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Note: In production, implement actual deletion
    return {
        "assessment_id": assessment_id,
        "status": "deleted",
        "message": "Assessment marked for deletion",
    }


# Control Families endpoint
@app.get("/api/v1/controls/families")
async def get_control_families():
    """Get list of ITSG-33 control families."""
    return {
        "families": [
            {"code": "AC", "name": "Access Control"},
            {"code": "AT", "name": "Awareness and Training"},
            {"code": "AU", "name": "Audit and Accountability"},
            {"code": "CA", "name": "Assessment, Authorization, and Monitoring"},
            {"code": "CM", "name": "Configuration Management"},
            {"code": "CP", "name": "Contingency Planning"},
            {"code": "IA", "name": "Identification and Authentication"},
            {"code": "IR", "name": "Incident Response"},
            {"code": "MA", "name": "Maintenance"},
            {"code": "MP", "name": "Media Protection"},
            {"code": "PE", "name": "Physical and Environmental Protection"},
            {"code": "PL", "name": "Planning"},
            {"code": "PS", "name": "Personnel Security"},
            {"code": "RA", "name": "Risk Assessment"},
            {"code": "SA", "name": "System and Services Acquisition"},
            {"code": "SC", "name": "System and Communications Protection"},
            {"code": "SI", "name": "System and Information Integrity"},
        ]
    }


@app.get("/api/v1/profiles")
async def get_profiles():
    """Get ITSG-33 profile information."""
    return {
        "profiles": [
            {
                "number": 1,
                "name": "Profile 1 - Low",
                "description": "For systems with low sensitivity data and low impact",
            },
            {
                "number": 2,
                "name": "Profile 2 - Moderate",
                "description": "For systems with moderate sensitivity data",
            },
            {
                "number": 3,
                "name": "Profile 3 - High",
                "description": "For systems with high sensitivity data or critical operations",
            },
        ]
    }


@app.post("/api/v1/assessment/{assessment_id}/rerun")
async def rerun_assessment(
    assessment_id: str,
    background_tasks: BackgroundTasks,
):
    """Rerun a completed assessment with any new documents."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Check if documents exist
    documents = await storage.get_documents(assessment_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded. Please upload documents first.",
        )

    # Start assessment in background (will preserve history)
    background_tasks.add_task(run_assessment_task, assessment_id)

    return {
        "assessment_id": assessment_id,
        "status": "running",
        "message": "Assessment rerun started. Previous results will be preserved in history.",
        "previous_runs": len(assessment_data.get("run_history", [])) + (1 if assessment_data.get("results") else 0),
    }


@app.get("/api/v1/assessment/{assessment_id}/history")
async def get_assessment_history(assessment_id: str):
    """Get assessment run history."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    history = assessment_data.get("run_history", [])
    current_run = None

    if assessment_data.get("results"):
        current_run = {
            "run_id": len(history) + 1,
            "completed_at": assessment_data.get("updated_at"),
            "is_current": True,
            "document_count": len(assessment_data.get("documents", [])),
        }

    return {
        "assessment_id": assessment_id,
        "current_run": current_run,
        "history": history,
        "total_runs": len(history) + (1 if current_run else 0),
    }


@app.get("/api/v1/assessment/{assessment_id}/history/{run_id}")
async def get_historical_run(assessment_id: str, run_id: int):
    """Get a specific historical run's results."""
    run = await storage.get_historical_run(assessment_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Historical run not found")

    return run


@app.get("/api/v1/assessment/{assessment_id}/download/word")
async def download_word_report(assessment_id: str):
    """Download assessment report as Word document."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400,
            detail="Assessment not completed. Run the assessment first.",
        )

    # Generate Word document
    doc_buffer = word_generator.generate_assessment_report(
        assessment=assessment_data,
        results=assessment_data["results"],
        project_name=assessment_data.get("project_name", "Unknown"),
        client_id=assessment_data.get("client_id", "Unknown"),
    )

    filename = f"ITSG33_Assessment_{assessment_data.get('project_name', 'Report').replace(' ', '_')}_{assessment_data['assessment_id'][:8]}.docx"

    return StreamingResponse(
        doc_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/v1/assessment/{assessment_id}/download/poam")
async def download_poam(assessment_id: str):
    """Download Plan of Action and Milestones (POA&M) as Word document."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400,
            detail="Assessment not completed. Run the assessment first.",
        )

    # Generate POAM document
    doc_buffer = word_generator.generate_poam(
        assessment=assessment_data,
        results=assessment_data["results"],
        project_name=assessment_data.get("project_name", "Unknown"),
        client_id=assessment_data.get("client_id", "Unknown"),
    )

    filename = f"POAM_{assessment_data.get('project_name', 'Report').replace(' ', '_')}_{assessment_data['assessment_id'][:8]}.docx"

    return StreamingResponse(
        doc_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
