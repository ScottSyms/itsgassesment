"""Helper tools for Evidence Assessor MCP Server."""

from typing import Dict, List, Any, Optional
from enum import Enum


class EvidenceType(str, Enum):
    """Types of evidence documents."""

    POLICY = "Policy"
    PROCEDURE = "Procedure"
    STANDARD = "Standard"
    GUIDELINE = "Guideline"
    DIAGRAM = "Diagram"
    CONFIGURATION = "Configuration"
    SCREENSHOT = "Screenshot"
    LOG = "Log"
    REPORT = "Report"
    ATTESTATION = "Attestation"
    CONTRACT = "Contract"
    TRAINING = "Training Record"
    OTHER = "Other"


def classify_evidence_type(filename: str, content: str) -> EvidenceType:
    """
    Classify evidence type based on filename and content.

    Args:
        filename: Name of the file
        content: Content of the file

    Returns:
        Classified evidence type
    """
    filename_lower = filename.lower()
    content_lower = content.lower()[:1000]  # Check first 1000 chars

    # Check filename patterns
    if any(word in filename_lower for word in ["policy", "pol-"]):
        return EvidenceType.POLICY
    if any(word in filename_lower for word in ["procedure", "proc-", "sop"]):
        return EvidenceType.PROCEDURE
    if any(word in filename_lower for word in ["standard", "std-"]):
        return EvidenceType.STANDARD
    if any(word in filename_lower for word in ["diagram", "architecture", "network"]):
        return EvidenceType.DIAGRAM
    if any(word in filename_lower for word in ["config", "settings"]):
        return EvidenceType.CONFIGURATION
    if any(word in filename_lower for word in [".png", ".jpg", ".jpeg", "screenshot"]):
        return EvidenceType.SCREENSHOT
    if any(word in filename_lower for word in ["log", "audit"]):
        return EvidenceType.LOG
    if any(word in filename_lower for word in ["report", "assessment"]):
        return EvidenceType.REPORT
    if any(word in filename_lower for word in ["training", "awareness"]):
        return EvidenceType.TRAINING
    if any(word in filename_lower for word in ["contract", "agreement", "sla"]):
        return EvidenceType.CONTRACT

    # Check content patterns
    if "policy" in content_lower and "shall" in content_lower:
        return EvidenceType.POLICY
    if "procedure" in content_lower and "step" in content_lower:
        return EvidenceType.PROCEDURE

    return EvidenceType.OTHER


def get_expected_evidence_types(control_id: str) -> List[EvidenceType]:
    """
    Get expected evidence types for a given control.

    Args:
        control_id: ITSG-33 control ID

    Returns:
        List of expected evidence types
    """
    family = control_id.split("-")[0] if "-" in control_id else control_id[:2]

    # Default expectations by control family
    family_evidence = {
        "AC": [EvidenceType.POLICY, EvidenceType.PROCEDURE, EvidenceType.CONFIGURATION],
        "AT": [EvidenceType.POLICY, EvidenceType.TRAINING],
        "AU": [EvidenceType.POLICY, EvidenceType.CONFIGURATION, EvidenceType.LOG],
        "CA": [EvidenceType.POLICY, EvidenceType.REPORT],
        "CM": [EvidenceType.POLICY, EvidenceType.PROCEDURE, EvidenceType.CONFIGURATION],
        "CP": [EvidenceType.POLICY, EvidenceType.PROCEDURE],
        "IA": [EvidenceType.POLICY, EvidenceType.CONFIGURATION],
        "IR": [EvidenceType.POLICY, EvidenceType.PROCEDURE],
        "MA": [EvidenceType.POLICY, EvidenceType.PROCEDURE],
        "MP": [EvidenceType.POLICY, EvidenceType.PROCEDURE],
        "PE": [EvidenceType.POLICY, EvidenceType.DIAGRAM],
        "PL": [EvidenceType.POLICY],
        "PS": [EvidenceType.POLICY, EvidenceType.PROCEDURE],
        "RA": [EvidenceType.POLICY, EvidenceType.REPORT],
        "SA": [EvidenceType.POLICY, EvidenceType.CONTRACT],
        "SC": [EvidenceType.POLICY, EvidenceType.CONFIGURATION, EvidenceType.DIAGRAM],
        "SI": [EvidenceType.POLICY, EvidenceType.CONFIGURATION],
    }

    return family_evidence.get(family.upper(), [EvidenceType.POLICY])


def calculate_coverage_score(
    control_count: int, covered_count: int, partial_count: int
) -> float:
    """
    Calculate evidence coverage score.

    Args:
        control_count: Total number of controls
        covered_count: Fully covered controls
        partial_count: Partially covered controls

    Returns:
        Coverage score as percentage
    """
    if control_count == 0:
        return 0.0

    # Full coverage = 100%, Partial = 50%
    score = covered_count + (partial_count * 0.5)
    return round((score / control_count) * 100, 2)
