"""Tests for MCP servers."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestKnowledgeBaseMCP:
    """Tests for Knowledge Base MCP Server."""

    @pytest.mark.asyncio
    async def test_search_controls_returns_list(self):
        """Test that search_controls returns a list."""
        from src.mcp_servers.knowledge_base.server import search_controls

        # Mock the collection
        with patch("src.mcp_servers.knowledge_base.server.collection") as mock_collection:
            mock_collection.query.return_value = {
                "documents": [["Test control description"]],
                "metadatas": [[{"family": "AC", "profile": 1}]],
                "ids": [["AC-1"]],
                "distances": [[0.5]],
            }

            result = await search_controls("access control")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["id"] == "AC-1"

    @pytest.mark.asyncio
    async def test_get_control_families_returns_list(self):
        """Test that get_control_families returns all families."""
        from src.mcp_servers.knowledge_base.server import get_control_families

        result = await get_control_families()

        assert isinstance(result, list)
        assert len(result) == 17
        codes = [f["code"] for f in result]
        assert "AC" in codes
        assert "AU" in codes
        assert "SC" in codes


class TestControlMapperMCP:
    """Tests for Control Mapper MCP Server."""

    @pytest.mark.asyncio
    async def test_determine_profile_low(self):
        """Test profile determination for low impact."""
        from src.mcp_servers.control_mapper.server import determine_profile

        categorization = {
            "confidentiality": "Low",
            "integrity": "Low",
            "availability": "Low",
        }

        result = await determine_profile(categorization)

        assert result["profile"] == 1

    @pytest.mark.asyncio
    async def test_determine_profile_moderate(self):
        """Test profile determination for moderate impact."""
        from src.mcp_servers.control_mapper.server import determine_profile

        categorization = {
            "confidentiality": "Moderate",
            "integrity": "Low",
            "availability": "Low",
        }

        result = await determine_profile(categorization)

        assert result["profile"] == 2

    @pytest.mark.asyncio
    async def test_determine_profile_high(self):
        """Test profile determination for high impact."""
        from src.mcp_servers.control_mapper.server import determine_profile

        categorization = {
            "confidentiality": "High",
            "integrity": "Low",
            "availability": "Moderate",
        }

        result = await determine_profile(categorization)

        assert result["profile"] == 3


class TestControlMapperTools:
    """Tests for Control Mapper tools."""

    def test_calculate_impact_level_high(self):
        """Test high impact calculation."""
        from src.mcp_servers.control_mapper.tools import calculate_impact_level

        factors = ["national security", "classified data"]
        result = calculate_impact_level(factors)

        assert result == "High"

    def test_calculate_impact_level_moderate(self):
        """Test moderate impact calculation."""
        from src.mcp_servers.control_mapper.tools import calculate_impact_level

        factors = ["protected b", "financial data"]
        result = calculate_impact_level(factors)

        assert result == "Moderate"

    def test_calculate_impact_level_low(self):
        """Test low impact calculation."""
        from src.mcp_servers.control_mapper.tools import calculate_impact_level

        factors = ["public information"]
        result = calculate_impact_level(factors)

        assert result == "Low"

    def test_get_baseline_controls_profile_1(self):
        """Test baseline controls for profile 1."""
        from src.mcp_servers.control_mapper.tools import get_baseline_controls

        controls = get_baseline_controls(1)

        assert isinstance(controls, list)
        assert "AC-1" in controls
        assert "AU-1" in controls


class TestGapAnalyzerTools:
    """Tests for Gap Analyzer tools."""

    def test_calculate_severity_critical(self):
        """Test critical severity calculation."""
        from src.mcp_servers.gap_analyzer.tools import calculate_severity, GapSeverity

        severity = calculate_severity("AC", "Not Implemented", "High")

        assert severity == GapSeverity.CRITICAL

    def test_calculate_compliance_score(self):
        """Test compliance score calculation."""
        from src.mcp_servers.gap_analyzer.tools import calculate_compliance_score

        result = calculate_compliance_score(
            total_controls=100,
            implemented=50,
            partial=20,
            not_implemented=30,
        )

        assert result["percentage"] == 60.0
        assert result["status"] == "Acceptable"
