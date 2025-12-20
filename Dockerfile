# Base Python image for all services
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Copy source code
COPY packages/ ./packages/
COPY services/ ./services/

# === API Service ===
FROM base as api

EXPOSE 8000

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# === Document Extract Agent ===
FROM base as agent-document-extract

# Install additional OCR dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "-m", "services.agents.document_extract"]

# === Deadline Agent ===
FROM base as agent-deadline

CMD ["python", "-m", "services.agents.deadline"]

# === Worker (background jobs) ===
FROM base as worker

CMD ["python", "-m", "services.worker"]
