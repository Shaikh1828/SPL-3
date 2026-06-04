# Multi-stage Docker build for FastAPI backend

FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install venv and upgrade pip
RUN python -m venv /build/.venv && \
    /build/.venv/bin/pip install --upgrade pip setuptools wheel

# Install Python dependencies directly (with retries and extended timeout)
RUN /build/.venv/bin/pip install --default-timeout=600 --retries 5 \
    fastapi==0.110.0 \
    uvicorn==0.27.0 \
    sqlalchemy==2.0.23 \
    psycopg2-binary==2.9.9 \
    pydantic==2.5.3 \
    pydantic-settings==2.1.0 \
    python-dotenv==1.0.0 \
    redis==5.0.1 \
    aioredis==2.0.1 \
    python-multipart==0.0.6 \
    python-jose==3.3.0 \
    passlib==1.7.4 \
    bcrypt==4.1.2 \
    email-validator==2.1.0 \
    slowapi==0.1.9 \
    httpx==0.25.2 \
    PyJWT==2.8.0 \
    Pillow==10.0.0 \
    structlog==24.1.0 \
    alembic==1.12.0 \
    requests==2.31.0 \
    aiofiles==23.2.0 \
    pytest==7.4.3 \
    pytest-asyncio==0.23.2 \
    pytest-cov==4.1.0 \
    aiosqlite==0.19.0 \
    numpy==1.24.3 \
    opencv-python==4.8.1.78

# ============================================================================
# Runtime stage
# ============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /storage

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

# Expose port
EXPOSE 8000

# Run API 
CMD ["/bin/sh", "-c", "/app/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"]
