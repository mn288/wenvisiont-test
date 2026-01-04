# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project definition
COPY backend/pyproject.toml backend/uv.lock /app/backend/

# Sync dependencies
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-install-project

# Runner stage
FROM python:3.12-slim AS runner

WORKDIR /app/backend

# Copy virtual env from builder
COPY --from=builder /app/backend/.venv /app/backend/.venv

# Copy source code
COPY backend/src /app/backend/src

# Set environment
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Command to run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
