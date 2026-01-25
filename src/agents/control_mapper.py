"""Control Mapper Agent using Swarms framework."""

from typing import Dict, Any, List
import httpx

from .base import BaseITSG33Agent, ITSG33_CONTROL_FAMILIES, ITSG33_PROFILES


class ControlMapperAgent(BaseITSG33Agent):
    """Agent for mapping ITSG-33 controls to systems."""

    def __init__(self, mcp_server_url: str = "http://localhost:8001"):
        """Initialize the control mapper agent."""
        system_prompt = f"""You are an ITSG-33 security control mapping expert for the
Canadian Government.

Your responsibilities:
1. Analyze CONOPS and system documentation
2. Determine security categorization (C/I/A levels)
3. Select appropriate ITSG-33 profile (1, 2, or 3)
4. Map applicable security controls from all 17 control families
5. Provide clear rationale for each control selection

{ITSG33_CONTROL_FAMILIES}

{ITSG33_PROFILES}

When analyzing systems:
1. Consider data sensitivity and classification
2. Evaluate business criticality
3. Assess connectivity and integration points
4. Review user types and access requirements
5. Consider regulatory requirements

Always provide:
- Clear categorization with rationale
- Complete control mappings covering all families
- Prioritized implementation recommendations
- JSON-formatted output for downstream processing
"""

        super().__init__(
            agent_name="ControlMapper",
            agent_description="Expert in ITSG-33 security control mapping and system categorization",
            system_prompt=system_prompt,
            mcp_server_url=mcp_server_url,
            max_loops=3,
        )

    async def run(self, task: str) -> Dict[str, Any]:
        """Run the control mapper agent."""
        result = self.agent.run(task)
        return {"agent": "ControlMapper", "result": result}

    async def categorize_system(
        self,
        conops: str,
        system_description: str,
        data_types: List[str],
    ) -> Dict[str, Any]:
        """
        Categorize system and determine profile.

        Args:
            conops: Concept of operations document
            system_description: Technical system description
            data_types: Types of data processed

        Returns:
            System categorization
        """
        task = f"""
Analyze this system and determine ITSG-33 categorization:

CONOPS Summary:
{conops[:5000]}

System Description:
{system_description[:3000]}

Data Types:
{', '.join(data_types)}

Determine:
1. Confidentiality level (Low/Moderate/High) with rationale
2. Integrity level (Low/Moderate/High) with rationale
3. Availability level (Low/Moderate/High) with rationale
4. Data classification (Unclassified, Protected A/B/C, Secret, Top Secret)
5. Recommended ITSG-33 profile (1, 2, or 3)

Provide detailed rationale for each determination.
Return as JSON.
"""

        result = self.agent.run(task)
        return {"categorization": result}

    async def map_controls(
        self,
        categorization: Dict[str, Any],
        system_characteristics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Map applicable controls based on categorization.

        Args:
            categorization: System categorization
            system_characteristics: System characteristics

        Returns:
            List of mapped controls
        """
        task = f"""
Based on this system categorization:
{categorization}

And these characteristics:
{system_characteristics}

Identify all applicable ITSG-33 security controls.

For each control:
1. Control ID and name
2. Control family
3. Baseline requirement (Profile 1, 2, or 3)
4. Rationale for applicability
5. Implementation priority (High, Medium, Low)

Cover all 17 control families comprehensively.
Return as JSON array.
"""

        result = self.agent.run(task)
        return [{"control_mappings": result}]
