"""Helper tools for Control Mapper MCP Server."""

from typing import Dict, List, Any


def calculate_impact_level(factors: List[str]) -> str:
    """
    Calculate impact level based on various factors.

    Args:
        factors: List of impact factors

    Returns:
        Impact level (Low, Moderate, High)
    """
    high_indicators = [
        "life safety",
        "national security",
        "critical infrastructure",
        "secret",
        "top secret",
        "protected c",
    ]

    moderate_indicators = [
        "protected b",
        "financial",
        "personal information",
        "privacy",
        "business critical",
    ]

    factors_lower = [f.lower() for f in factors]

    for indicator in high_indicators:
        if any(indicator in f for f in factors_lower):
            return "High"

    for indicator in moderate_indicators:
        if any(indicator in f for f in factors_lower):
            return "Moderate"

    return "Low"


def get_baseline_controls(profile: int) -> List[str]:
    """
    Get list of baseline control IDs for a given profile.

    Args:
        profile: ITSG-33 profile number (1, 2, or 3)

    Returns:
        List of control IDs
    """
    # Profile 1 baseline controls (Low)
    profile_1_controls = [
        "AC-1", "AC-2", "AC-3", "AC-7", "AC-8", "AC-14", "AC-17", "AC-18", "AC-19", "AC-20",
        "AT-1", "AT-2", "AT-3",
        "AU-1", "AU-2", "AU-3", "AU-4", "AU-5", "AU-6", "AU-8", "AU-9", "AU-11", "AU-12",
        "CA-1", "CA-2", "CA-3", "CA-5", "CA-6", "CA-7",
        "CM-1", "CM-2", "CM-4", "CM-5", "CM-6", "CM-7", "CM-8", "CM-10", "CM-11",
        "CP-1", "CP-2", "CP-3", "CP-4", "CP-9", "CP-10",
        "IA-1", "IA-2", "IA-4", "IA-5", "IA-6", "IA-7", "IA-8",
        "IR-1", "IR-2", "IR-4", "IR-5", "IR-6", "IR-7", "IR-8",
        "MA-1", "MA-2", "MA-3", "MA-4", "MA-5",
        "MP-1", "MP-2", "MP-6", "MP-7",
        "PE-1", "PE-2", "PE-3", "PE-6", "PE-8", "PE-12", "PE-13", "PE-14", "PE-15", "PE-16",
        "PL-1", "PL-2", "PL-4",
        "PS-1", "PS-2", "PS-3", "PS-4", "PS-5", "PS-6", "PS-7", "PS-8",
        "RA-1", "RA-2", "RA-3", "RA-5",
        "SA-1", "SA-2", "SA-3", "SA-4", "SA-5", "SA-8", "SA-9", "SA-10", "SA-11",
        "SC-1", "SC-5", "SC-7", "SC-12", "SC-13", "SC-15", "SC-20", "SC-21", "SC-22",
        "SI-1", "SI-2", "SI-3", "SI-4", "SI-5", "SI-12",
    ]

    # Additional Profile 2 controls (Moderate)
    profile_2_additional = [
        "AC-4", "AC-5", "AC-6", "AC-11", "AC-12", "AC-21",
        "AU-7", "AU-10",
        "CA-8",
        "CM-3", "CM-9",
        "CP-6", "CP-7", "CP-8",
        "IA-3",
        "IR-3",
        "MA-6",
        "MP-3", "MP-4", "MP-5",
        "PE-4", "PE-5", "PE-9", "PE-10", "PE-11",
        "PL-8",
        "SA-12", "SA-15",
        "SC-2", "SC-3", "SC-4", "SC-8", "SC-10", "SC-17", "SC-18", "SC-19", "SC-23", "SC-28",
        "SI-6", "SI-7", "SI-8", "SI-10", "SI-11",
    ]

    # Additional Profile 3 controls (High)
    profile_3_additional = [
        "AC-10", "AC-16",
        "AU-13", "AU-14",
        "CP-11",
        "IA-11",
        "PE-17", "PE-18",
        "SA-16", "SA-17",
        "SC-11", "SC-16", "SC-24", "SC-25",
        "SI-13", "SI-14",
    ]

    if profile == 1:
        return profile_1_controls
    elif profile == 2:
        return profile_1_controls + profile_2_additional
    else:  # profile == 3
        return profile_1_controls + profile_2_additional + profile_3_additional


def get_control_family_for_id(control_id: str) -> str:
    """Extract control family from control ID."""
    return control_id.split("-")[0] if "-" in control_id else control_id[:2]
