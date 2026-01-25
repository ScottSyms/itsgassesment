"""Report Generator MCP Server - Generates assessment reports."""

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.utils.gemini_client import GeminiClient

# Initialize FastMCP server
mcp = FastMCP("Report Generator")

# Initialize Gemini client
gemini = GeminiClient()


@mcp.tool()
async def generate_executive_summary(
    assessment_results: Dict[str, Any],
    client_info: Dict[str, str],
) -> Dict[str, Any]:
    """
    Generate executive summary report.

    Args:
        assessment_results: Complete assessment results
        client_info: Client information

    Returns:
        Executive summary document
    """
    prompt = f"""
    Generate an executive summary for an ITSG-33 security assessment.

    Client Information:
    {client_info}

    Assessment Results:
    {assessment_results}

    Create a professional executive summary including:
    1. Assessment Overview
       - Scope and objectives
       - Assessment methodology
       - Key dates
    2. Overall Security Posture
       - Compliance percentage
       - Risk rating (Critical, High, Moderate, Low)
    3. Key Findings Summary
       - Top 5 critical/high findings
       - Positive findings
    4. Compliance Status by Control Family
       - Brief status for each of the 17 families
    5. Recommendations
       - Top priority actions
       - Strategic recommendations
    6. Conclusion

    Write in professional, executive-friendly language.
    Use clear sections and bullet points for readability.

    Return as structured JSON with markdown-formatted content.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "executive_summary",
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


@mcp.tool()
async def generate_detailed_report(
    assessment_results: Dict[str, Any],
    control_assessments: List[Dict[str, Any]],
    gaps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate detailed technical assessment report.

    Args:
        assessment_results: Overall assessment results
        control_assessments: Individual control assessments
        gaps: Identified gaps

    Returns:
        Detailed technical report
    """
    prompt = f"""
    Generate a detailed technical ITSG-33 assessment report.

    Assessment Overview:
    {assessment_results}

    Control Assessments (sample):
    {control_assessments[:20] if len(control_assessments) > 20 else control_assessments}

    Identified Gaps:
    {gaps}

    Create a comprehensive technical report with:
    1. Introduction
       - Assessment scope
       - Methodology
       - Standards reference (ITSG-33)
    2. System Description
       - Architecture overview
       - Security boundaries
       - Data classification
    3. Control Assessment Details
       - Assessment by control family
       - Implementation status for each control
       - Evidence reviewed
    4. Gap Analysis
       - Detailed gap descriptions
       - Risk implications
       - Remediation recommendations
    5. Compliance Matrix
       - Control-by-control status
    6. Recommendations and Roadmap
       - Prioritized action items
       - Resource requirements
    7. Appendices
       - Evidence list
       - Glossary

    Return as structured JSON with markdown-formatted sections.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "detailed_technical",
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


@mcp.tool()
async def generate_gap_remediation_plan(
    gaps: List[Dict[str, Any]], prioritization: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate gap remediation plan.

    Args:
        gaps: List of identified gaps
        prioritization: Gap prioritization information

    Returns:
        Remediation plan document
    """
    prompt = f"""
    Generate a detailed gap remediation plan for ITSG-33 compliance.

    Identified Gaps:
    {gaps}

    Prioritization:
    {prioritization}

    Create a remediation plan including:
    1. Remediation Overview
       - Total gaps to address
       - Target timeline
       - Resource requirements
    2. Immediate Actions (0-30 days)
       - Critical gaps requiring immediate attention
       - Quick wins
       - Responsible parties
    3. Short-term Actions (30-90 days)
       - High priority gaps
       - Process improvements
    4. Medium-term Actions (90-180 days)
       - Medium priority gaps
       - Policy/procedure updates
    5. Long-term Actions (180+ days)
       - Lower priority gaps
       - Strategic improvements
    6. Resource Plan
       - Personnel requirements
       - Budget considerations
       - External support needs
    7. Progress Tracking
       - Milestones
       - Success metrics
       - Reporting cadence

    For each gap, provide:
    - Specific remediation steps
    - Responsible party
    - Dependencies
    - Success criteria

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "remediation_plan",
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


@mcp.tool()
async def generate_compliance_matrix(
    control_assessments: List[Dict[str, Any]], profile: int
) -> Dict[str, Any]:
    """
    Generate compliance matrix showing status of all controls.

    Args:
        control_assessments: List of control assessments
        profile: ITSG-33 profile number

    Returns:
        Compliance matrix
    """
    prompt = f"""
    Generate a compliance matrix for ITSG-33 Profile {profile}.

    Control Assessments:
    {control_assessments}

    Create a compliance matrix with:
    1. Control Family sections
    2. For each control:
       - Control ID
       - Control Name
       - Implementation Status (Implemented, Partial, Not Implemented, N/A)
       - Evidence References
       - Notes/Findings
    3. Summary statistics per family
    4. Overall compliance percentage

    Format as a structured table suitable for documentation.

    Return as JSON with tabular data.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "compliance_matrix",
        "profile": profile,
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


@mcp.tool()
async def generate_evidence_request_list(
    missing_evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate list of evidence needed from client.

    Args:
        missing_evidence: List of missing or insufficient evidence

    Returns:
        Evidence request document
    """
    prompt = f"""
    Generate an evidence request list for ITSG-33 assessment.

    Missing/Insufficient Evidence:
    {missing_evidence}

    Create a clear evidence request document including:
    1. Introduction explaining the request
    2. For each piece of evidence needed:
       - Related Control ID(s)
       - Evidence Type Required (Policy, Procedure, Configuration, etc.)
       - Specific Description of what's needed
       - Acceptance Criteria
       - Priority (High, Medium, Low)
    3. Submission instructions
    4. Contact information for questions
    5. Deadline recommendations

    Write in clear, professional language suitable for sending to clients.
    Group requests by evidence type for easier collection.

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "evidence_request",
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


@mcp.tool()
async def generate_risk_assessment_summary(
    gaps: List[Dict[str, Any]],
    system_categorization: Dict[str, str]
) -> Dict[str, Any]:
    """
    Generate risk assessment summary based on gaps.

    Args:
        gaps: List of identified gaps
        system_categorization: System security categorization

    Returns:
        Risk assessment summary
    """
    prompt = f"""
    Generate a risk assessment summary for ITSG-33 compliance gaps.

    System Categorization:
    {system_categorization}

    Identified Gaps:
    {gaps}

    Create a risk assessment including:
    1. Risk Overview
       - Overall risk level
       - Risk distribution by severity
    2. Risk Analysis by Control Family
       - Key risks per family
       - Impact assessment
    3. Top Risks
       - Detailed analysis of highest risks
       - Likelihood and impact
       - Potential threat scenarios
    4. Risk Mitigation Status
       - Controls that mitigate risks
       - Residual risk assessment
    5. Recommendations
       - Risk treatment options
       - Prioritized mitigations
    6. Risk Acceptance Considerations
       - Risks that may be accepted
       - Justification requirements

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {
        "report_type": "risk_assessment",
        "generated_at": datetime.utcnow().isoformat(),
        "content": response
    }


if __name__ == "__main__":
    mcp.run()
