"""FastAPI application for ITSG-33 Accreditation System."""

import os
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
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

from src.utils.localizer import Localizer

# Initialize components
coordinator = ITSG33Coordinator()
doc_parser = DocumentParser()
storage = StorageManager()
word_generator = WordReportGenerator()
localizer = Localizer()


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
    video_count: int = 0


# Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(
        content="""
        <html>
            <head><title>ITSG-33 Accreditation System</title></head>
            <body>
                <h1>ITSG-33 Accreditation System</h1>
                <p>Dashboard not found. API available at <a href="/docs">/docs</a></p>
            </body>
        </html>
    """
    )


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
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    metadata: Optional[str] = Form(None),
):
    """Upload documents for assessment."""
    # Verify assessment exists
    assessment = await storage.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    uploaded_files = []
    new_documents = []
    metadata_map: Dict[str, Dict[str, Any]] = {}

    if metadata:
        try:
            raw_metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid metadata JSON: {exc}")

        if isinstance(raw_metadata, list):
            for item in raw_metadata:
                if isinstance(item, dict):
                    filename_value = item.get("filename")
                    if isinstance(filename_value, str) and filename_value:
                        metadata_map[filename_value] = item
        elif isinstance(raw_metadata, dict):
            if "files" in raw_metadata and isinstance(raw_metadata["files"], list):
                for item in raw_metadata["files"]:
                    if isinstance(item, dict):
                        filename_value = item.get("filename")
                        if isinstance(filename_value, str) and filename_value:
                            metadata_map[filename_value] = item
            else:
                for key, value in raw_metadata.items():
                    if isinstance(key, str) and key and isinstance(value, dict):
                        metadata_map[key] = {"filename": key, **value}
        else:
            raise HTTPException(status_code=400, detail="Metadata must be a JSON object or array")

    for file in files:
        try:
            filename = file.filename or ""
            user_metadata = metadata_map.get(filename, {})
            file_path = await storage.save_upload(assessment_id, file, metadata=user_metadata)

            # Parse document
            parsed_content = await doc_parser.parse(file_path)

            file_info = {
                "filename": file.filename,
                "path": str(file_path),
                "content_type": file.content_type,
                "parsed": parsed_content is not None,
                "type": "diagram"
                if file.content_type and file.content_type.startswith("image/")
                else (
                    "video"
                    if file.content_type and file.content_type.startswith("video/")
                    else "document"
                ),
                "user_metadata": user_metadata,
            }

            if parsed_content:
                if "full_text" in parsed_content:
                    file_info["content"] = parsed_content["full_text"]
                if "type" in parsed_content:
                    file_info["document_type"] = parsed_content.get("type")
                if "keyframes" in parsed_content:
                    file_info["keyframes"] = parsed_content.get("keyframes")

                if user_metadata.get("declared_type"):
                    file_info["declared_type"] = user_metadata.get("declared_type")
                if user_metadata.get("control_ids"):
                    file_info["user_control_hints"] = user_metadata.get("control_ids")
                if user_metadata.get("explanation") or user_metadata.get("significance_note"):
                    file_info["user_explanation"] = user_metadata.get(
                        "explanation"
                    ) or user_metadata.get("significance_note")
                new_documents.append(file_info)

            uploaded_files.append(file_info)
        except Exception as e:
            uploaded_files.append(
                {
                    "filename": file.filename,
                    "error": str(e),
                    "parsed": False,
                }
            )

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
    videos = await storage.get_videos(assessment_id)

    # Parse documents to get content
    parsed_docs = []
    for doc in documents:
        if "path" in doc:
            parsed = await doc_parser.parse(Path(doc["path"]))
            if parsed:
                doc["content"] = parsed.get("full_text", "")
                doc["document_type"] = parsed.get("type")
        user_metadata = doc.get("user_metadata", {})
        if user_metadata:
            doc["declared_type"] = user_metadata.get("declared_type")
            doc["user_control_hints"] = user_metadata.get("control_ids")
            doc["user_explanation"] = user_metadata.get("explanation") or user_metadata.get(
                "significance_note"
            )
        parsed_docs.append(doc)

    # Parse videos to get keyframes
    parsed_videos = []
    for video in videos:
        if "path" in video:
            parsed = await doc_parser.parse(Path(video["path"]))
            if parsed:
                video.update(parsed)
        user_metadata = video.get("user_metadata", {})
        if user_metadata:
            video["user_explanation"] = user_metadata.get("explanation") or user_metadata.get(
                "significance_note"
            )
        parsed_videos.append(video)

    # Run assessment
    result = await coordinator.run_assessment(
        conops=assessment_data.get("conops", ""),
        documents=parsed_docs,
        diagrams=diagrams,
        videos=parsed_videos,
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


@app.get("/api/v1/controls/families")
async def get_control_families(lang: str = "en"):
    """Get list of ITSG-33 control families."""
    families = [
        {"code": "AC", "en": "Access Control", "fr": "Contrôle d'accès"},
        {"code": "AT", "en": "Awareness and Training", "fr": "Sensibilisation et formation"},
        {"code": "AU", "en": "Audit and Accountability", "fr": "Audit et responsabilité"},
        {
            "code": "CA",
            "en": "Assessment, Authorization, and Monitoring",
            "fr": "Évaluation, autorisation et surveillance",
        },
        {"code": "CM", "en": "Configuration Management", "fr": "Gestion de configuration"},
        {"code": "CP", "en": "Contingency Planning", "fr": "Planification des mesures d'urgence"},
        {
            "code": "IA",
            "en": "Identification and Authentication",
            "fr": "Identification et authentification",
        },
        {"code": "IR", "en": "Incident Response", "fr": "Intervention en cas d'incident"},
        {"code": "MA", "en": "Maintenance", "fr": "Maintenance"},
        {"code": "MP", "en": "Media Protection", "fr": "Protection des supports"},
        {
            "code": "PE",
            "en": "Physical and Environmental Protection",
            "fr": "Protection physique et environnementale",
        },
        {"code": "PL", "en": "Planning", "fr": "Planification"},
        {"code": "PS", "en": "Personnel Security", "fr": "Sécurité du personnel"},
        {"code": "RA", "en": "Risk Assessment", "fr": "Évaluation des risques"},
        {
            "code": "SA",
            "en": "System and Services Acquisition",
            "fr": "Acquisition de systèmes et de services",
        },
        {
            "code": "SC",
            "en": "System and Communications Protection",
            "fr": "Protection des systèmes et des communications",
        },
        {
            "code": "SI",
            "en": "System and Information Integrity",
            "fr": "Intégrité des systèmes et de l'information",
        },
    ]

    return {"families": [{"code": f["code"], "name": f.get(lang, f["en"])} for f in families]}


@app.get("/api/v1/profiles")
async def get_profiles(lang: str = "en"):
    """Get ITSG-33 profile information."""
    profiles = [
        {
            "number": 1,
            "en": {
                "name": "Profile 1 - Low",
                "desc": "For systems with low sensitivity data and low impact",
            },
            "fr": {
                "name": "Profil 1 - Faible",
                "desc": "Pour les systèmes ayant des données à faible sensibilité",
            },
        },
        {
            "number": 2,
            "en": {
                "name": "Profile 2 - Moderate",
                "desc": "For systems with moderate sensitivity data",
            },
            "fr": {
                "name": "Profil 2 - Modéré",
                "desc": "Pour les systèmes ayant des données à sensibilité modérée",
            },
        },
        {
            "number": 3,
            "en": {
                "name": "Profile 3 - High",
                "desc": "For systems with high sensitivity data or critical operations",
            },
            "fr": {
                "name": "Profil 3 - Élevé",
                "desc": "Pour les systèmes ayant des données à haute sensibilité",
            },
        },
    ]

    return {
        "profiles": [
            {
                "number": p["number"],
                "name": p.get(lang, p["en"])["name"],
                "description": p.get(lang, p["en"])["desc"],
            }
            for p in profiles
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
        "previous_runs": len(assessment_data.get("run_history", []))
        + (1 if assessment_data.get("results") else 0),
    }


@app.get("/api/v1/assessment/{assessment_id}/history")
async def get_assessment_history(assessment_id: str):
    """Get assessment run history."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    history = assessment_data.get("run_history", [])
    current_run = None

    # Helper to extract summary from results
    def extract_summary(results):
        if not results:
            return {}
        summary = results.get("summary", {})
        return {
            "total_controls": summary.get("total_controls", 0),
            "controls_with_evidence": summary.get("controls_with_evidence", 0),
            "controls_partial": summary.get("controls_partial", 0),
            "controls_missing": summary.get("controls_missing", 0),
            "coverage_percentage": summary.get("coverage_percentage", 0),
        }

    if assessment_data.get("results"):
        results = assessment_data.get("results", {})
        current_run = {
            "run_id": len(history) + 1,
            "completed_at": assessment_data.get("updated_at"),
            "is_current": True,
            "document_count": len(assessment_data.get("documents", [])),
            **extract_summary(results),
        }

    # Add summary to historical runs
    enriched_history = []
    for run in history:
        enriched_run = {**run}
        enriched_run.update(extract_summary(run.get("results", {})))
        enriched_history.append(enriched_run)

    return {
        "assessment_id": assessment_id,
        "current_run": current_run,
        "history": enriched_history,
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
async def download_word_report(assessment_id: str, lang: str = "en"):
    """Download assessment report as Word document."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400,
            detail="Assessment not completed. Run the assessment first.",
        )

    results = assessment_data["results"]
    if lang != "en":
        results = await localizer.translate_results(results, lang)

    # Generate Word document
    doc_buffer = word_generator.generate_assessment_report(
        assessment=assessment_data,
        results=results,
        project_name=assessment_data.get("project_name", "Unknown"),
        client_id=assessment_data.get("client_id", "Unknown"),
        lang=lang,
    )

    filename = f"ITSG33_Assessment_{assessment_data.get('project_name', 'Report').replace(' ', '_')}_{assessment_data['assessment_id'][:8]}.docx"

    return StreamingResponse(
        doc_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/v1/assessment/{assessment_id}/download/poam")
async def download_poam(assessment_id: str, lang: str = "en"):
    """Download Plan of Action and Milestones (POA&M) as Word document."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400,
            detail="Assessment not completed. Run the assessment first.",
        )

    results = assessment_data["results"]
    if lang != "en":
        results = await localizer.translate_results(results, lang)

    # Generate POAM document
    doc_buffer = word_generator.generate_poam(
        assessment=assessment_data,
        results=results,
        project_name=assessment_data.get("project_name", "Unknown"),
        client_id=assessment_data.get("client_id", "Unknown"),
        lang=lang,
    )

    filename = f"POAM_{assessment_data.get('project_name', 'Report').replace(' ', '_')}_{assessment_data['assessment_id'][:8]}.docx"

    return StreamingResponse(
        doc_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class MarkNotApplicableRequest(BaseModel):
    """Request model for marking a control as not applicable."""

    reason: str


class RejectEvidenceRequest(BaseModel):
    """Request model for rejecting evidence as insufficient."""

    reason: str


@app.post("/api/v1/assessment/{assessment_id}/control/{control_id}/not-applicable")
async def mark_control_not_applicable(
    assessment_id: str,
    control_id: str,
    request: MarkNotApplicableRequest,
):
    """Mark a control as not applicable to this solution (manual override)."""
    if not request.reason or not request.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")

    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400, detail="Assessment not completed. Run the assessment first."
        )

    results = assessment_data["results"]
    coverage = results.get("phases", {}).get("coverage", {})

    # Initialize not_applicable list if it doesn't exist
    if "not_applicable" not in coverage:
        coverage["not_applicable"] = []

    # Find the control in full_coverage, partial_coverage, no_coverage, or rejected_evidence
    control_found = None
    source_list = None

    for list_name in ["full_coverage", "partial_coverage", "no_coverage", "rejected_evidence"]:
        for ctrl in coverage.get(list_name, []):
            if ctrl.get("control_id") == control_id:
                control_found = ctrl.copy()
                source_list = list_name
                break
        if control_found:
            break

    if not control_found:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    # Remove from source list
    coverage[source_list] = [c for c in coverage[source_list] if c.get("control_id") != control_id]

    # Clean up any previous rejection info
    control_found.pop("rejection_reason", None)
    control_found.pop("rejected_from", None)
    control_found.pop("rejected_at", None)

    # Add to not_applicable with reason - mark as manual override
    control_found["not_applicable_reason"] = request.reason.strip()
    control_found["marked_not_applicable_at"] = datetime.utcnow().isoformat()
    control_found["original_status"] = source_list
    control_found["auto_determined"] = False  # Manual override
    coverage["not_applicable"].append(control_found)

    # Recalculate coverage statistics (not_applicable excluded from total)
    total_controls = results.get("summary", {}).get("total_controls", 0)
    not_applicable_count = len(coverage.get("not_applicable", []))
    full_count = len(coverage.get("full_coverage", []))
    partial_count = len(coverage.get("partial_coverage", []))
    rejected_evidence_count = len(coverage.get("rejected_evidence", []))
    no_coverage_count = len(coverage.get("no_coverage", []))

    # Coverage percentage: not_applicable excluded from denominator
    effective_total = total_controls - not_applicable_count
    if effective_total > 0:
        coverage_pct = (full_count + partial_count * 0.5) / effective_total * 100
    else:
        coverage_pct = 0

    coverage["controls_with_evidence"] = full_count
    coverage["controls_partial"] = partial_count
    coverage["controls_missing"] = no_coverage_count
    coverage["controls_rejected_evidence"] = rejected_evidence_count
    coverage["controls_not_applicable"] = not_applicable_count
    coverage["coverage_percentage"] = round(coverage_pct, 1)

    # Update summary
    results["summary"]["controls_with_evidence"] = full_count
    results["summary"]["controls_partial"] = partial_count
    results["summary"]["controls_missing"] = no_coverage_count
    results["summary"]["controls_rejected_evidence"] = rejected_evidence_count
    results["summary"]["controls_not_applicable"] = not_applicable_count
    results["summary"]["coverage_percentage"] = round(coverage_pct, 1)

    await storage.store_results(assessment_id, results, preserve_history=False)

    return {
        "status": "marked_not_applicable",
        "control_id": control_id,
        "message": f"Control {control_id} marked as not applicable",
        "new_coverage_percentage": round(coverage_pct, 1),
    }


@app.post("/api/v1/assessment/{assessment_id}/control/{control_id}/reject-evidence")
async def reject_control_evidence(
    assessment_id: str,
    control_id: str,
    request: RejectEvidenceRequest,
):
    """Reject evidence for a control as insufficient (control remains applicable)."""
    if not request.reason or not request.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")

    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400, detail="Assessment not completed. Run the assessment first."
        )

    results = assessment_data["results"]
    coverage = results.get("phases", {}).get("coverage", {})

    # Initialize rejected_evidence list if it doesn't exist
    if "rejected_evidence" not in coverage:
        coverage["rejected_evidence"] = []

    # Find the control in full_coverage or partial_coverage only (must have evidence to reject)
    control_found = None
    source_list = None

    for list_name in ["full_coverage", "partial_coverage"]:
        for ctrl in coverage.get(list_name, []):
            if ctrl.get("control_id") == control_id:
                control_found = ctrl.copy()
                source_list = list_name
                break
        if control_found:
            break

    if not control_found:
        raise HTTPException(
            status_code=404, detail=f"Control {control_id} not found in controls with evidence"
        )

    # Remove from source list
    coverage[source_list] = [c for c in coverage[source_list] if c.get("control_id") != control_id]

    # Add to rejected_evidence with rejection info
    control_found["rejection_reason"] = request.reason.strip()
    control_found["rejected_from"] = source_list
    control_found["rejected_at"] = datetime.utcnow().isoformat()
    coverage["rejected_evidence"].append(control_found)

    # Recalculate coverage statistics
    total_controls = results.get("summary", {}).get("total_controls", 0)
    not_applicable_count = len(coverage.get("not_applicable", []))
    full_count = len(coverage.get("full_coverage", []))
    partial_count = len(coverage.get("partial_coverage", []))
    rejected_evidence_count = len(coverage.get("rejected_evidence", []))
    no_coverage_count = len(coverage.get("no_coverage", []))

    # Coverage: not_applicable excluded, rejected_evidence counts as needing evidence
    effective_total = total_controls - not_applicable_count
    if effective_total > 0:
        coverage_pct = (full_count + partial_count * 0.5) / effective_total * 100
    else:
        coverage_pct = 0

    coverage["controls_with_evidence"] = full_count
    coverage["controls_partial"] = partial_count
    coverage["controls_missing"] = no_coverage_count
    coverage["controls_rejected_evidence"] = rejected_evidence_count
    coverage["controls_not_applicable"] = not_applicable_count
    coverage["coverage_percentage"] = round(coverage_pct, 1)

    # Update summary
    results["summary"]["controls_with_evidence"] = full_count
    results["summary"]["controls_partial"] = partial_count
    results["summary"]["controls_missing"] = no_coverage_count
    results["summary"]["controls_rejected_evidence"] = rejected_evidence_count
    results["summary"]["controls_not_applicable"] = not_applicable_count
    results["summary"]["coverage_percentage"] = round(coverage_pct, 1)

    await storage.store_results(assessment_id, results, preserve_history=False)

    return {
        "status": "evidence_rejected",
        "control_id": control_id,
        "message": f"Evidence for control {control_id} rejected - needs better documentation",
        "new_coverage_percentage": round(coverage_pct, 1),
    }


@app.post("/api/v1/assessment/{assessment_id}/control/{control_id}/restore")
async def restore_control(assessment_id: str, control_id: str):
    """Restore a control from not_applicable or rejected_evidence back to its original status."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(status_code=400, detail="Assessment not completed.")

    results = assessment_data["results"]
    coverage = results.get("phases", {}).get("coverage", {})

    # Find the control in not_applicable or rejected_evidence
    control_found = None
    source_list = None

    for list_name in ["not_applicable", "rejected_evidence"]:
        for ctrl in coverage.get(list_name, []):
            if ctrl.get("control_id") == control_id:
                control_found = ctrl.copy()
                source_list = list_name
                break
        if control_found:
            break

    if not control_found:
        raise HTTPException(
            status_code=404,
            detail=f"Control {control_id} not found in not applicable or rejected evidence",
        )

    # Remove from source list
    coverage[source_list] = [c for c in coverage[source_list] if c.get("control_id") != control_id]

    # Determine where to restore to
    if source_list == "not_applicable":
        # If it was auto-determined not applicable, restore to no_coverage
        # If it was manually marked, restore to original_status
        was_auto = control_found.get("auto_determined", False)
        if was_auto:
            original_list = "no_coverage"
        else:
            original_list = control_found.get("original_status", "no_coverage")
    else:
        original_list = control_found.get("rejected_from", "partial_coverage")

    # Clean up metadata
    control_found.pop("rejection_reason", None)
    control_found.pop("rejected_from", None)
    control_found.pop("rejected_at", None)
    control_found.pop("not_applicable_reason", None)
    control_found.pop("marked_not_applicable_at", None)
    control_found.pop("original_status", None)
    control_found.pop("auto_determined", None)

    if original_list not in coverage:
        coverage[original_list] = []
    coverage[original_list].append(control_found)

    # Recalculate coverage statistics
    total_controls = results.get("summary", {}).get("total_controls", 0)
    not_applicable_count = len(coverage.get("not_applicable", []))
    full_count = len(coverage.get("full_coverage", []))
    partial_count = len(coverage.get("partial_coverage", []))
    rejected_evidence_count = len(coverage.get("rejected_evidence", []))
    no_coverage_count = len(coverage.get("no_coverage", []))

    effective_total = total_controls - not_applicable_count
    if effective_total > 0:
        coverage_pct = (full_count + partial_count * 0.5) / effective_total * 100
    else:
        coverage_pct = 0

    coverage["controls_with_evidence"] = full_count
    coverage["controls_partial"] = partial_count
    coverage["controls_missing"] = no_coverage_count
    coverage["controls_rejected_evidence"] = rejected_evidence_count
    coverage["controls_not_applicable"] = not_applicable_count
    coverage["coverage_percentage"] = round(coverage_pct, 1)

    # Update summary
    results["summary"]["controls_with_evidence"] = full_count
    results["summary"]["controls_partial"] = partial_count
    results["summary"]["controls_missing"] = no_coverage_count
    results["summary"]["controls_rejected_evidence"] = rejected_evidence_count
    results["summary"]["controls_not_applicable"] = not_applicable_count
    results["summary"]["coverage_percentage"] = round(coverage_pct, 1)

    await storage.store_results(assessment_id, results, preserve_history=False)

    return {
        "status": "restored",
        "control_id": control_id,
        "message": f"Control {control_id} restored to {original_list}",
        "restored_to": original_list,
        "new_coverage_percentage": round(coverage_pct, 1),
    }


@app.get("/api/v1/assessment/{assessment_id}/quality-report")
async def get_evidence_quality_report(assessment_id: str):
    """Get detailed evidence quality analysis with strength distribution."""
    assessment_data = await storage.get_assessment(assessment_id)
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if not assessment_data.get("results"):
        raise HTTPException(
            status_code=400, detail="Assessment not completed. Run the assessment first."
        )

    results = assessment_data["results"]
    coverage = results.get("phases", {}).get("coverage", {})
    summary = results.get("summary", {})

    # Strength labels for the response
    strength_labels = {
        1: "System-Generated",
        2: "Infrastructure-as-Code",
        3: "Automated Test",
        4: "Code Enforcement",
        5: "Screenshot",
        6: "Video Walkthrough",
        7: "Narrative",
    }

    # Aggregate evidence by strength tier
    strength_distribution = {tier: 0 for tier in range(1, 8)}
    machine_verifiable_count = 0
    human_curated_count = 0
    evidence_details = []

    for category in ["full_coverage", "partial_coverage"]:
        for ctrl in coverage.get(category, []):
            for ev in ctrl.get("evidence", []):
                tier = ev.get("evidence", {}).get("evidence_strength_tier", 7)
                # Ensure tier is an integer
                if isinstance(tier, str):
                    try:
                        tier = int(tier)
                    except ValueError:
                        tier = 7
                tier = max(1, min(7, tier))  # Clamp to valid range

                strength_distribution[tier] += 1
                if tier <= 4:
                    machine_verifiable_count += 1
                else:
                    human_curated_count += 1

                evidence_details.append(
                    {
                        "control_id": ctrl.get("control_id"),
                        "document": ev.get("document"),
                        "strength_tier": tier,
                        "strength_label": strength_labels.get(tier, "Unknown"),
                        "coverage": ev.get("evidence", {}).get("coverage", "MENTIONS"),
                        "is_machine_verifiable": tier <= 4,
                    }
                )

    total_evidence = machine_verifiable_count + human_curated_count
    machine_verifiable_ratio = round(machine_verifiable_count / max(total_evidence, 1) * 100, 1)

    return {
        "assessment_id": assessment_id,
        "quality_score": summary.get("quality_score", 0),
        "coverage_percentage": summary.get("coverage_percentage", 0),
        "strength_distribution": {
            strength_labels[tier]: count for tier, count in strength_distribution.items()
        },
        "strength_distribution_raw": strength_distribution,
        "total_evidence_items": total_evidence,
        "machine_verifiable_count": machine_verifiable_count,
        "human_curated_count": human_curated_count,
        "machine_verifiable_ratio": machine_verifiable_ratio,
        "evidence_details": evidence_details,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
