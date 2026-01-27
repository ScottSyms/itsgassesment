"""Data models for evidence and gaps."""

from enum import Enum, IntEnum
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


class EvidenceStrength(IntEnum):
    """Evidence strength ranking (1=strongest, 7=weakest).

    Ranked from strongest to weakest based on auditability and verifiability:
    - Tiers 1-4: Machine-verifiable artifacts (preferred)
    - Tiers 5-7: Human-curated evidence
    """

    SYSTEM_GENERATED = 1       # Logs, audit records, config exports, IAM dumps
    INFRASTRUCTURE_AS_CODE = 2 # Terraform, Helm charts, Ansible, K8s manifests
    AUTOMATED_TEST = 3         # CI pipeline output, SAST/DAST, CIS benchmarks
    CODE_ENFORCEMENT = 4       # Authorization middleware, input validation, crypto
    SCREENSHOT = 5             # Admin console shots, RBAC settings in UI
    VIDEO_WALKTHROUGH = 6      # Demonstrative recordings (non-auditable)
    NARRATIVE = 7              # Written descriptions, attestations


# Evidence strength scores (0-100)
EVIDENCE_STRENGTH_SCORES: Dict[EvidenceStrength, int] = {
    EvidenceStrength.SYSTEM_GENERATED: 100,
    EvidenceStrength.INFRASTRUCTURE_AS_CODE: 90,
    EvidenceStrength.AUTOMATED_TEST: 80,
    EvidenceStrength.CODE_ENFORCEMENT: 70,
    EvidenceStrength.SCREENSHOT: 50,
    EvidenceStrength.VIDEO_WALKTHROUGH: 30,
    EvidenceStrength.NARRATIVE: 20,
}

# Human-readable labels for evidence strength tiers
EVIDENCE_STRENGTH_LABELS: Dict[EvidenceStrength, str] = {
    EvidenceStrength.SYSTEM_GENERATED: "System-Generated",
    EvidenceStrength.INFRASTRUCTURE_AS_CODE: "Infrastructure-as-Code",
    EvidenceStrength.AUTOMATED_TEST: "Automated Test",
    EvidenceStrength.CODE_ENFORCEMENT: "Code Enforcement",
    EvidenceStrength.SCREENSHOT: "Screenshot",
    EvidenceStrength.VIDEO_WALKTHROUGH: "Video Walkthrough",
    EvidenceStrength.NARRATIVE: "Narrative",
}

# Category name to EvidenceStrength mapping
EVIDENCE_CATEGORY_MAP: Dict[str, EvidenceStrength] = {
    "SYSTEM_GENERATED": EvidenceStrength.SYSTEM_GENERATED,
    "INFRASTRUCTURE_AS_CODE": EvidenceStrength.INFRASTRUCTURE_AS_CODE,
    "AUTOMATED_TEST": EvidenceStrength.AUTOMATED_TEST,
    "CODE_ENFORCEMENT": EvidenceStrength.CODE_ENFORCEMENT,
    "SCREENSHOT": EvidenceStrength.SCREENSHOT,
    "VIDEO_WALKTHROUGH": EvidenceStrength.VIDEO_WALKTHROUGH,
    "NARRATIVE": EvidenceStrength.NARRATIVE,
}


def get_strength_score(tier: int) -> int:
    """Get numeric score (0-100) for evidence strength tier."""
    try:
        return EVIDENCE_STRENGTH_SCORES.get(EvidenceStrength(tier), 20)
    except ValueError:
        return 20  # Default to lowest score for invalid tiers


def get_strength_label(tier: int) -> str:
    """Get human-readable label for evidence strength tier."""
    try:
        return EVIDENCE_STRENGTH_LABELS.get(EvidenceStrength(tier), "Unknown")
    except ValueError:
        return "Unknown"


def is_machine_verifiable(tier: int) -> bool:
    """Check if evidence type is machine-verifiable (tiers 1-4)."""
    return 1 <= tier <= 4


def get_strength_from_category(category: str) -> int:
    """Get strength tier from category name."""
    strength = EVIDENCE_CATEGORY_MAP.get(category.upper())
    return strength.value if strength else 7  # Default to NARRATIVE


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
