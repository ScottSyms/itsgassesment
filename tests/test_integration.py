"""Integration tests for ITSG-33 Accreditation System."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path


class TestFastAPIApp:
    """Tests for FastAPI application endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from src.main import app

        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns system info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ITSG-33 Accreditation System"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_control_families_endpoint(self, client):
        """Test control families endpoint."""
        response = client.get("/api/v1/controls/families")

        assert response.status_code == 200
        data = response.json()
        assert "families" in data
        assert len(data["families"]) == 17

    def test_profiles_endpoint(self, client):
        """Test profiles endpoint."""
        response = client.get("/api/v1/profiles")

        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert len(data["profiles"]) == 3

    def test_create_assessment(self, client):
        """Test creating an assessment."""
        response = client.post(
            "/api/v1/assessment/create",
            json={
                "client_id": "TEST_CLIENT",
                "project_name": "Test Project",
                "conops": "Test CONOPS",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "assessment_id" in data
        assert data["status"] == "created"

    def test_get_assessment_status_not_found(self, client):
        """Test getting status for non-existent assessment."""
        response = client.get("/api/v1/assessment/nonexistent-id/status")

        assert response.status_code == 404


class TestStorageManager:
    """Tests for StorageManager."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager with temp directory."""
        from src.utils.storage import StorageManager

        return StorageManager(
            upload_dir=str(tmp_path / "uploads"),
            output_dir=str(tmp_path / "outputs"),
            data_dir=str(tmp_path / "data"),
        )

    @pytest.mark.asyncio
    async def test_create_assessment(self, storage):
        """Test creating an assessment record."""
        result = await storage.create_assessment(
            assessment_id="test-123",
            client_id="CLIENT_001",
            project_name="Test Project",
            conops="Test CONOPS content",
        )

        assert result["assessment_id"] == "test-123"
        assert result["client_id"] == "CLIENT_001"
        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_get_assessment(self, storage):
        """Test retrieving an assessment."""
        await storage.create_assessment(
            assessment_id="test-456",
            client_id="CLIENT_002",
            project_name="Another Project",
        )

        result = await storage.get_assessment("test-456")

        assert result is not None
        assert result["assessment_id"] == "test-456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_assessment(self, storage):
        """Test retrieving non-existent assessment."""
        result = await storage.get_assessment("nonexistent")

        assert result is None


class TestDocumentParser:
    """Tests for DocumentParser."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create document parser."""
        from src.utils.document_parser import DocumentParser

        return DocumentParser(upload_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_parse_text_file(self, parser, tmp_path):
        """Test parsing a text file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content.")

        result = await parser.parse(test_file)

        assert result is not None
        assert result["type"] == "text"
        assert "This is test content" in result["full_text"]

    def test_supported_extensions(self, parser):
        """Test getting supported extensions."""
        extensions = parser.get_supported_extensions()

        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".txt" in extensions

    @pytest.mark.asyncio
    async def test_parse_nonexistent_file(self, parser, tmp_path):
        """Test parsing non-existent file."""
        result = await parser.parse(tmp_path / "nonexistent.txt")

        assert result is None


class TestModels:
    """Tests for data models."""

    def test_system_categorization_profile(self):
        """Test profile determination from categorization."""
        from src.models.controls import SystemCategorization, SecurityProfile

        cat = SystemCategorization(
            confidentiality="High",
            integrity="Moderate",
            availability="Low",
            data_classification="Protected B",
            business_criticality="Critical",
        )

        assert cat.get_profile() == SecurityProfile.PROFILE_3

    def test_assessment_result_compliance_calculation(self):
        """Test compliance percentage calculation."""
        from src.models.assessment import AssessmentResult
        from datetime import datetime

        result = AssessmentResult(
            assessment_id="test",
            project_name="Test",
            client_id="CLIENT",
            profile=2,
            total_controls=100,
            implemented_count=60,
            partial_count=20,
            not_implemented_count=20,
        )

        compliance = result.calculate_compliance()

        assert compliance == 70.0  # 60 + (20 * 0.5) = 70

    def test_gap_model(self):
        """Test Gap model creation."""
        from src.models.evidence import Gap, GapSeverity

        gap = Gap(
            gap_id="GAP-001",
            control_id="AC-1",
            control_name="Access Control Policy",
            gap_type="Implementation",
            severity=GapSeverity.HIGH,
            description="Access control policy not documented",
            impact="Unauthorized access may occur",
            recommendation="Document access control policy",
        )

        assert gap.severity == GapSeverity.HIGH
        assert gap.status == "Open"
