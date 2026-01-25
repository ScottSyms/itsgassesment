"""Gap Analyzer MCP Server - Identifies gaps in control implementation."""

from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.utils.gemini_client import GeminiClient

# Initialize FastMCP server
mcp = FastMCP("Gap Analyzer")

# Initialize Gemini client
gemini = GeminiClient()


class Gap(BaseModel):
    """Gap identification result."""

    control_id: str
    gap_type: str = Field(..., description="Implementation, Evidence, or Both")
    severity: str = Field(..., description="Critical, High, Medium, Low")
    description: str
    impact: str
    recommendation: str


@mcp.tool()
async def identify_implementation_gaps(
    control_assessments: List[Dict[str, Any]], profile: int
) -> Dict[str, Any]:
    """
    Identify gaps in control implementation.

    Args:
        control_assessments: List of control assessment results
        profile: ITSG-33 profile number (1, 2, or 3)

    Returns:
        List of identified implementation gaps
    """
    prompt = f"""
    Analyze the following control assessments and identify implementation gaps
    for ITSG-33 Profile {profile}.

    Control Assessments:
    {control_assessments}

    For each gap identified, provide:
    1. Control ID
    2. Gap Type: Implementation (control not implemented) or Evidence (no proof of implementation)
    3. Severity: Critical, High, Medium, or Low based on:
       - Critical: Fundamental security control missing
       - High: Important control missing or significantly deficient
       - Medium: Control partially implemented or evidence incomplete
       - Low: Minor gaps or documentation issues
    4. Description: Clear description of the gap
    5. Impact: Potential security impact if gap is not addressed
    6. Recommendation: Specific remediation steps
    7. Estimated effort: Quick fix, Short-term, Medium-term, Long-term

    Prioritize gaps by severity and potential risk.

    Return as structured JSON array of gaps.
    """

    response = await gemini.generate_async(prompt)
    return {"gaps": response, "profile": profile}


@mcp.tool()
async def analyze_evidence_gaps(
    evidence_mapping: Dict[str, Any], required_controls: List[str]
) -> Dict[str, Any]:
    """
    Analyze gaps in evidence coverage.

    Args:
        evidence_mapping: Mapping of controls to available evidence
        required_controls: List of required control IDs

    Returns:
        Analysis of evidence gaps
    """
    prompt = f"""
    Analyze evidence coverage for ITSG-33 controls and identify documentation gaps.

    Evidence Mapping:
    {evidence_mapping}

    Required Controls:
    {', '.join(required_controls)}

    Identify:
    1. Controls with no evidence
    2. Controls with insufficient evidence
    3. Controls with outdated evidence
    4. Missing evidence types (policies, procedures, configurations, etc.)

    For each gap:
    1. Control ID
    2. Current evidence status
    3. Required evidence types
    4. Specific documents needed
    5. Priority for collection

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {"evidence_gaps": response}


@mcp.tool()
async def prioritize_gaps(gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prioritize identified gaps for remediation.

    Args:
        gaps: List of identified gaps

    Returns:
        Prioritized gap list with remediation roadmap
    """
    prompt = f"""
    Prioritize the following security control gaps for remediation.

    Identified Gaps:
    {gaps}

    Create a prioritized remediation roadmap considering:
    1. Severity of the gap
    2. Potential security impact
    3. Regulatory/compliance implications
    4. Dependencies between gaps
    5. Resource requirements
    6. Quick wins vs long-term efforts

    Group into:
    - Immediate (address within 30 days)
    - Short-term (address within 90 days)
    - Medium-term (address within 180 days)
    - Long-term (address within 1 year)

    Provide:
    1. Prioritized list of gaps
    2. Recommended remediation sequence
    3. Resource estimates
    4. Risk acceptance recommendations for deferred items

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {"prioritized_gaps": response}


@mcp.tool()
async def generate_gap_summary(
    gaps: List[Dict[str, Any]], assessment_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate executive summary of gap analysis.

    Args:
        gaps: List of identified gaps
        assessment_context: Context about the assessment

    Returns:
        Executive summary of gap analysis
    """
    prompt = f"""
    Generate an executive summary of the ITSG-33 gap analysis.

    Assessment Context:
    {assessment_context}

    Identified Gaps:
    {gaps}

    Create an executive summary including:
    1. Overall compliance posture
    2. Summary statistics (total gaps by severity)
    3. Key risk areas
    4. Critical findings requiring immediate attention
    5. Positive findings (well-implemented controls)
    6. Strategic recommendations
    7. Resource implications

    Write in clear, executive-friendly language suitable for senior management.
    Include specific numbers and percentages where applicable.

    Return as structured JSON with sections for each component.
    """

    response = await gemini.generate_async(prompt)
    return {"executive_summary": response}


@mcp.tool()
async def compare_to_baseline(
    current_state: Dict[str, Any], target_profile: int
) -> Dict[str, Any]:
    """
    Compare current implementation state to target ITSG-33 profile baseline.

    Args:
        current_state: Current control implementation state
        target_profile: Target ITSG-33 profile (1, 2, or 3)

    Returns:
        Comparison analysis with gaps to target baseline
    """
    prompt = f"""
    Compare current control implementation state to ITSG-33 Profile {target_profile} baseline.

    Current State:
    {current_state}

    Target: ITSG-33 Profile {target_profile}

    Analyze:
    1. Controls meeting Profile {target_profile} requirements
    2. Controls below Profile {target_profile} requirements
    3. Controls exceeding requirements (potential over-engineering)
    4. Overall readiness percentage for Profile {target_profile}
    5. Effort required to achieve full Profile {target_profile} compliance

    Provide specific recommendations for achieving target profile.

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {"baseline_comparison": response, "target_profile": target_profile}


if __name__ == "__main__":
    mcp.run()
