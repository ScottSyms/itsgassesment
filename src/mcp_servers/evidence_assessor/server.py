"""Evidence Assessor MCP Server - Evaluates documentation against controls."""

from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.utils.gemini_client import GeminiClient

# Initialize FastMCP server
mcp = FastMCP("Evidence Assessor")

# Initialize Gemini client
gemini = GeminiClient()


class EvidenceAssessment(BaseModel):
    """Evidence assessment result."""

    evidence_id: str
    control_id: str
    relevance: str = Field(..., description="High, Medium, or Low")
    sufficiency: str = Field(..., description="Full, Partial, or Insufficient")
    findings: str
    excerpts: List[str] = []


@mcp.tool()
async def assess_evidence_for_control(
    evidence_content: str,
    evidence_name: str,
    control_id: str,
    control_description: str,
) -> Dict[str, Any]:
    """
    Assess evidence against a specific ITSG-33 control.

    Args:
        evidence_content: Content of the evidence document
        evidence_name: Name of the evidence document
        control_id: ITSG-33 control ID (e.g., AC-1)
        control_description: Description of the control requirement

    Returns:
        Assessment of evidence relevance and sufficiency
    """
    prompt = f"""
    Assess the following evidence document against ITSG-33 control {control_id}.

    Control ID: {control_id}
    Control Requirement: {control_description}

    Evidence Document: {evidence_name}
    Evidence Content:
    {evidence_content[:8000]}  # Limit content length

    Evaluate:
    1. Relevance: How relevant is this evidence to the control? (High, Medium, Low)
    2. Sufficiency: Does this evidence fully address the control? (Full, Partial, Insufficient)
    3. Implementation Status: Based on evidence, what is the implementation status?
       (Implemented, Partially Implemented, Not Implemented, Cannot Determine)
    4. Key Findings: What does this evidence demonstrate?
    5. Gaps: What aspects of the control are not addressed?
    6. Relevant Excerpts: Quote specific text that supports the assessment

    Return as structured JSON with the following format:
    {{
        "control_id": "{control_id}",
        "evidence_name": "{evidence_name}",
        "relevance": "High/Medium/Low",
        "sufficiency": "Full/Partial/Insufficient",
        "implementation_status": "status",
        "findings": "detailed findings",
        "gaps": ["list of gaps"],
        "excerpts": ["relevant quotes from evidence"]
    }}
    """

    response = await gemini.generate_async(prompt)
    return {"assessment": response, "control_id": control_id, "evidence_name": evidence_name}


@mcp.tool()
async def assess_evidence_batch(
    evidence_content: str, evidence_name: str, control_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    Assess evidence against multiple controls.

    Args:
        evidence_content: Content of the evidence document
        evidence_name: Name of the evidence document
        control_ids: List of control IDs to assess against

    Returns:
        List of assessments for each control
    """
    prompt = f"""
    Analyze the following evidence document and assess its relevance to each of the
    listed ITSG-33 controls.

    Evidence Document: {evidence_name}
    Evidence Content:
    {evidence_content[:8000]}

    Controls to assess:
    {', '.join(control_ids)}

    For each control, provide:
    1. Relevance (High, Medium, Low, None)
    2. Sufficiency if relevant (Full, Partial, Insufficient)
    3. Brief finding

    Return as JSON array with one entry per control.
    """

    response = await gemini.generate_async(prompt)
    return [{"batch_assessment": response, "evidence_name": evidence_name}]


@mcp.tool()
async def identify_controls_in_document(document_content: str) -> Dict[str, Any]:
    """
    Identify ITSG-33 controls mentioned or addressed in a document.

    Args:
        document_content: Content of the document to analyze

    Returns:
        List of controls identified with confidence levels
    """
    prompt = f"""
    Analyze the following document and identify all ITSG-33 security controls that are
    mentioned, referenced, or addressed.

    Document Content:
    {document_content[:10000]}

    For each control identified:
    1. Control ID (e.g., AC-1, AU-2)
    2. Control Family
    3. How it's addressed (Explicitly mentioned, Implicitly addressed, Related content)
    4. Confidence level (High, Medium, Low)
    5. Relevant excerpt from document

    Focus on the 17 ITSG-33 control families:
    AC, AT, AU, CA, CM, CP, IA, IR, MA, MP, PE, PL, PS, RA, SA, SC, SI

    Return as structured JSON array.
    """

    response = await gemini.generate_async(prompt)
    return {"identified_controls": response}


@mcp.tool()
async def evaluate_evidence_quality(
    evidence_content: str, evidence_type: str
) -> Dict[str, Any]:
    """
    Evaluate the quality and completeness of evidence.

    Args:
        evidence_content: Content of the evidence
        evidence_type: Type of evidence (Policy, Procedure, Configuration, etc.)

    Returns:
        Quality assessment of the evidence
    """
    prompt = f"""
    Evaluate the quality of this {evidence_type} document as security evidence.

    Document Content:
    {evidence_content[:8000]}

    Assess:
    1. Completeness: Is the document complete? (Complete, Partial, Incomplete)
    2. Currency: Does it appear current/up-to-date? (Current, Dated, Unknown)
    3. Authority: Does it have proper approval/authority? (Approved, Draft, Unknown)
    4. Specificity: Is it specific enough to demonstrate compliance? (Specific, General, Vague)
    5. Traceability: Can findings be traced to specific requirements? (Yes, Partial, No)

    Overall Quality Score: (High, Medium, Low)
    Recommendations for improvement.

    Return as structured JSON.
    """

    response = await gemini.generate_async(prompt)
    return {"quality_assessment": response, "evidence_type": evidence_type}


@mcp.tool()
async def map_evidence_to_controls(
    evidence_list: List[Dict[str, str]], control_list: List[str]
) -> Dict[str, Any]:
    """
    Create a mapping matrix of evidence to controls.

    Args:
        evidence_list: List of evidence items with name and summary
        control_list: List of control IDs

    Returns:
        Mapping matrix showing which evidence supports which controls
    """
    evidence_summaries = "\n".join(
        [f"- {e.get('name', 'Unknown')}: {e.get('summary', '')}" for e in evidence_list]
    )

    prompt = f"""
    Create a mapping matrix showing which evidence documents support which ITSG-33 controls.

    Available Evidence:
    {evidence_summaries}

    Controls to Map:
    {', '.join(control_list)}

    For each control, identify:
    1. Primary evidence (directly addresses the control)
    2. Supporting evidence (partially addresses or supports)
    3. Gaps (no evidence available)

    Return as JSON with control IDs as keys and evidence mappings as values.
    """

    response = await gemini.generate_async(prompt)
    return {"evidence_mapping": response}


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8002)
