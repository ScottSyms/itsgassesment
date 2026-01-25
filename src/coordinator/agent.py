"""Main coordinator agent orchestrating the ITSG-33 assessment."""

import os
from typing import Dict, Any, List, Optional
import asyncio

from swarms import Agent

from src.agents.control_mapper import ControlMapperAgent
from src.agents.evidence_assessor import EvidenceAssessorAgent
from src.agents.gap_analyzer import GapAnalyzerAgent
from src.agents.report_generator import ReportGeneratorAgent
from src.utils.gemini_client import GeminiClient
from src.utils.document_parser import DocumentParser


class ITSG33Coordinator:
    """Coordinator for ITSG-33 accreditation process."""

    def __init__(self):
        """Initialize coordinator with agent handoffs."""
        # Initialize specialized agents
        self.control_mapper = ControlMapperAgent()
        self.evidence_assessor = EvidenceAssessorAgent()
        self.gap_analyzer = GapAnalyzerAgent()
        self.report_generator = ReportGeneratorAgent()

        # Initialize utilities
        self.gemini = GeminiClient()
        self.doc_parser = DocumentParser()

        # Initialize coordinator agent
        self.coordinator = Agent(
            agent_name="ITSG33Coordinator",
            agent_description="""Orchestrates the complete ITSG-33 security
            accreditation process, coordinating specialized agents.""",
            system_prompt=self._get_system_prompt(),
            model_name=os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-exp"),
            max_loops="auto",
            handoffs=[
                self.control_mapper.get_agent(),
                self.evidence_assessor.get_agent(),
                self.gap_analyzer.get_agent(),
                self.report_generator.get_agent(),
            ],
            dynamic_temperature_enabled=True,
            saved_state_path="coordinator_state.json",
            context_length=16000,
            return_step_meta=True,
        )

    def _get_system_prompt(self) -> str:
        """Get coordinator system prompt."""
        return """You are the ITSG-33 Accreditation Coordinator.

You orchestrate the complete security assessment process following these phases:

Phase 1 - Control Mapping:
- Analyze CONOPS and system documentation
- Determine security categorization (C/I/A)
- Select appropriate ITSG-33 profile (1, 2, or 3)
- Map applicable controls from all 17 families
- Delegate to ControlMapper agent

Phase 2 - Evidence Assessment:
- Process submitted documentation
- Map evidence to controls
- Assess evidence quality and sufficiency
- Delegate to EvidenceAssessor agent

Phase 3 - Gap Analysis:
- Identify implementation gaps
- Identify evidence gaps
- Prioritize by severity and risk
- Delegate to GapAnalyzer agent

Phase 4 - Iteration:
- Review gap analysis results
- Request additional evidence from client if needed
- Re-assess with new documentation
- Continue until satisfactory coverage

Phase 5 - Report Generation:
- Generate executive summary
- Create detailed technical report
- Produce compliance matrix
- Develop remediation plan
- Delegate to ReportGenerator agent

Workflow Management:
- Track overall progress
- Coordinate between agents
- Manage state and context
- Handle errors gracefully
- Ensure comprehensive assessment

Always maintain:
- Clear communication of progress
- Traceability of decisions
- Comprehensive documentation
- Professional output quality
"""

    async def run_assessment(
        self,
        conops: str,
        documents: List[Dict[str, Any]],
        diagrams: List[Dict[str, Any]],
        client_id: str,
    ) -> Dict[str, Any]:
        """
        Run complete ITSG-33 assessment.

        Args:
            conops: Concept of operations document
            documents: List of document metadata
            diagrams: List of diagram metadata
            client_id: Client identifier

        Returns:
            Complete assessment results
        """
        results = {
            "client_id": client_id,
            "status": "in_progress",
            "phases": {},
        }

        try:
            # Phase 1: Control Mapping
            categorization = await self._phase_control_mapping(conops, documents)
            results["phases"]["control_mapping"] = categorization

            # Phase 2: Evidence Assessment
            evidence_assessment = await self._phase_evidence_assessment(
                documents, diagrams, categorization.get("control_mappings", [])
            )
            results["phases"]["evidence_assessment"] = evidence_assessment

            # Phase 3: Gap Analysis
            gap_analysis = await self._phase_gap_analysis(
                evidence_assessment, categorization.get("profile", 2)
            )
            results["phases"]["gap_analysis"] = gap_analysis

            # Phase 4: Report Generation
            reports = await self._phase_report_generation(
                results, client_id
            )
            results["phases"]["reports"] = reports

            results["status"] = "completed"

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)

        return results

    async def _phase_control_mapping(
        self,
        conops: str,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute control mapping phase."""
        # Extract system description from documents
        system_description = ""
        data_types = []

        for doc in documents[:5]:  # Process first 5 docs for description
            if "content" in doc:
                system_description += doc.get("content", "")[:2000]

        # Categorize system
        categorization = await self.control_mapper.categorize_system(
            conops=conops,
            system_description=system_description,
            data_types=data_types or ["General data"],
        )

        # Map controls
        control_mappings = await self.control_mapper.map_controls(
            categorization=categorization.get("categorization", {}),
            system_characteristics={"documents": len(documents)},
        )

        return {
            "categorization": categorization,
            "control_mappings": control_mappings,
            "profile": 2,  # Default to moderate
        }

    async def _phase_evidence_assessment(
        self,
        documents: List[Dict[str, Any]],
        diagrams: List[Dict[str, Any]],
        control_mappings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute evidence assessment phase."""
        evidence_items = []

        for doc in documents:
            evidence_items.append({
                "name": doc.get("filename", "Unknown"),
                "summary": doc.get("content", "")[:500] if "content" in doc else "",
            })

        for diagram in diagrams:
            evidence_items.append({
                "name": diagram.get("filename", "Unknown"),
                "summary": "Diagram/image file",
            })

        # Get list of control IDs from mappings
        control_ids = []
        for mapping in control_mappings:
            if isinstance(mapping, dict) and "control_id" in mapping:
                control_ids.append(mapping["control_id"])

        if not control_ids:
            control_ids = ["AC-1", "AU-1", "CM-1", "IA-1", "SC-1"]  # Default controls

        evaluation = await self.evidence_assessor.evaluate_evidence_set(
            evidence_items=evidence_items,
            required_controls=control_ids,
        )

        return evaluation

    async def _phase_gap_analysis(
        self,
        evidence_assessment: Dict[str, Any],
        profile: int,
    ) -> Dict[str, Any]:
        """Execute gap analysis phase."""
        # Create control assessments from evidence assessment
        control_assessments = []

        if "evidence_evaluation" in evidence_assessment:
            # Parse the evaluation to create control assessments
            control_assessments = [evidence_assessment]

        gap_analysis = await self.gap_analyzer.analyze_gaps(
            control_assessments=control_assessments,
            profile=profile,
        )

        return gap_analysis

    async def _phase_report_generation(
        self,
        results: Dict[str, Any],
        client_id: str,
    ) -> Dict[str, Any]:
        """Execute report generation phase."""
        client_info = {"client_id": client_id}

        # Generate executive summary
        executive_summary = await self.report_generator.generate_executive_summary(
            assessment_results=results,
            client_info=client_info,
        )

        # Generate compliance matrix
        control_assessments = results.get("phases", {}).get(
            "evidence_assessment", {}
        )
        compliance_matrix = await self.report_generator.generate_compliance_matrix(
            control_assessments=[control_assessments],
            profile=results.get("phases", {}).get("control_mapping", {}).get("profile", 2),
        )

        return {
            "executive_summary": executive_summary,
            "compliance_matrix": compliance_matrix,
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get current coordinator status."""
        return {
            "coordinator": "ITSG33Coordinator",
            "agents": [
                "ControlMapper",
                "EvidenceAssessor",
                "GapAnalyzer",
                "ReportGenerator",
            ],
            "status": "ready",
        }
