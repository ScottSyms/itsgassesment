"""Helper tools for Report Generator MCP Server."""

from typing import Dict, List, Any
from datetime import datetime


def format_date(dt: datetime) -> str:
    """Format datetime for reports."""
    return dt.strftime("%B %d, %Y")


def format_datetime(dt: datetime) -> str:
    """Format datetime with time for reports."""
    return dt.strftime("%B %d, %Y at %H:%M UTC")


def generate_report_header(
    title: str,
    client_name: str,
    project_name: str,
    report_date: datetime
) -> str:
    """
    Generate standard report header.

    Args:
        title: Report title
        client_name: Client name
        project_name: Project name
        report_date: Report date

    Returns:
        Formatted header string
    """
    return f"""
# {title}

**Client:** {client_name}
**Project:** {project_name}
**Report Date:** {format_date(report_date)}
**Assessment Framework:** ITSG-33 (Government of Canada IT Security Standard)

---
"""


def calculate_summary_statistics(
    control_assessments: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate summary statistics for reporting.

    Args:
        control_assessments: List of control assessments

    Returns:
        Summary statistics
    """
    total = len(control_assessments)
    implemented = 0
    partial = 0
    not_implemented = 0
    not_applicable = 0

    for assessment in control_assessments:
        status = assessment.get("status", "").lower()
        if status == "implemented":
            implemented += 1
        elif status in ["partial", "partially implemented"]:
            partial += 1
        elif status in ["not implemented", "not_implemented"]:
            not_implemented += 1
        elif status in ["not applicable", "n/a"]:
            not_applicable += 1

    assessed = total - not_applicable
    if assessed > 0:
        compliance_rate = round(
            ((implemented + partial * 0.5) / assessed) * 100, 1
        )
    else:
        compliance_rate = 0

    return {
        "total_controls": total,
        "implemented": implemented,
        "partial": partial,
        "not_implemented": not_implemented,
        "not_applicable": not_applicable,
        "assessed": assessed,
        "compliance_rate": compliance_rate
    }


def format_control_family_summary(
    family_code: str,
    family_name: str,
    stats: Dict[str, int]
) -> str:
    """
    Format control family summary for reports.

    Args:
        family_code: Control family code
        family_name: Control family name
        stats: Statistics for the family

    Returns:
        Formatted summary string
    """
    total = stats.get("total", 0)
    implemented = stats.get("implemented", 0)
    partial = stats.get("partial", 0)

    if total > 0:
        rate = round(((implemented + partial * 0.5) / total) * 100, 1)
    else:
        rate = 0

    status_emoji = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"

    return f"| {family_code} | {family_name} | {total} | {implemented} | {partial} | {rate}% | {status_emoji} |"


def generate_findings_section(gaps: List[Dict[str, Any]]) -> str:
    """
    Generate findings section for report.

    Args:
        gaps: List of identified gaps

    Returns:
        Formatted findings section
    """
    sections = []

    # Group by severity
    critical = [g for g in gaps if g.get("severity", "").lower() == "critical"]
    high = [g for g in gaps if g.get("severity", "").lower() == "high"]
    medium = [g for g in gaps if g.get("severity", "").lower() == "medium"]
    low = [g for g in gaps if g.get("severity", "").lower() == "low"]

    if critical:
        sections.append("### Critical Findings\n")
        for i, gap in enumerate(critical, 1):
            sections.append(
                f"{i}. **{gap.get('control_id', 'Unknown')}**: {gap.get('description', 'No description')}\n"
            )

    if high:
        sections.append("\n### High Severity Findings\n")
        for i, gap in enumerate(high, 1):
            sections.append(
                f"{i}. **{gap.get('control_id', 'Unknown')}**: {gap.get('description', 'No description')}\n"
            )

    if medium:
        sections.append("\n### Medium Severity Findings\n")
        for i, gap in enumerate(medium, 1):
            sections.append(
                f"{i}. **{gap.get('control_id', 'Unknown')}**: {gap.get('description', 'No description')}\n"
            )

    if low:
        sections.append("\n### Low Severity Findings\n")
        for i, gap in enumerate(low, 1):
            sections.append(
                f"{i}. **{gap.get('control_id', 'Unknown')}**: {gap.get('description', 'No description')}\n"
            )

    return "".join(sections)


CONTROL_FAMILY_NAMES = {
    "AC": "Access Control",
    "AT": "Awareness and Training",
    "AU": "Audit and Accountability",
    "CA": "Assessment, Authorization, and Monitoring",
    "CM": "Configuration Management",
    "CP": "Contingency Planning",
    "IA": "Identification and Authentication",
    "IR": "Incident Response",
    "MA": "Maintenance",
    "MP": "Media Protection",
    "PE": "Physical and Environmental Protection",
    "PL": "Planning",
    "PS": "Personnel Security",
    "RA": "Risk Assessment",
    "SA": "System and Services Acquisition",
    "SC": "System and Communications Protection",
    "SI": "System and Information Integrity",
}
