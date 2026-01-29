"""Storage manager for assessment data."""

import os
import json
import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import aiofiles
from fastapi import UploadFile


class StorageManager:
    """Manages storage of assessment data and uploaded files."""

    def __init__(
        self, upload_dir: str = "./uploads", output_dir: str = "./outputs", data_dir: str = "./data"
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
        self, assessment_id: str, client_id: str, project_name: str, conops: Optional[str] = None
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
            "videos": [],
            "results": None,
            "run_history": [],  # Track all assessment runs
            "deleted": False,
            "deleted_at": None,
            "delete_reason": None,
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
                assessment.setdefault("deleted", False)
                assessment.setdefault("deleted_at", None)
                assessment.setdefault("delete_reason", None)
                self._assessments[assessment_id] = assessment
                return assessment

        return None

    async def save_upload(
        self,
        assessment_id: str,
        file: UploadFile,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Save uploaded file using streaming to handle large files."""
        assessment_dir = self.upload_dir / assessment_id
        assessment_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        safe_filename = f"{file_id}_{file.filename}"
        file_path = assessment_dir / safe_filename

        # Save file using chunks to avoid memory issues with large files
        file_size = 0
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                file_size += len(chunk)

        # Update assessment record
        if assessment_id in self._assessments:
            file_record = {
                "file_id": file_id,
                "filename": file.filename,
                "saved_as": safe_filename,
                "path": str(file_path),
                "content_type": file.content_type,
                "size": file_size,
                "uploaded_at": datetime.utcnow().isoformat(),
                "user_metadata": metadata or {},
                "significance_note": (metadata or {}).get("significance_note"),
            }

            # Categorize as document or diagram
            if file.content_type and file.content_type.startswith("image/"):
                self._assessments[assessment_id]["diagrams"].append(file_record)
            elif file.content_type and file.content_type.startswith("video/"):
                # We can add a 'videos' list or keep them in documents for now
                if "videos" not in self._assessments[assessment_id]:
                    self._assessments[assessment_id]["videos"] = []
                self._assessments[assessment_id]["videos"].append(file_record)
            else:
                self._assessments[assessment_id]["documents"].append(file_record)

            await self._save_assessment_metadata(assessment_id, self._assessments[assessment_id])

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

    async def get_videos(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get all videos for an assessment."""
        assessment = await self.get_assessment(assessment_id)
        if assessment:
            return assessment.get("videos", [])
        return []

    async def add_documents(self, assessment_id: str, documents: List[Dict[str, Any]]) -> None:
        """Add document records to an assessment."""
        assessment = await self.get_assessment(assessment_id)
        if not assessment:
            return

        if "documents" not in assessment:
            assessment["documents"] = []

        assessment["documents"].extend(documents)
        assessment["updated_at"] = datetime.utcnow().isoformat()
        await self._save_assessment_metadata(assessment_id, assessment)

    async def update_document_metadata(
        self, assessment_id: str, file_id: str, significance_note: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Update significance note for a single document."""
        assessment = await self.get_assessment(assessment_id)
        if not assessment:
            return None

        collections = ["documents", "diagrams", "videos"]
        for collection in collections:
            items = assessment.get(collection, [])
            for item in items:
                if item.get("file_id") == file_id:
                    item.setdefault("user_metadata", {})
                    item["user_metadata"]["significance_note"] = significance_note
                    item["significance_note"] = significance_note
                    assessment["updated_at"] = datetime.utcnow().isoformat()
                    await self._save_assessment_metadata(assessment_id, assessment)
                    return item

        return None

    async def store_results(
        self, assessment_id: str, results: Dict[str, Any], preserve_history: bool = True
    ) -> None:
        """Store assessment results, optionally preserving history."""
        if assessment_id in self._assessments:
            now = datetime.utcnow().isoformat()

            # Preserve previous run in history if there was one
            if preserve_history and self._assessments[assessment_id].get("results"):
                previous_run = {
                    "run_id": len(self._assessments[assessment_id].get("run_history", [])) + 1,
                    "completed_at": self._assessments[assessment_id].get("updated_at"),
                    "results": self._assessments[assessment_id]["results"],
                    "document_count": len(self._assessments[assessment_id].get("documents", [])),
                }
                if "run_history" not in self._assessments[assessment_id]:
                    self._assessments[assessment_id]["run_history"] = []
                self._assessments[assessment_id]["run_history"].append(previous_run)

            self._assessments[assessment_id]["results"] = results
            self._assessments[assessment_id]["status"] = "completed"
            self._assessments[assessment_id]["updated_at"] = now

            await self._save_assessment_metadata(assessment_id, self._assessments[assessment_id])

            # Save results to separate file
            results_path = self.output_dir / f"{assessment_id}_results.json"
            async with aiofiles.open(results_path, "w") as f:
                await f.write(json.dumps(results, indent=2))

            # Also save timestamped version for history
            history_path = self.output_dir / f"{assessment_id}_results_{now.replace(':', '-')}.json"
            async with aiofiles.open(history_path, "w") as f:
                await f.write(json.dumps(results, indent=2))

    async def get_run_history(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get assessment run history."""
        assessment = await self.get_assessment(assessment_id)
        if assessment:
            return assessment.get("run_history", [])
        return []

    async def get_historical_run(self, assessment_id: str, run_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific historical run."""
        history = await self.get_run_history(assessment_id)
        for run in history:
            if run.get("run_id") == run_id:
                return run
        return None

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
                "diagram_count": len(assessment.get("diagrams", [])),
                "video_count": len(assessment.get("videos", [])),
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
                "generated_at": assessment.get("updated_at"),
            }
        return None

    async def _save_assessment_metadata(
        self, assessment_id: str, assessment: Dict[str, Any]
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
            if assessment.get("deleted"):
                continue
            assessments.append(
                {
                    "assessment_id": assessment_id,
                    "project_name": assessment.get("project_name"),
                    "client_id": assessment.get("client_id"),
                    "status": assessment.get("status"),
                    "created_at": assessment.get("created_at"),
                    "deleted": assessment.get("deleted", False),
                    "deleted_at": assessment.get("deleted_at"),
                }
            )

        # Also check disk for any not in memory
        if self.upload_dir.exists():
            for item in self.upload_dir.iterdir():
                if item.is_dir() and item.name not in self._assessments:
                    metadata_path = item / "metadata.json"
                    if metadata_path.exists():
                        async with aiofiles.open(metadata_path, "r") as f:
                            content = await f.read()
                            assessment = json.loads(content)
                            if assessment.get("deleted"):
                                continue
                            assessments.append(
                                {
                                    "assessment_id": item.name,
                                    "project_name": assessment.get("project_name"),
                                    "client_id": assessment.get("client_id"),
                                    "status": assessment.get("status"),
                                    "created_at": assessment.get("created_at"),
                                    "deleted": assessment.get("deleted", False),
                                    "deleted_at": assessment.get("deleted_at"),
                                }
                            )

        return assessments

    async def list_assessments_with_deleted(self) -> List[Dict[str, Any]]:
        """List all assessments including deleted ones."""
        assessments = []

        for assessment_id, assessment in self._assessments.items():
            assessments.append(
                {
                    "assessment_id": assessment_id,
                    "project_name": assessment.get("project_name"),
                    "client_id": assessment.get("client_id"),
                    "status": assessment.get("status"),
                    "created_at": assessment.get("created_at"),
                    "deleted": assessment.get("deleted", False),
                    "deleted_at": assessment.get("deleted_at"),
                }
            )

        if self.upload_dir.exists():
            for item in self.upload_dir.iterdir():
                if item.is_dir() and item.name not in self._assessments:
                    metadata_path = item / "metadata.json"
                    if metadata_path.exists():
                        async with aiofiles.open(metadata_path, "r") as f:
                            content = await f.read()
                            assessment = json.loads(content)
                            assessments.append(
                                {
                                    "assessment_id": item.name,
                                    "project_name": assessment.get("project_name"),
                                    "client_id": assessment.get("client_id"),
                                    "status": assessment.get("status"),
                                    "created_at": assessment.get("created_at"),
                                    "deleted": assessment.get("deleted", False),
                                    "deleted_at": assessment.get("deleted_at"),
                                }
                            )

        return assessments

    async def soft_delete_assessment(
        self, assessment_id: str, reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Soft delete an assessment."""
        assessment = await self.get_assessment(assessment_id)
        if not assessment:
            return None

        assessment["deleted"] = True
        assessment["deleted_at"] = datetime.utcnow().isoformat()
        assessment["delete_reason"] = reason
        assessment["updated_at"] = datetime.utcnow().isoformat()
        await self._save_assessment_metadata(assessment_id, assessment)
        return assessment

    async def restore_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Restore a soft-deleted assessment."""
        assessment = await self.get_assessment(assessment_id)
        if not assessment:
            return None

        assessment["deleted"] = False
        assessment["deleted_at"] = None
        assessment["delete_reason"] = None
        assessment["updated_at"] = datetime.utcnow().isoformat()
        await self._save_assessment_metadata(assessment_id, assessment)
        return assessment

    async def purge_assessment(self, assessment_id: str) -> bool:
        """Permanently delete an assessment and its files."""
        # Remove from memory
        if assessment_id in self._assessments:
            del self._assessments[assessment_id]

        # Remove uploads directory
        assessment_dir = self.upload_dir / assessment_id
        if assessment_dir.exists():
            shutil.rmtree(assessment_dir, ignore_errors=True)

        # Remove outputs
        if self.output_dir.exists():
            for output_file in self.output_dir.glob(f"{assessment_id}_results*.json"):
                try:
                    output_file.unlink()
                except Exception:
                    pass

        return True

    async def purge_expired_assessments(self, days: int = 30) -> List[str]:
        """Purge assessments that have been soft-deleted longer than the given days."""
        purged = []
        now = datetime.utcnow()

        for assessment in await self.list_assessments_with_deleted():
            if not assessment.get("deleted"):
                continue
            deleted_at = assessment.get("deleted_at")
            if not deleted_at:
                continue
            try:
                deleted_time = datetime.fromisoformat(deleted_at)
            except ValueError:
                continue

            if (now - deleted_time).days >= days:
                await self.purge_assessment(assessment["assessment_id"])
                purged.append(assessment["assessment_id"])

        return purged
