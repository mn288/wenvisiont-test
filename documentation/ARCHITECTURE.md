# Technical Architecture & Flow

This document outlines the technical infrastructure and data flow architecture of the Mnabaa Agentic Platform.

## High-Levels Architecture

```mermaid
graph TB
    subgraph Client ["Frontend (Next.js)"]
        UI["User Interface"]
        Stream["EventSource (SSE)"]
        APIClient["API Client"]
    end

    subgraph Backend ["Backend System (FastAPI)"]
        direction TB

        subgraph APILayer ["API Layer"]
            Endpoints["Endpoints (/jobs, /stream, /agents)"]
            Auth["Tenant/Role Middleware"]
        end

        subgraph Orchestration ["Orchestration Core (LangGraph)"]
            Graph["GraphService"]
            Supervisor["Supervisor Node"]
            Preprocess["Preprocess Node"]
            QA["QA Node"]
        end

        subgraph Execution ["Execution Engine (CrewAI)"]
            Crew["CrewService"]
            Registry["Agent Registry"]
            Agents["Workers (Research, Code, etc.)"]
        end

        subgraph Infra ["Infrastructure Services"]
            InfraSvc["InfrastructureService"]
            Tools["Async Tools (File, S3)"]
            Logger["LogHandler"]
        end
    end

    subgraph Persistence ["Data & Storage"]
        DB[("PostgreSQL")]
        FS["Local Workspace (/tmp)"]
        S3["AWS S3"]
    end

    %% Client Interactions
    UI -->|Submit Job| APIClient
    APIClient -->|POST /jobs| Endpoints
    UI -->|Listen| Stream
    Endpoints -.->|SSE Events| Stream

    %% API to Core
    Endpoints -->|Invoke| Graph
    Endpoints -->|Query History| DB

    %% Orchestration Flow
    Graph --> Preprocess
    Preprocess --> Supervisor
    Supervisor -->|Decide Next Step| Registry
    Supervisor -->|Delegate Task| Crew

    %% Execution Flow
    Crew -->|Instantiate| Agents
    Agents -->|Execute| Tools
    Tools -->|Use| InfraSvc

    %% Infrastructure & IO
    InfraSvc -->|Read/Write| FS
    InfraSvc -->|Sync/Store| S3

    %% Logging & State
    Agents -->|Log Steps| Logger
    Graph -->|Checkpoint State| DB
    Logger -->|Persist Logs| DB
```

## Detailed Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as Backend API
    participant Graph as LangGraph (Supervisor)
    participant Crew as CrewAI Service
    participant Infra as Infrastructure / Tools
    participant DB as PostgreSQL

    User->>FE: Submits Request
    FE->>API: POST /jobs (input)
    API->>DB: Create Conversation
    API->>Graph: Start Background Task
    API-->>FE: Job ID (Accepted)

    FE->>API: GET /stream (Subscribe SSE)

    loop Graph Execution
        Graph->>Graph: Preprocess (Mask PII)
        Graph->>Graph: Supervisor (Plan)
        Graph->>Crew: Execute Task (Agent X)

        activate Crew
        Crew->>Infra: Setup Workspace (/tmp/{thread_id})
        Crew->>Infra: Execute Tools (Write Code/File)
        Infra-->>Crew: Result
        Crew->>DB: Log Step (Thought/Output)
        Crew-->>Graph: Task Result
        deactivate Crew

        Graph->>API: Emit SSE Event (Progress)
        API-->>FE: Update UI
    end

    Graph->>Graph: QA Node (Finalize)
    Graph->>DB: Checkpoint Final State
    Graph-->>API: Stream [DONE]
    API-->>FE: Stream Complete
```

## Core Components

### 1. Frontend (Next.js)

- **Role**: User interaction, visualization, and monitoring.
- **Key Features**:
  - **Studio**: Flow creation and management.
  - **Chat Interface**: Interaction with agents.
  - **Graph Visualizer**: Real-time rendering of LangGraph topology via `reactflow`.

### 2. Backend API (FastAPI)

- **Role**: Entry point for all operations.
- **Key Endpoints**:
  - `/jobs`: Submit new tasks.
  - `/stream`: Real-time Server-Sent Events (SSE) for agent thoughts and status.
  - `/agents`: List available capabilities.
  - `/infrastructure`: Manage S3/Workspace config.
  - `/history`: Retrieve conversation logs and checkpoints.

### 3. Orchestrator (LangGraph)

- **Role**: Manages the state machine and decision logic.
- **Nodes**:
  - `preprocess`: Input validation and PII masking.
  - `supervisor`: Dynamic routing based on agent capabilities.
  - `execute_agent`: Bridge to CrewAI for task execution.
  - `qa`: Final answer synthesis.

### 4. Execution Engine (CrewAI)

- **Role**: Hosts specific agents (Coder, Researcher, Reviewer).
- **Registry**: Loads agent definitions dynamically from DB/Config.
- **Context**: Maintains thread-specific context and memory.

### 5. Infrastructure Layer

- **Workspace**: Sandboxed directories in `/tmp/mnabaa/workspace/{thread_id}`.
- **Persistence**:
  - **Structured Data**: PostgreSQL (`conversations`, `step_logs`).
  - **Unstructured Data**: Local Filesystem / S3.
