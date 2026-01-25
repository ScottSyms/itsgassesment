"""Evidence Assessor Agent using Swarms framework."""

from typing import Dict, Any, List

from .base import BaseITSG33Agent, ITSG33_CONTROL_FAMILIES


class EvidenceAssessorAgent(BaseITSG33Agent):
    """Agent for assessing evidence against ITSG-33 controls."""

    def __init__(self, mcp_server_url: str = "http://localhost:8002"):
        """Initialize the evidence assessor agent."""
        system_prompt = f"""You are an ITSG-33 evidence assessment expert specializing in
evaluating security documentation against control requirements.

Your responsibilities:
1. Analyze submitted documentation (policies, procedures, configurations, etc.)
2. Map evidence to specific ITSG-33 controls
3. Assess evidence quality and sufficiency
4. Identify gaps in documentation
5. Determine implementation status based on evidence

{ITSG33_CONTROL_FAMILIES}

Evidence Types to Consider:
- Policies: High-level security policies
- Procedures: Operational procedures and processes
- Standards: Technical standards and guidelines
- Configurations: System configuration documentation
- Diagrams: Architecture and network diagrams
- Screenshots: System screenshots showing configurations
- Logs: Audit logs and monitoring records
- Reports: Security assessment and audit reports
- Training Records: Security awareness training records
- Contracts: Service agreements and security clauses

Assessment Criteria:
1. Relevance: Does the evidence relate to the control?
2. Sufficiency: Does it fully address control requirements?
3. Currency: Is the evidence current and up-to-date?
4. Authority: Is it properly approved/authorized?
5. Specificity: Is it specific enough to demonstrate compliance?

Always provide:
- Clear assessment with supporting rationale
- Relevant excerpts from evidence
- Gap identification where evidence is insufficient
- Recommendations for additional evidence needed
- JSON-formatted output
"""

        super().__init__(
            agent_name="EvidenceAssessor",
            agent_description="Expert in evaluating security evidence against ITSG-33 controls",
            system_prompt=system_prompt,
            mcp_server_url=mcp_server_url,
            max_loops=3,
        )

    async def run(self, task: str) -> Dict[str, Any]:
        """Run the evidence assessor agent."""
        result = self.agent.run(task)
        return {"agent": "EvidenceAssessor", "result": result}

    async def assess_document(
        self,
        document_content: str,
        document_name: str,
        target_controls: List[str],
    ) -> Dict[str, Any]:
        """
        Assess a document against target controls.

        Args:
            document_content: Content of the document
            document_name: Name of the document
            target_controls: List of control IDs to assess against

        Returns:
            Assessment results
        """
        task = f"""
Assess this document against ITSG-33 controls.

Document: {document_name}
Content:
{document_content[:8000]}

Target Controls: {', '.join(target_controls)}

For each control:
1. Relevance (High, Medium, Low, None)
2. Sufficiency (Full, Partial, Insufficient)
3. Implementation status indicated
4. Key findings and excerpts
5. Gaps identified

Return as JSON with assessment for each control.
"""

        result = self.agent.run(task)
        return {"document": document_name, "assessment": result}

    async def evaluate_evidence_set(
        self,
        evidence_items: List[Dict[str, str]],
        required_controls: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluate a set of evidence items against required controls.

        Args:
            evidence_items: List of evidence items with name and summary
            required_controls: List of required control IDs

        Returns:
            Evidence mapping and gaps
        """
        evidence_summary = "\n".join(
            [f"- {e['name']}: {e.get('summary', 'No summary')}" for e in evidence_items]
        )

        task = f"""
Evaluate evidence coverage for ITSG-33 controls.

Available Evidence:
{evidence_summary}

Required Controls: {', '.join(required_controls)}

Create:
1. Evidence-to-control mapping matrix
2. Controls with full evidence coverage
3. Controls with partial coverage
4. Controls with no evidence
5. Recommendations for additional evidence

Return as JSON.
"""

        result = self.agent.run(task)
        return {"evidence_evaluation": result}
