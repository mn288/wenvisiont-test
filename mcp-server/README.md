# Specialized MCP Servers

This directory contains a collection of specialized Model Context Protocol (MCP) servers designed to provide modular tools to your AI agents.

## Architecture

Instead of a monolithic toolset, each domain is isolated in its own server:

| Server | Port | Endpoint | Description |
|--------|------|----------|-------------|
| **Filesystem** | `8001` | `/sse` | Local file reading/writing. |
| **S3** | `8002` | `/sse` | AWS S3 bucket listing, reading, and writing. |
| **Analysis** | `8003` | `/sse` | Data analysis (Polars) and Web Search (Mock). |

## Setup

### 1. Environment Variables
Create a `.env` file in this directory if you plan to use S3:

```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
# FILESYSTEM_ROOT=/app/data (Defaults to /app/data inside container)
```

### 2. Run with Docker Compose
The servers are orchestrated via the main project's Docker Compose.

```bash
# Run from project root
docker-compose up -d --build
```


## Integration

These servers are **not automatically added** to your agent. You must register them in your main application to expose them.

### How to Register
In your application's "Add MCP Server" interface (or database), add the following entries:

**1. Filesystem Server**
- **Name**: `filesystem`
- **URL**: `http://localhost:8001/sse`
- *(If running backend in Docker)*: `http://filesystem-mcp:8000/sse`

**2. S3 Server**
- **Name**: `s3`
- **URL**: `http://localhost:8002/sse`
- *(If running backend in Docker)*: `http://s3-mcp:8000/sse`

**3. Analysis Server**
- **Name**: `analysis`
- **URL**: `http://localhost:8003/sse`
- *(If running backend in Docker)*: `http://analysis-mcp:8000/sse`

## Development
To add a new server:
1. Create a `new_server.py` using `FastMCP`.
2. Add a service entry in the root `docker-compose.yml` exposing a new port.
3. Rebuild: `docker-compose up -d --build`.
