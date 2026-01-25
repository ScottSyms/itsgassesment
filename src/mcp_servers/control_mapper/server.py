"""Control Mapper MCP Server - Identifies applicable ITSG-33 controls."""

import os
from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.utils.gemini_client import GeminiClient

# Initialize FastMCP server
mcp = FastMCP("Control Mapper")

# Initialize Gemini client
gemini = GeminiClient()


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


class ControlMapping(BaseModel):
    """Control mapping result."""

    control_id: str
    control_name: str
    control_family: str
    baseline: str
    rationale: str
    profile_requirement: int


@mcp.tool()
async def categorize_system(
    conops_summary: str, system_description: str, data_types: List[str]
) -> Dict[str, Any]:
    """
    Categorize system based on CONOPS and determine security categorization.

    Args:
        conops_summary: Summary of concept of operations
        system_description: Technical description of the system
        data_types: Types of data processed/stored

    Returns:
        System categorization following ITSG-33 guidelines
    """
    prompt = f"""
    Analyze the following system information and determine the ITSG-33 security categorization.

    CONOPS Summary:
    {conops_summary}

    System Description:
    {system_description}

    Data Types Processed:
    {', '.join(data_types)}

    Based on ITSG-33 guidelines, determine:
    1. Confidentiality level (Low, Moderate, or High)
    2. Integrity level (Low, Moderate, or High)
    3. Availability level (Low, Moderate, or High)
    4. Data classification (Unclassified, Protected A, Protected B, Protected C, Secret, Top Secret)
    5. Business criticality (Non-critical, Critical, Mission-critical)
    6. Recommended ITSG-33 profile (1, 2, or 3)

    Provide detailed rationale for each determination.

    Return your analysis in the following JSON format:
    {{
        "confidentiality": "level",
        "integrity": "level",
        "availability": "level",
        "data_classification": "classification",
        "business_criticality": "criticality",
        "recommended_profile": number,
        "rationale": {{
            "confidentiality_rationale": "explanation",
            "integrity_rationale": "explanation",
            "availability_rationale": "explanation",
            "profile_rationale": "explanation"
        }}
    }}
    """

    response = await gemini.generate_async(prompt)
    return {"raw_response": response, "status": "analyzed"}


@mcp.tool()
async def map_controls_to_system(
    categorization: Dict[str, str], system_characteristics: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Map applicable ITSG-33 controls based on system categorization.

    Args:
        categorization: System security categorization
        system_characteristics: Technical and operational characteristics

    Returns:
        List of applicable controls with rationale
    """
    prompt = f"""
    Based on the following system categorization and characteristics, identify all applicable
    ITSG-33 security controls.

    System Categorization:
    - Confidentiality: {categorization.get('confidentiality', 'Unknown')}
    - Integrity: {categorization.get('integrity', 'Unknown')}
    - Availability: {categorization.get('availability', 'Unknown')}
    - Data Classification: {categorization.get('data_classification', 'Unknown')}

    System Characteristics:
    {system_characteristics}

    For each applicable control, provide:
    1. Control ID (e.g., AC-1, AU-2)
    2. Control Name
    3. Control Family
    4. Baseline Requirement (Profile 1, 2, or 3)
    5. Rationale for applicability
    6. Implementation priority (High, Medium, Low)

    Cover all 17 ITSG-33 control families:
    AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PS, RA, SA, SC, SI

    Return as a JSON array of control mappings.
    """

    response = await gemini.generate_async(prompt)
    return [{"raw_response": response, "status": "mapped"}]


@mcp.tool()
async def determine_profile(categorization: Dict[str, str]) -> Dict[str, Any]:
    """
    Determine appropriate ITSG-33 profile (1, 2, or 3).

    Args:
        categorization: System security categorization

    Returns:
        Profile determination with rationale
    """
    cia_levels = [
        categorization.get("confidentiality", "").lower(),
        categorization.get("integrity", "").lower(),
        categorization.get("availability", "").lower(),
    ]

    if "high" in cia_levels:
        profile = 3
        rationale = "High impact level detected in one or more CIA components"
    elif "moderate" in cia_levels:
        profile = 2
        rationale = "Moderate impact level detected; no high impact components"
    else:
        profile = 1
        rationale = "Low impact across all CIA components"

    return {
        "profile": profile,
        "rationale": rationale,
        "cia_levels": {
            "confidentiality": categorization.get("confidentiality", "Unknown"),
            "integrity": categorization.get("integrity", "Unknown"),
            "availability": categorization.get("availability", "Unknown"),
        },
    }


@mcp.tool()
async def analyze_conops(conops_text: str) -> Dict[str, Any]:
    """
    Analyze CONOPS document to extract security-relevant information.

    Args:
        conops_text: Full text of the CONOPS document

    Returns:
        Extracted security-relevant information
    """
    prompt = f"""
    Analyze the following Concept of Operations (CONOPS) document and extract
    security-relevant information for ITSG-33 assessment.

    CONOPS Document:
    {conops_text[:10000]}  # Limit to first 10000 chars

    Extract and identify:
    1. System purpose and mission
    2. Data types processed/stored
    3. User types and access requirements
    4. Integration points with other systems
    5. Security boundaries
    6. Availability requirements
    7. Compliance requirements mentioned
    8. Risk factors identified

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {"analysis": response, "status": "analyzed"}


if __name__ == "__main__":
    mcp.run()
