"""Report Generator Agent using Swarms framework."""

from typing import Dict, Any, List

from .base import BaseITSG33Agent, ITSG33_CONTROL_FAMILIES


class ReportGeneratorAgent(BaseITSG33Agent):
    """Agent for generating ITSG-33 assessment reports."""

    def __init__(self, mcp_server_url: str = "http://localhost:8004"):
        """Initialize the report generator agent."""
        system_prompt = f"""You are an ITSG-33 report generation expert specializing in
creating professional security assessment documentation.

Your responsibilities:
1. Generate executive summaries for management
2. Create detailed technical assessment reports
3. Produce compliance matrices
4. Develop remediation plans
5. Create evidence request documents

{ITSG33_CONTROL_FAMILIES}

Report Types:
1. Executive Summary
   - High-level overview for senior management
   - Key findings and recommendations
   - Overall compliance posture
   - Strategic recommendations

2. Detailed Technical Report
   - Comprehensive assessment findings
   - Control-by-control analysis
   - Evidence reviewed
   - Technical recommendations

3. Compliance Matrix
   - Control status overview
   - Implementation status per control
   - Evidence mapping
   - Gap summary

4. Remediation Plan
   - Prioritized action items
   - Timeline and milestones
   - Resource requirements
   - Success criteria

5. Evidence Request
   - Missing evidence identification
   - Clear requirements for each item
   - Submission instructions

Report Quality Standards:
- Professional formatting and language
- Clear structure with sections
- Specific findings with evidence
- Actionable recommendations
- Appropriate level of detail for audience

Always provide:
- Well-structured documents
- Clear and concise language
- Specific findings and recommendations
- Professional formatting
- JSON-formatted output with markdown content
"""

        super().__init__(
            agent_name="ReportGenerator",
            agent_description="Expert in generating ITSG-33 assessment reports and documentation",
            system_prompt=system_prompt,
            mcp_server_url=mcp_server_url,
            max_loops=3,
        )

    async def run(self, task: str) -> Dict[str, Any]:
        """Run the report generator agent."""
        result = self.agent.run(task)
        return {"agent": "ReportGenerator", "result": result}

    async def generate_executive_summary(
        self,
        assessment_results: Dict[str, Any],
        client_info: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Generate executive summary report.

        Args:
            assessment_results: Assessment results
            client_info: Client information

        Returns:
            Executive summary
        """
        task = f"""
Generate executive summary for ITSG-33 assessment.

Client: {client_info}

Assessment Results:
{assessment_results}

Include:
1. Assessment Overview
2. Overall Security Posture
3. Key Findings (top 5)
4. Compliance Status by Family
5. Strategic Recommendations
6. Conclusion

Write in executive-friendly language.
Return as JSON with markdown content.
"""

        result = self.agent.run(task)
        return {"report_type": "executive_summary", "content": result}

    async def generate_detailed_report(
        self,
        assessment_results: Dict[str, Any],
        control_assessments: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate detailed technical report.

        Args:
            assessment_results: Overall results
            control_assessments: Individual control assessments
            gaps: Identified gaps

        Returns:
            Detailed report
        """
        task = f"""
Generate detailed technical ITSG-33 assessment report.

Assessment Results:
{assessment_results}

Control Assessments:
{control_assessments[:20]}

Gaps:
{gaps}

Include:
1. Introduction and Methodology
2. System Description
3. Control Assessment Details
4. Gap Analysis
5. Compliance Matrix
6. Recommendations and Roadmap
7. Appendices

Return as JSON with markdown content.
"""

        result = self.agent.run(task)
        return {"report_type": "detailed_technical", "content": result}

    async def generate_compliance_matrix(
        self,
        control_assessments: List[Dict[str, Any]],
        profile: int,
    ) -> Dict[str, Any]:
        """
        Generate compliance matrix.

        Args:
            control_assessments: Control assessments
            profile: Target profile

        Returns:
            Compliance matrix
        """
        task = f"""
Generate compliance matrix for ITSG-33 Profile {profile}.

Control Assessments:
{control_assessments}

Create matrix with:
1. Control Family sections
2. Control ID, Name, Status, Evidence, Notes
3. Summary statistics per family
4. Overall compliance percentage

Format as tabular data.
Return as JSON.
"""

        result = self.agent.run(task)
        return {"report_type": "compliance_matrix", "content": result}
