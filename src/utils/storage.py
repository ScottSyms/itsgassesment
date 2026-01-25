"""Storage manager for assessment data."""

import os
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiofiles
from fastapi import UploadFile


class StorageManager:
    """Manages storage of assessment data and uploaded files."""

    def __init__(
        self,
        upload_dir: str = "./uploads",
        output_dir: str = "./outputs",
        data_dir: str = "./data"
    ):
        """Initialize storage manager."""
        self.upload_dir = Path(upload_dir)
        self.output_dir = Path(output_dir)
        self.data_dir = Path(data_dir)

        # Create directories
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # In-memory storage (would use database in production)
        self._assessments: Dict[str, Dict[str, Any]] = {}

    async def create_assessment(
        self,
        assessment_id: str,
        client_id: str,
        project_name: str,
        conops: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new assessment record."""
        assessment = {
            "assessment_id": assessment_id,
            "client_id": client_id,
            "project_name": project_name,
            "conops": conops,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "documents": [],
            "diagrams": [],
            "results": None
        }

        self._assessments[assessment_id] = assessment

        # Create assessment directory
        assessment_dir = self.upload_dir / assessment_id
        assessment_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        await self._save_assessment_metadata(assessment_id, assessment)

        return assessment

    async def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment by ID."""
        if assessment_id in self._assessments:
            return self._assessments[assessment_id]

        # Try to load from disk
        metadata_path = self.upload_dir / assessment_id / "metadata.json"
        if metadata_path.exists():
            async with aiofiles.open(metadata_path, "r") as f:
                content = await f.read()
                assessment = json.loads(content)
                self._assessments[assessment_id] = assessment
                return assessment

        return None

    async def save_upload(self, assessment_id: str, file: UploadFile) -> Path:
        """Save uploaded file."""
        assessment_dir = self.upload_dir / assessment_id
        assessment_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        safe_filename = f"{file_id}_{file.filename}"
        file_path = assessment_dir / safe_filename

        # Save file
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Update assessment record
        if assessment_id in self._assessments:
            file_record = {
                "file_id": file_id,
                "filename": file.filename,
                "saved_as": safe_filename,
                "path": str(file_path),
                "content_type": file.content_type,
                "size": len(content),
                "uploaded_at": datetime.utcnow().isoformat()
            }

            # Categorize as document or diagram
            if file.content_type and file.content_type.startswith("image/"):
                self._assessments[assessment_id]["diagrams"].append(file_record)
            else:
                self._assessments[assessment_id]["documents"].append(file_record)

            await self._save_assessment_metadata(
                assessment_id,
                self._assessments[assessment_id]
            )

        return file_path

    async def get_documents(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get all documents for an assessment."""
        assessment = await self.get_assessment(assessment_id)
        if assessment:
            return assessment.get("documents", [])
        return []

    async def get_diagrams(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get all diagrams for an assessment."""
        assessment = await self.get_assessment(assessment_id)
        if assessment:
            return assessment.get("diagrams", [])
        return []

    async def store_results(
        self,
        assessment_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Store assessment results."""
        if assessment_id in self._assessments:
            self._assessments[assessment_id]["results"] = results
            self._assessments[assessment_id]["status"] = "completed"
            self._assessments[assessment_id]["updated_at"] = datetime.utcnow().isoformat()

            await self._save_assessment_metadata(
                assessment_id,
                self._assessments[assessment_id]
            )

            # Save results to separate file
            results_path = self.output_dir / f"{assessment_id}_results.json"
            async with aiofiles.open(results_path, "w") as f:
                await f.write(json.dumps(results, indent=2))

    async def get_status(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment status."""
        assessment = await self.get_assessment(assessment_id)
        if assessment:
            return {
                "assessment_id": assessment_id,
                "status": assessment.get("status"),
                "created_at": assessment.get("created_at"),
                "updated_at": assessment.get("updated_at"),
                "document_count": len(assessment.get("documents", [])),
                "diagram_count": len(assessment.get("diagrams", []))
            }
        return None

    async def get_report(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment report."""
        assessment = await self.get_assessment(assessment_id)
        if assessment and assessment.get("results"):
            return {
                "assessment_id": assessment_id,
                "project_name": assessment.get("project_name"),
                "client_id": assessment.get("client_id"),
                "status": assessment.get("status"),
                "results": assessment.get("results"),
                "generated_at": assessment.get("updated_at")
            }
        return None

    async def _save_assessment_metadata(
        self,
        assessment_id: str,
        assessment: Dict[str, Any]
    ) -> None:
        """Save assessment metadata to disk."""
        metadata_path = self.upload_dir / assessment_id / "metadata.json"
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(assessment, indent=2))

    async def list_assessments(self) -> List[Dict[str, Any]]:
        """List all assessments."""
        assessments = []

        # Check in-memory cache
        for assessment_id, assessment in self._assessments.items():
            assessments.append({
                "assessment_id": assessment_id,
                "project_name": assessment.get("project_name"),
                "client_id": assessment.get("client_id"),
                "status": assessment.get("status"),
                "created_at": assessment.get("created_at")
            })

        # Also check disk for any not in memory
        if self.upload_dir.exists():
            for item in self.upload_dir.iterdir():
                if item.is_dir() and item.name not in self._assessments:
                    metadata_path = item / "metadata.json"
                    if metadata_path.exists():
                        async with aiofiles.open(metadata_path, "r") as f:
                            content = await f.read()
                            assessment = json.loads(content)
                            assessments.append({
                                "assessment_id": item.name,
                                "project_name": assessment.get("project_name"),
                                "client_id": assessment.get("client_id"),
                                "status": assessment.get("status"),
                                "created_at": assessment.get("created_at")
                            })

        return assessments
