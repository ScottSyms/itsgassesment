"""Base agent class for ITSG-33 agents."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from swarms import Agent


class BaseITSG33Agent(ABC):
    """Base class for all ITSG-33 agents."""

    def __init__(
        self,
        agent_name: str,
        agent_description: str,
        system_prompt: str,
        mcp_server_url: Optional[str] = None,
        max_loops: int = 3,
    ):
        """
        Initialize base agent.

        Args:
            agent_name: Name of the agent
            agent_description: Description of agent capabilities
            system_prompt: System prompt for the agent
            mcp_server_url: URL of the associated MCP server
            max_loops: Maximum number of reasoning loops
        """
        self.agent_name = agent_name
        self.mcp_url = mcp_server_url

        self.agent = Agent(
            agent_name=agent_name,
            agent_description=agent_description,
            system_prompt=system_prompt,
            model_name=os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-exp"),
            max_loops=max_loops,
            dynamic_temperature_enabled=True,
            saved_state_path=f"{agent_name.lower()}_state.json",
            user_name="itsg33_system",
            retry_attempts=3,
            context_length=8000,
            return_step_meta=True,
            output_type="json",
        )

    @abstractmethod
    async def run(self, task: str) -> Dict[str, Any]:
        """
        Run the agent on a task.

        Args:
            task: Task description

        Returns:
            Agent output
        """
        pass

    def get_agent(self) -> Agent:
        """Get the underlying Swarms agent."""
        return self.agent


ITSG33_CONTROL_FAMILIES = """
ITSG-33 Control Families:
- AC: Access Control - Controls related to user access, authentication, and authorization
- AT: Awareness and Training - Security awareness and training programs
- AU: Audit and Accountability - Audit logging, monitoring, and accountability
- CA: Assessment, Authorization, and Monitoring - Security assessment and continuous monitoring
- CM: Configuration Management - System configuration and change management
- CP: Contingency Planning - Business continuity and disaster recovery
- IA: Identification and Authentication - User identification and authentication mechanisms
- IR: Incident Response - Security incident handling and response
- MA: Maintenance - System maintenance procedures
- MP: Media Protection - Protection of storage media
- PE: Physical and Environmental Protection - Physical security controls
- PL: Planning - Security planning and documentation
- PS: Personnel Security - Personnel security policies and procedures
- RA: Risk Assessment - Risk identification and assessment
- SA: System and Services Acquisition - Secure system development and acquisition
- SC: System and Communications Protection - Network and communications security
- SI: System and Information Integrity - System integrity and malware protection
"""


ITSG33_PROFILES = """
ITSG-33 Security Profiles:
- Profile 1 (Low): For systems with low sensitivity data and low impact
- Profile 2 (Moderate): For systems with moderate sensitivity data
- Profile 3 (High): For systems with high sensitivity data or critical operations
"""
