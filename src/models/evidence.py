"""Data models for evidence and gaps."""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Types of evidence."""

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    DIAGRAM = "Diagram"
    CONFIGURATION = "Configuration"
    SCREENSHOT = "Screenshot"
    LOG = "Log"
    REPORT = "Report"
    ATTESTATION = "Attestation"
    CONTRACT = "Contract"
    TRAINING_RECORD = "Training Record"
    OTHER = "Other"


class Evidence(BaseModel):
    """Evidence item."""

    evidence_id: str = Field(..., description="Unique evidence ID")
    name: str = Field(..., description="Evidence name")
    type: EvidenceType = Field(..., description="Type of evidence")
    description: Optional[str] = Field(None, description="Description")
    file_path: Optional[str] = Field(None, description="Path to evidence file")
    content_summary: Optional[str] = Field(None, description="Summary of content")
    related_controls: List[str] = Field(
        default_factory=list, description="Related control IDs"
    )
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceAssessment(BaseModel):
    """Assessment of evidence for a control."""

    evidence_id: str = Field(..., description="Evidence ID")
    control_id: str = Field(..., description="Control ID")
    relevance: str = Field(..., description="How relevant (High, Medium, Low)")
    sufficiency: str = Field(..., description="How sufficient (Full, Partial, Insufficient)")
    findings: str = Field(..., description="Assessment findings")
    excerpts: List[str] = Field(
        default_factory=list, description="Relevant excerpts from evidence"
    )
    gaps_identified: List[str] = Field(
        default_factory=list, description="Gaps identified in evidence"
    )
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class GapSeverity(str, Enum):
    """Gap severity levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class Gap(BaseModel):
    """Identified gap in control implementation or evidence."""

    gap_id: str = Field(..., description="Unique gap ID")
    control_id: str = Field(..., description="Related control ID")
    control_name: str = Field(..., description="Control name")
    gap_type: str = Field(..., description="Type of gap (Implementation, Evidence, Both)")
    severity: GapSeverity = Field(..., description="Gap severity")
    description: str = Field(..., description="Gap description")
    impact: str = Field(..., description="Potential impact")
    recommendation: str = Field(..., description="Recommended remediation")
    evidence_needed: List[str] = Field(
        default_factory=list, description="Evidence needed to close gap"
    )
    estimated_effort: Optional[str] = Field(None, description="Estimated remediation effort")
    identified_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field("Open", description="Gap status (Open, In Progress, Closed)")


class GapAnalysisResult(BaseModel):
    """Result of gap analysis."""

    assessment_id: str = Field(..., description="Assessment ID")
    total_gaps: int = Field(0, description="Total gaps identified")
    critical_gaps: int = Field(0, description="Critical severity gaps")
    high_gaps: int = Field(0, description="High severity gaps")
    medium_gaps: int = Field(0, description="Medium severity gaps")
    low_gaps: int = Field(0, description="Low severity gaps")
    gaps: List[Gap] = Field(default_factory=list, description="All identified gaps")
    summary: Optional[str] = Field(None, description="Gap analysis summary")
    prioritized_recommendations: List[str] = Field(
        default_factory=list, description="Prioritized recommendations"
    )
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
