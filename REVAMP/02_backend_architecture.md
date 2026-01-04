# Backend Architecture Plan - The Architect & The Engine

## Overview

The backend transforms from a static graph runner to a **Dynamic Graph Engine**.

## 1. Data Models (`src/models/`)

### `Superagent`

```python
class Superagent(BaseModel):
    id: UUID
    tenant_id: str
    name: str
    description: str
    graph_config: GraphConfig  # The Blueprint
    api_key_hash: str
    is_active: bool
    created_at: datetime
```

### `GraphConfig` (The Blueprint)

```python
class GraphConfig(BaseModel):
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    entry_point: str

class NodeConfig(BaseModel):
    id: str  # e.g., "financial_analyst"
    role: str
    goal: str
    system_prompt: str
    tools: List[str]  # e.g., ["google_search", "pdf_reader"]
```

## 2. Services (`src/services/`)

### `ArchitectService`

- **Role**: The Brain that designs the Brains.
- **Method**: `design_workflow(user_prompt: str) -> GraphConfig`
- **Logic**:
  1.  Uses a strong LLM (Reasoning Model).
  2.  Prompts: "Analyze this request. Break it down into specialized agents. Define the flow."
  3.  Outputs structured JSON (nodes/edges).

### `DynamicGraphService`

- **Role**: The Builder.
- **Method**: `compile_graph(config: GraphConfig) -> CompiledStateGraph`
- **Logic**:
  1.  Instantiates `StateGraph`.
  2.  Loops through `config.nodes`: creates `AgentNode` functions dynamically.
  3.  Loops through `config.edges`: adds `add_edge` or `add_conditional_edge`.
  4.  Returns compiled graph ready for `invoke`.

### `IdentityService`

- **Role**: Context & Security.
- **Middleware**: Extracts `X-Tenant-ID` or API Key.
- **RLS**: Sets a Postgres SESSION variable `app.current_tenant` to ensure queries only see relevant data.

## 3. API Endpoints (`src/api/v1/`)

### `routes/superagents.py`

- `POST /`: Design & Preview (calls Architect).
- `POST /confirm`: Save Superagent (calls DB).
- `POST /{id}/expose`: Generate API Key.

### `routes/invoke.py`

- `POST /invoke/{agent_id}`:
  - Auth: Validate API Key.
  - Rate Limit: Check Quota.
  - Execution: Load Graph -> Run -> Stream Events -> Return Final Output.

## Measurable Deliverables

- [ ] **Schema Migration**: Alembic script for `superagents` table.
- [ ] **Service**: `ArchitectService` with >90% success rate on "Create Financial Analyst" prompt.
- [ ] **Engine**: `DynamicGraphBuilder` unit tests passing for complex topologies (loops, parallel branches).
