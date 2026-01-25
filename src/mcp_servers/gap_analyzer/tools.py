"""Helper tools for Gap Analyzer MCP Server."""

from typing import Dict, List, Any
from enum import Enum


class GapSeverity(str, Enum):
    """Gap severity levels."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class GapType(str, Enum):
    """Types of gaps."""

    IMPLEMENTATION = "Implementation"
    EVIDENCE = "Evidence"
    BOTH = "Both"


def calculate_severity(
    control_family: str,
    implementation_status: str,
    data_sensitivity: str
) -> GapSeverity:
    """
    Calculate gap severity based on various factors.

    Args:
        control_family: Control family code
        implementation_status: Current implementation status
        data_sensitivity: Data sensitivity level

    Returns:
        Calculated severity level
    """
    # Critical control families
    critical_families = ["AC", "IA", "AU", "SC"]

    # Determine base severity from implementation status
    if implementation_status.lower() == "not implemented":
        base_severity = GapSeverity.HIGH
    elif implementation_status.lower() == "partially implemented":
        base_severity = GapSeverity.MEDIUM
    else:
        base_severity = GapSeverity.LOW

    # Elevate severity for critical families
    if control_family.upper() in critical_families:
        if base_severity == GapSeverity.HIGH:
            return GapSeverity.CRITICAL
        elif base_severity == GapSeverity.MEDIUM:
            return GapSeverity.HIGH

    # Elevate severity for high sensitivity data
    if data_sensitivity.lower() in ["high", "protected c", "secret", "top secret"]:
        if base_severity == GapSeverity.HIGH:
            return GapSeverity.CRITICAL
        elif base_severity == GapSeverity.MEDIUM:
            return GapSeverity.HIGH
        elif base_severity == GapSeverity.LOW:
            return GapSeverity.MEDIUM

    return base_severity


def categorize_gap(gap: Dict[str, Any]) -> Dict[str, str]:
    """
    Categorize a gap for reporting purposes.

    Args:
        gap: Gap information

    Returns:
        Categorization details
    """
    severity = gap.get("severity", "Medium")
    gap_type = gap.get("gap_type", "Implementation")

    # Determine timeline
    if severity == "Critical":
        timeline = "Immediate"
        priority = 1
    elif severity == "High":
        timeline = "Short-term"
        priority = 2
    elif severity == "Medium":
        timeline = "Medium-term"
        priority = 3
    else:
        timeline = "Long-term"
        priority = 4

    # Determine effort estimate
    if gap_type == "Evidence":
        effort = "Low"  # Documentation typically easier
    elif gap_type == "Both":
        effort = "High"
    else:
        effort = "Medium"

    return {
        "timeline": timeline,
        "priority": priority,
        "effort_estimate": effort,
    }


def aggregate_gaps_by_family(gaps: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Aggregate gaps by control family.

    Args:
        gaps: List of gaps

    Returns:
        Gaps grouped by control family
    """
    grouped = {}

    for gap in gaps:
        control_id = gap.get("control_id", "")
        family = control_id.split("-")[0] if "-" in control_id else "Unknown"

        if family not in grouped:
            grouped[family] = []
        grouped[family].append(gap)

    return grouped


def calculate_compliance_score(
    total_controls: int,
    implemented: int,
    partial: int,
    not_implemented: int
) -> Dict[str, Any]:
    """
    Calculate overall compliance score.

    Args:
        total_controls: Total number of applicable controls
        implemented: Fully implemented controls
        partial: Partially implemented controls
        not_implemented: Not implemented controls

    Returns:
        Compliance score details
    """
    if total_controls == 0:
        return {
            "score": 0,
            "percentage": 0,
            "status": "No controls assessed"
        }

    # Full = 100%, Partial = 50%
    score = implemented + (partial * 0.5)
    percentage = round((score / total_controls) * 100, 2)

    # Determine status
    if percentage >= 90:
        status = "Excellent"
    elif percentage >= 75:
        status = "Good"
    elif percentage >= 60:
        status = "Acceptable"
    elif percentage >= 40:
        status = "Needs Improvement"
    else:
        status = "Critical"

    return {
        "score": score,
        "percentage": percentage,
        "status": status,
        "breakdown": {
            "implemented": implemented,
            "partial": partial,
            "not_implemented": not_implemented,
            "total": total_controls
        }
    }
