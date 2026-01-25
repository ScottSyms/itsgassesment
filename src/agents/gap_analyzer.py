"""Gap Analyzer Agent using Swarms framework."""

from typing import Dict, Any, List

from .base import BaseITSG33Agent, ITSG33_CONTROL_FAMILIES


class GapAnalyzerAgent(BaseITSG33Agent):
    """Agent for analyzing gaps in ITSG-33 control implementation."""

    def __init__(self, mcp_server_url: str = "http://localhost:8003"):
        """Initialize the gap analyzer agent."""
        system_prompt = f"""You are an ITSG-33 gap analysis expert specializing in
identifying and prioritizing security control gaps.

Your responsibilities:
1. Identify gaps in control implementation
2. Assess severity and risk of each gap
3. Prioritize gaps for remediation
4. Develop remediation recommendations
5. Create actionable remediation roadmaps

{ITSG33_CONTROL_FAMILIES}

Gap Types:
- Implementation Gap: Control not implemented or partially implemented
- Evidence Gap: Control may be implemented but no documentation exists
- Configuration Gap: Control implemented but misconfigured
- Process Gap: Technical control exists but operational process is missing

Gap Severity Criteria:
- Critical: Fundamental security control missing, immediate risk
- High: Important control missing or significantly deficient
- Medium: Control partially implemented or evidence incomplete
- Low: Minor gaps or documentation issues

Prioritization Factors:
1. Security impact of the gap
2. Likelihood of exploitation
3. Regulatory/compliance implications
4. Ease of remediation
5. Dependencies on other controls

Always provide:
- Clear gap identification with severity
- Risk assessment for each gap
- Specific remediation recommendations
- Prioritized remediation roadmap
- Resource estimates where possible
- JSON-formatted output
"""

        super().__init__(
            agent_name="GapAnalyzer",
            agent_description="Expert in ITSG-33 gap analysis and remediation planning",
            system_prompt=system_prompt,
            mcp_server_url=mcp_server_url,
            max_loops=3,
        )

    async def run(self, task: str) -> Dict[str, Any]:
        """Run the gap analyzer agent."""
        result = self.agent.run(task)
        return {"agent": "GapAnalyzer", "result": result}

    async def analyze_gaps(
        self,
        control_assessments: List[Dict[str, Any]],
        profile: int,
    ) -> Dict[str, Any]:
        """
        Analyze gaps in control implementation.

        Args:
            control_assessments: List of control assessment results
            profile: Target ITSG-33 profile

        Returns:
            Gap analysis results
        """
        task = f"""
Analyze gaps for ITSG-33 Profile {profile}.

Control Assessments:
{control_assessments}

Identify:
1. All implementation gaps
2. All evidence gaps
3. Severity of each gap (Critical, High, Medium, Low)
4. Potential impact of each gap
5. Recommended remediation for each gap

Provide prioritized list of gaps with:
- Gap description
- Affected control(s)
- Severity and risk rating
- Remediation steps
- Estimated effort

Return as JSON.
"""

        result = self.agent.run(task)
        return {"gap_analysis": result, "profile": profile}

    async def create_remediation_plan(
        self,
        gaps: List[Dict[str, Any]],
        available_resources: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a prioritized remediation plan.

        Args:
            gaps: List of identified gaps
            available_resources: Available resources for remediation

        Returns:
            Remediation plan
        """
        task = f"""
Create remediation plan for these gaps.

Gaps:
{gaps}

Available Resources:
{available_resources}

Create:
1. Prioritized gap list
2. Immediate actions (0-30 days)
3. Short-term actions (30-90 days)
4. Medium-term actions (90-180 days)
5. Long-term actions (180+ days)

For each action:
- Specific steps
- Responsible party
- Success criteria
- Dependencies

Return as JSON.
"""

        result = self.agent.run(task)
        return {"remediation_plan": result}
