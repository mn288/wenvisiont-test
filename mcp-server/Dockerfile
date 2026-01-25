FROM python:3.11-slim

# Install uv directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install curl for healthcheck (optional but good practice)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies using uv
# --system installs into the system python environment, avoiding the need for a venv in the container
RUN uv pip install --system --no-cache -r requirements.txt

# Copy all server files
COPY . .

# Expose the default port (can be overridden by docker-compose)
EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
