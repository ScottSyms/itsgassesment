#!/bin/bash

# Start all MCP servers in background
echo "Starting ITSG-33 MCP Servers..."

# Change to project directory
cd "$(dirname "$0")/.."

# Ensure virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi
fi

# Knowledge Base
echo "Starting Knowledge Base MCP on port 8005..."
uv run python -m src.mcp_servers.knowledge_base.server &
KB_PID=$!

# Control Mapper
echo "Starting Control Mapper MCP on port 8001..."
uv run python -m src.mcp_servers.control_mapper.server &
CM_PID=$!

# Evidence Assessor
echo "Starting Evidence Assessor MCP on port 8002..."
uv run python -m src.mcp_servers.evidence_assessor.server &
EA_PID=$!

# Gap Analyzer
echo "Starting Gap Analyzer MCP on port 8003..."
uv run python -m src.mcp_servers.gap_analyzer.server &
GA_PID=$!

# Report Generator
echo "Starting Report Generator MCP on port 8004..."
uv run python -m src.mcp_servers.report_generator.server &
RG_PID=$!

echo ""
echo "All MCP servers started!"
echo "  - Knowledge Base MCP: port 8005 (PID: $KB_PID)"
echo "  - Control Mapper MCP: port 8001 (PID: $CM_PID)"
echo "  - Evidence Assessor MCP: port 8002 (PID: $EA_PID)"
echo "  - Gap Analyzer MCP: port 8003 (PID: $GA_PID)"
echo "  - Report Generator MCP: port 8004 (PID: $RG_PID)"
echo ""
echo "To stop all servers: pkill -f 'mcp_servers'"
echo "Or use: kill $KB_PID $CM_PID $EA_PID $GA_PID $RG_PID"

# Wait for any background process
wait
