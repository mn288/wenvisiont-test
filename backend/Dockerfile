# /backend/Dockerfile
FROM python:3.12-slim-bookworm

# Configure Python and uv to run in non-interactive modes
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies if needed (e.g. for potential native builds)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install uv check for updates: https://github.com/astral-sh/uv
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /bin/uv

WORKDIR /app

# Copy dependency definitions first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies strictly from the lockfile
RUN uv sync --frozen --no-dev

# Copy application code
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

# Create a non-root user for security (GCP Cloud Run best practice)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose the port
EXPOSE 8000

# Command to run the application using uvicorn
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
