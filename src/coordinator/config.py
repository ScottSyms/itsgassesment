"""Configuration for the coordinator."""

import os
from pydantic_settings import BaseSettings


class CoordinatorConfig(BaseSettings):
    """Coordinator configuration settings."""

    # Gemini settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"

    # MCP Server URLs
    mcp_control_mapper_url: str = "http://localhost:8001"
    mcp_evidence_assessor_url: str = "http://localhost:8002"
    mcp_gap_analyzer_url: str = "http://localhost:8003"
    mcp_report_generator_url: str = "http://localhost:8004"
    mcp_knowledge_base_url: str = "http://localhost:8005"

    # Processing settings
    max_loops: int = 5
    max_iterations: int = 3

    # Storage settings
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    data_dir: str = "./data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_config() -> CoordinatorConfig:
    """Get coordinator configuration."""
    return CoordinatorConfig()
