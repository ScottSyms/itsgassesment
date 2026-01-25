"""Data models for ITSG-33 security controls."""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ControlFamily(str, Enum):
    """ITSG-33 Control Families."""

    AC = "AC"  # Access Control
    AT = "AT"  # Awareness and Training
    AU = "AU"  # Audit and Accountability
    CA = "CA"  # Assessment, Authorization, and Monitoring
    CM = "CM"  # Configuration Management
    CP = "CP"  # Contingency Planning
    IA = "IA"  # Identification and Authentication
    IR = "IR"  # Incident Response
    MA = "MA"  # Maintenance
    MP = "MP"  # Media Protection
    PE = "PE"  # Physical and Environmental Protection
    PL = "PL"  # Planning
    PS = "PS"  # Personnel Security
    RA = "RA"  # Risk Assessment
    SA = "SA"  # System and Services Acquisition
    SC = "SC"  # System and Communications Protection
    SI = "SI"  # System and Information Integrity


CONTROL_FAMILY_NAMES = {
    ControlFamily.AC: "Access Control",
    ControlFamily.AT: "Awareness and Training",
    ControlFamily.AU: "Audit and Accountability",
    ControlFamily.CA: "Assessment, Authorization, and Monitoring",
    ControlFamily.CM: "Configuration Management",
    ControlFamily.CP: "Contingency Planning",
    ControlFamily.IA: "Identification and Authentication",
    ControlFamily.IR: "Incident Response",
    ControlFamily.MA: "Maintenance",
    ControlFamily.MP: "Media Protection",
    ControlFamily.PE: "Physical and Environmental Protection",
    ControlFamily.PL: "Planning",
    ControlFamily.PS: "Personnel Security",
    ControlFamily.RA: "Risk Assessment",
    ControlFamily.SA: "System and Services Acquisition",
    ControlFamily.SC: "System and Communications Protection",
    ControlFamily.SI: "System and Information Integrity",
}


class SecurityProfile(int, Enum):
    """ITSG-33 Security Profiles."""

    PROFILE_1 = 1  # Low impact
    PROFILE_2 = 2  # Moderate impact
    PROFILE_3 = 3  # High impact


class Control(BaseModel):
    """ITSG-33 Security Control."""

    id: str = Field(..., description="Control ID (e.g., AC-1, AU-2)")
    name: str = Field(..., description="Control name")
    family: ControlFamily = Field(..., description="Control family")
    description: str = Field(..., description="Control description")
    profile: SecurityProfile = Field(..., description="Minimum profile requiring this control")
    supplemental_guidance: Optional[str] = Field(None, description="Additional guidance")
    related_controls: List[str] = Field(default_factory=list, description="Related control IDs")
    enhancements: List[str] = Field(default_factory=list, description="Control enhancements")
    questions: List[str] = Field(default_factory=list, description="Assessment questions")


class SystemCategorization(BaseModel):
    """System security categorization."""

    confidentiality: str = Field(..., description="Low, Moderate, or High")
    integrity: str = Field(..., description="Low, Moderate, or High")
    availability: str = Field(..., description="Low, Moderate, or High")
    data_classification: str = Field(
        ..., description="Unclassified, Protected A, Protected B, etc."
    )
    business_criticality: str = Field(
        ..., description="Non-critical, Critical, or Mission-critical"
    )
    rationale: Optional[str] = Field(None, description="Rationale for categorization")

    def get_profile(self) -> SecurityProfile:
        """Determine appropriate ITSG-33 profile based on categorization."""
        levels = [
            self.confidentiality.lower(),
            self.integrity.lower(),
            self.availability.lower()
        ]

        if "high" in levels:
            return SecurityProfile.PROFILE_3
        elif "moderate" in levels:
            return SecurityProfile.PROFILE_2
        else:
            return SecurityProfile.PROFILE_1


class ControlMapping(BaseModel):
    """Mapping of a control to a system."""

    control_id: str = Field(..., description="Control ID")
    control_name: str = Field(..., description="Control name")
    control_family: ControlFamily = Field(..., description="Control family")
    baseline: SecurityProfile = Field(..., description="Baseline requirement")
    applicable: bool = Field(True, description="Whether control is applicable")
    rationale: str = Field(..., description="Rationale for applicability determination")
    priority: str = Field("Normal", description="Implementation priority")
    implementation_status: Optional[str] = Field(
        None, description="Current implementation status"
    )
    notes: Optional[str] = Field(None, description="Additional notes")
