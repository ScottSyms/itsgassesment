"""ITSG-33 Knowledge Base MCP Server."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
import chromadb
from chromadb.config import Settings

# Initialize FastMCP server
mcp = FastMCP("ITSG-33 Knowledge Base")

# Get data directory
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Initialize ChromaDB
chroma_client = chromadb.Client(
    Settings(persist_directory=CHROMA_DIR, anonymized_telemetry=False)
)

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="itsg33_controls",
    metadata={"description": "ITSG-33 security controls catalog"},
)


@mcp.tool()
async def search_controls(
    query: str,
    control_family: Optional[str] = None,
    profile: Optional[int] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search ITSG-33 security controls by query.

    Args:
        query: Natural language query about security controls
        control_family: Optional filter by control family (e.g., 'AC', 'AU', 'CM')
        profile: Optional filter by profile number (1, 2, or 3)
        limit: Maximum number of results

    Returns:
        List of matching security controls
    """
    # Build metadata filter
    where = {}
    if control_family:
        where["family"] = control_family
    if profile:
        where["profile"] = {"$lte": profile}

    # Search in vector database
    results = collection.query(
        query_texts=[query], n_results=limit, where=where if where else None
    )

    controls = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            controls.append(
                {
                    "id": results["ids"][0][i],
                    "description": doc,
                    "metadata": metadata,
                    "distance": results["distances"][0][i]
                    if results["distances"]
                    else None,
                }
            )

    return controls


@mcp.tool()
async def get_control_by_id(control_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific ITSG-33 control by ID (e.g., 'AC-1', 'AU-2').

    Args:
        control_id: Control identifier

    Returns:
        Control details or None if not found
    """
    results = collection.get(ids=[control_id])

    if results["documents"]:
        return {
            "id": control_id,
            "description": results["documents"][0],
            "metadata": results["metadatas"][0] if results["metadatas"] else {},
        }

    return None


@mcp.tool()
async def get_profile_controls(profile: int) -> List[Dict[str, Any]]:
    """
    Get all controls for a specific ITSG-33 profile.

    Args:
        profile: Profile number (1, 2, or 3)

    Returns:
        List of controls for the profile
    """
    results = collection.get(where={"profile": {"$lte": profile}})

    controls = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"]):
            controls.append(
                {
                    "id": results["ids"][i],
                    "description": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                }
            )

    return controls


@mcp.tool()
async def get_control_families() -> List[Dict[str, str]]:
    """
    Get list of all ITSG-33 control families with descriptions.

    Returns:
        List of control family information
    """
    families = [
        {"code": "AC", "name": "Access Control"},
        {"code": "AT", "name": "Awareness and Training"},
        {"code": "AU", "name": "Audit and Accountability"},
        {"code": "CA", "name": "Assessment, Authorization, and Monitoring"},
        {"code": "CM", "name": "Configuration Management"},
        {"code": "CP", "name": "Contingency Planning"},
        {"code": "IA", "name": "Identification and Authentication"},
        {"code": "IR", "name": "Incident Response"},
        {"code": "MA", "name": "Maintenance"},
        {"code": "MP", "name": "Media Protection"},
        {"code": "PE", "name": "Physical and Environmental Protection"},
        {"code": "PL", "name": "Planning"},
        {"code": "PS", "name": "Personnel Security"},
        {"code": "RA", "name": "Risk Assessment"},
        {"code": "SA", "name": "System and Services Acquisition"},
        {"code": "SC", "name": "System and Communications Protection"},
        {"code": "SI", "name": "System and Information Integrity"},
    ]
    return families


@mcp.tool()
async def get_controls_by_family(family: str) -> List[Dict[str, Any]]:
    """
    Get all controls in a specific family.

    Args:
        family: Control family code (e.g., 'AC', 'AU')

    Returns:
        List of controls in the family
    """
    results = collection.get(where={"family": family.upper()})

    controls = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"]):
            controls.append(
                {
                    "id": results["ids"][i],
                    "description": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                }
            )

    return controls


@mcp.tool()
async def get_control_questions(control_id: str) -> List[str]:
    """
    Get assessment questions for a specific control.

    Args:
        control_id: Control identifier

    Returns:
        List of assessment questions
    """
    control = await get_control_by_id(control_id)
    if control and "metadata" in control:
        return control["metadata"].get("questions", [])
    return []


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8005)
