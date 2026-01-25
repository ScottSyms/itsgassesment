# ITSG-33 Accreditation System - Main Application
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY static/ ./static/
COPY data/ ./data/
COPY scripts/ ./scripts/

# Install dependencies
RUN uv pip install --system -e .

# Create directories
RUN mkdir -p uploads outputs chroma_db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
