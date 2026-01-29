# ITSG-33 Accreditation System

An AI-powered multi-agent system for ITSG-33 security compliance assessment using Google Gemini, FastMCP, and Swarms.

## Overview

This system automates the ITSG-33 security accreditation process for Canadian Government systems by:

1. **Analyzing CONOPS** - Understanding system purpose, data types, and security requirements
2. **Mapping Controls** - Identifying applicable security controls across all 17 control families
3. **Assessing Evidence** - Evaluating submitted documentation against control requirements
4. **Analyzing Gaps** - Identifying and prioritizing implementation and evidence gaps
5. **Generating Reports** - Producing executive summaries, technical reports, and remediation plans

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Interface                          │
│              (FastAPI + Document Upload)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Swarms Coordinator Agent                        │
│           (Orchestrates entire workflow)                     │
└─────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────┘
      │      │      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌─────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌────────────┐
│ Control │ │Evidence│ │   Gap   │ │ Report  │ │ Knowledge  │
│ Mapper  │ │Assessor│ │Analyzer │ │Generator│ │   Base     │
│  MCP    │ │  MCP   │ │   MCP   │ │   MCP   │ │    MCP     │
└─────────┘ └────────┘ └─────────┘ └─────────┘ └────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Google Gemini API key

### Installation

```bash
# Clone and navigate to project
cd itsg33-accreditation

# Create virtual environment
uv venv
source .venv/bin/activate  # Unix/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
uv pip install -e ".[dev]"

# Copy environment file and add your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
# Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD for the first admin user
```

### Initialize Knowledge Base

```bash
# Load ITSG-33 controls into vector database
uv run python scripts/setup_knowledge_base.py
```

### Run the Application

```bash
# Start the FastAPI server
uv run uvicorn src.main:app --reload --port 8000
```

### Authentication

- On first startup, a local admin account is created from `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD`.
- Sign in at http://localhost:8000 to access the UI and API.
- Roles: admin (full access), assessor (run assessments), client (upload and view shared assessments), viewer (read-only for shared assessments).

### Run an Assessment (CLI)

```bash
# Run assessment with documents
uv run python scripts/run_assessment.py \
    "GOV_DEPT_001" \
    "New System Assessment" \
    -c ./samples/conops.pdf \
    -d ./samples/architecture.pdf ./samples/policies.docx \
    --wait
```

## Documentation

- Quickstart: docs/QUICKSTART.md
- User Guide: docs/USER_GUIDE.md
- In-app (served): http://localhost:8000/guides/QUICKSTART.md and http://localhost:8000/guides/USER_GUIDE.md

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | System information |
| `/health` | GET | Health check |
| `/auth/login` | POST | Create session |
| `/auth/logout` | POST | Destroy session |
| `/auth/me` | GET | Current user |
| `/auth/change-password` | POST | Change current password |
| `/auth/users` | GET | List users (admin) |
| `/auth/users` | POST | Create user (admin) |
| `/auth/users/{user_id}/roles` | POST | Update user roles (admin) |
| `/api/v1/assessment/create` | POST | Create new assessment |
| `/api/v1/assessment/{id}/upload` | POST | Upload documents |
| `/api/v1/assessment/{id}/run` | POST | Start assessment |
| `/api/v1/assessment/{id}/status` | GET | Get assessment status |
| `/api/v1/assessment/{id}/results` | GET | Get assessment results |
| `/api/v1/assessment/{id}/report` | GET | Get assessment report |
| `/api/v1/assessment/{id}/share` | POST | Share assessment (admin/assessor) |
| `/api/v1/assessment/{id}/share/{user_id}` | DELETE | Remove shared access (admin/assessor) |
| `/api/v1/assessments` | GET | List all assessments |
| `/api/v1/controls/families` | GET | List control families |
| `/api/v1/profiles` | GET | List ITSG-33 profiles |

## Control Families

The system assesses controls across all 17 ITSG-33 families:

| Code | Family Name |
|------|-------------|
| AC | Access Control |
| AT | Awareness and Training |
| AU | Audit and Accountability |
| CA | Assessment, Authorization, and Monitoring |
| CM | Configuration Management |
| CP | Contingency Planning |
| IA | Identification and Authentication |
| IR | Incident Response |
| MA | Maintenance |
| MP | Media Protection |
| PE | Physical and Environmental Protection |
| PL | Planning |
| PS | Personnel Security |
| RA | Risk Assessment |
| SA | System and Services Acquisition |
| SC | System and Communications Protection |
| SI | System and Information Integrity |

## Security Profiles

| Profile | Description |
|---------|-------------|
| Profile 1 | Low impact systems |
| Profile 2 | Moderate impact systems |
| Profile 3 | High impact systems |

## Development

### Run Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Code Formatting

```bash
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
```

## Project Structure

```
itsg33-accreditation/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── coordinator/            # Orchestration agent
│   ├── agents/                 # Specialized Swarms agents
│   ├── mcp_servers/            # FastMCP servers
│   ├── models/                 # Data models
│   └── utils/                  # Utilities
├── data/                       # Control catalog and profiles
├── scripts/                    # Setup and CLI scripts
├── tests/                      # Test suite
├── uploads/                    # Uploaded documents
└── outputs/                    # Generated reports
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.0-flash` |
| `UPLOAD_DIR` | Document upload directory | `./uploads` |
| `OUTPUT_DIR` | Report output directory | `./outputs` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage | `./chroma_db` |
| `AUTH_PROVIDER` | Auth provider (local only) | `local` |
| `AUTH_DB_PATH` | Auth database path | `./data/auth.db` |
| `AUTH_SECRET` | Session signing secret (set in production) | `change-me` |
| `SESSION_TTL_MINUTES` | Session lifetime | `120` |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Session idle timeout | `30` |
| `INITIAL_ADMIN_EMAIL` | Bootstrap admin email (first run) | `admin@example.com` |
| `INITIAL_ADMIN_PASSWORD` | Bootstrap admin password (first run) | `change-me-strong` |

## License

Proprietary - Government of Canada

## References

- [ITSG-33 Overview](https://www.cyber.gc.ca/en/guidance/it-security-risk-management-lifecycle-approach-itsg-33)
- [Swarms Documentation](https://docs.swarms.world)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Google Gemini API](https://ai.google.dev/docs)
