"""Tests for ITSG-33 agents."""

import pytest
from unittest.mock import MagicMock, patch

from src.agents.base import BaseITSG33Agent, ITSG33_CONTROL_FAMILIES
from src.agents.control_mapper import ControlMapperAgent
from src.agents.evidence_assessor import EvidenceAssessorAgent
from src.agents.gap_analyzer import GapAnalyzerAgent
from src.agents.report_generator import ReportGeneratorAgent


class TestBaseAgent:
    """Tests for base agent functionality."""

    def test_control_families_defined(self):
        """Test that control families are properly defined."""
        assert "AC" in ITSG33_CONTROL_FAMILIES
        assert "AU" in ITSG33_CONTROL_FAMILIES
        assert "17 control families" in ITSG33_CONTROL_FAMILIES or len(
            [line for line in ITSG33_CONTROL_FAMILIES.split("\n") if line.startswith("- ")]
        ) >= 17


class TestControlMapperAgent:
    """Tests for ControlMapperAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent fixture."""
        with patch("src.agents.control_mapper.BaseITSG33Agent.__init__"):
            agent = ControlMapperAgent.__new__(ControlMapperAgent)
            agent.agent = MagicMock()
            return agent

    def test_agent_has_categorize_method(self):
        """Test that agent has categorize_system method."""
        assert hasattr(ControlMapperAgent, "categorize_system")

    def test_agent_has_map_controls_method(self):
        """Test that agent has map_controls method."""
        assert hasattr(ControlMapperAgent, "map_controls")


class TestEvidenceAssessorAgent:
    """Tests for EvidenceAssessorAgent."""

    def test_agent_has_assess_document_method(self):
        """Test that agent has assess_document method."""
        assert hasattr(EvidenceAssessorAgent, "assess_document")

    def test_agent_has_evaluate_evidence_set_method(self):
        """Test that agent has evaluate_evidence_set method."""
        assert hasattr(EvidenceAssessorAgent, "evaluate_evidence_set")


class TestGapAnalyzerAgent:
    """Tests for GapAnalyzerAgent."""

    def test_agent_has_analyze_gaps_method(self):
        """Test that agent has analyze_gaps method."""
        assert hasattr(GapAnalyzerAgent, "analyze_gaps")

    def test_agent_has_create_remediation_plan_method(self):
        """Test that agent has create_remediation_plan method."""
        assert hasattr(GapAnalyzerAgent, "create_remediation_plan")


class TestReportGeneratorAgent:
    """Tests for ReportGeneratorAgent."""

    def test_agent_has_generate_executive_summary_method(self):
        """Test that agent has generate_executive_summary method."""
        assert hasattr(ReportGeneratorAgent, "generate_executive_summary")

    def test_agent_has_generate_detailed_report_method(self):
        """Test that agent has generate_detailed_report method."""
        assert hasattr(ReportGeneratorAgent, "generate_detailed_report")

    def test_agent_has_generate_compliance_matrix_method(self):
        """Test that agent has generate_compliance_matrix method."""
        assert hasattr(ReportGeneratorAgent, "generate_compliance_matrix")
