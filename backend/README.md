# AWP Backend

High-performance AI Agent Orchestration Service built with **FastAPI**, **LangGraph**, and **CrewAI**.

## 🏗 Architecture: Async Supervisor Swarm

The backend implements a sophisticated **Hierarchical Supervisor Swarm** architecture designed for scalability, autonomy, and advanced reasoning.

### Key Patterns
1.  **Orchestrator (LangGraph)**:
    - A stateful graph (`src/brain/nodes.py`) acts as the "Brain".
    - Uses a **Supervisor Node** returning `Command` objects for dynamic routing to atomic agents OR **Superagent Teams**.
    - **DyLAN (Dynamic Layout of Agents)** Strategy: Agents are ranked dynamically by importance and success rate during selection.
    - **Circuit Breaker**: Detects and breaks infinite loops or repetitive failures, routing to human (QA) intervention.

2.  **Worker Agents (CrewAI)**:
    - Individual agents are defined using **CrewAI** (`src/crew/`).
    - Agents operate *asynchronously* for maximum throughput.
    - Includes **Self-Reflection** loops: Agents critique their own output before finishing.

3.  **Mixture-of-Agents (MoA)**:
    - The final **QA Node** acts as an aggregator.
    - It synthesizes outputs from multiple agents (Layer 1) into a cohesive final response (Layer 2).
    - Resolves conflicts and merges insights from different specialists.

4.  **Voyager-Style Skill Retrieval**:
    - Agents use a **Skill Service** (`src/services/skill_service.py`) to retrieve past successful solutions.
    - New successful executions are saved as skills, allowing the swarm to "learn" and improve over time.

5.  **FastMCP Tool Bus**:
    - Tools are exposed via **Model Context Protocol (MCP)** using `fastmcp`.
    - Supports both local and remote MCP servers through a unified `tool_planning_node` interface.
    - Uses `orjson` for high-performance JSON parsing of complex tool arguments.

## 🛠 Technology Stack

### Core Frameworks
- **Python**: 3.12+ (managed by `uv`).
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/).
- **Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/).
- **Agents**: [CrewAI](https://crewai.com).
- **Tooling**: [FastMCP](https://github.com/punkpeye/fastmcp).

### Data & Infrastructure
- **Database**: PostgreSQL (with `pgvector` for extensive vector search).
- **Observability**: [Langfuse](https://langfuse.com/) (Distributed Tracing & Evaluation).
- **Migration**: Alembic.
- **Containerization**: Docker & Kubernetes.

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- `uv` (Python Package Manager)

### Local Development

1.  **Clone the repository** (part of the monorepo).
2.  **Infrastructure Up**:
    ```bash
    docker compose up -d
    ```
    This starts Postgres, Langfuse, and other dependencies.

3.  **Run Backend**:
    ```bash
    cd backend
    uv sync
    uv run poe dev
    ```
    The server will start at `http://localhost:8000`.

### Directory Structure

- `src/api`: FastAPI routes and endpoints.
- `src/brain`: LangGraph nodes and workflow logic.
- `src/crew`: CrewAI agent definitions.
- `src/core`: Configuration, Database, and Observability.
- `src/mcp`: FastMCP tool servers.
- `src/services`: Business logic (Execution, Orchestrator, Skills).

## 🧩 Observability

Every execution is traced using **Langfuse**.
- **Traces**: Full visibility into the Supervisor's decision-making and Agent execution.
- **Scores**: Automated evaluation of agent performance.
- **Generations**: Track token usage and latency for every LLM call.

---
Part of the **AWP** System.
