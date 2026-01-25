"""Data models for assessments."""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AssessmentStatus(str, Enum):
    """Assessment status values."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    AWAITING_EVIDENCE = "awaiting_evidence"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ImplementationStatus(str, Enum):
    """Control implementation status."""

    IMPLEMENTED = "Implemented"
    PARTIALLY_IMPLEMENTED = "Partially Implemented"
    PLANNED = "Planned"
    NOT_IMPLEMENTED = "Not Implemented"
    NOT_APPLICABLE = "Not Applicable"
    UNKNOWN = "Unknown"


class ControlAssessment(BaseModel):
    """Assessment of a single control."""

    control_id: str = Field(..., description="Control ID")
    control_name: str = Field(..., description="Control name")
    status: ImplementationStatus = Field(..., description="Implementation status")
    evidence_references: List[str] = Field(
        default_factory=list, description="References to supporting evidence"
    )
    findings: Optional[str] = Field(None, description="Assessment findings")
    recommendations: Optional[str] = Field(None, description="Recommendations")
    risk_level: Optional[str] = Field(None, description="Associated risk level")
    assessor_notes: Optional[str] = Field(None, description="Assessor notes")
    assessed_at: Optional[datetime] = Field(None, description="Assessment timestamp")


class AssessmentResult(BaseModel):
    """Complete assessment result."""

    assessment_id: str = Field(..., description="Assessment ID")
    project_name: str = Field(..., description="Project name")
    client_id: str = Field(..., description="Client identifier")
    profile: int = Field(..., description="ITSG-33 profile (1, 2, or 3)")
    total_controls: int = Field(..., description="Total applicable controls")
    implemented_count: int = Field(0, description="Fully implemented controls")
    partial_count: int = Field(0, description="Partially implemented controls")
    not_implemented_count: int = Field(0, description="Not implemented controls")
    compliance_percentage: float = Field(0.0, description="Overall compliance percentage")
    control_assessments: List[ControlAssessment] = Field(
        default_factory=list, description="Individual control assessments"
    )
    gaps: List[Dict[str, Any]] = Field(default_factory=list, description="Identified gaps")
    recommendations: List[str] = Field(
        default_factory=list, description="Overall recommendations"
    )
    executive_summary: Optional[str] = Field(None, description="Executive summary")
    assessed_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_compliance(self) -> float:
        """Calculate compliance percentage."""
        if self.total_controls == 0:
            return 0.0

        # Full implementation = 100%, Partial = 50%
        score = self.implemented_count + (self.partial_count * 0.5)
        return round((score / self.total_controls) * 100, 2)


class Assessment(BaseModel):
    """Assessment record."""

    assessment_id: str = Field(..., description="Unique assessment ID")
    client_id: str = Field(..., description="Client identifier")
    project_name: str = Field(..., description="Project name")
    conops: Optional[str] = Field(None, description="Concept of operations")
    status: AssessmentStatus = Field(
        AssessmentStatus.CREATED, description="Current status"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[Dict[str, Any]] = Field(
        default_factory=list, description="Uploaded documents"
    )
    diagrams: List[Dict[str, Any]] = Field(
        default_factory=list, description="Uploaded diagrams"
    )
    categorization: Optional[Dict[str, Any]] = Field(
        None, description="System categorization"
    )
    result: Optional[AssessmentResult] = Field(None, description="Assessment result")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
