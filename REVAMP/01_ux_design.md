# UX/UI Design Plan - The Agent Studio

## Overview

The UX shifts from "Chatting with an Assistant" to "Building a Digital Workforce". The user persona is a **Financial Tools Administrator** or **Senior Analyst**.

## 1. The Dashboard (Command Center)

**Goal**: Overview of active Superagents and System Health.

- **Metric**: Show "Active Superagents", "Total Invocations", "Avg Latency".
- **List View**: Card-based list of Superagents (e.g., "Risk Analyzer v1", "Weekly Reporter").
- **Action**: prominent "Create New Superagent" button.

## 2. The Creation Flow (Chat-to-Architecture)

**Goal**: Seamlessly translate intent into structure.

1.  **Prompt**: User enters "I need a system to read annual reports and flag ESG risks."
2.  **Thinking Phase**: UI shows "Architect is analyzing requirements..." -> "Designing Workflow..." -> "Selecting Tools...".
3.  **Review Phase (Critical)**:
    - Display a **Visual Graph** (Nodes = Agents, Edges = Flow).
    - Example: `[PDF Reader] --> [ESG Analyst] --> [Risk Scorer] --> [Result]`
    - **Edit Mode**: User can click a Node to change its "System Prompt" or "Tools".
4.  **Confirm**: User clicks "Deploy Superagent".

## 3. The Superagent Details View

**Goal**: Management and Exposure.

- **Tabs**:
  - **Overview**: Name, Description, Stats.
  - **API**: "Enable API Access" toggle. Show Endpoint (`https://api.sfeir.dev/v1/agents/{id}/invoke`) and "Generate Key".
  - **Logs**: Audit trail of execution history.
  - **Settings**: Update Prompts, Change Model (e.g., switch to GPT-4o).

## 4. The "Run" Playground

**Goal**: Test before external use.

- A built-in chat interface to manually invoke the Superagent with test inputs (e.g., upload a PDF).
- Visual Trace: Show the graph lighting up as the request progresses.

## Measurable Deliverables

- [ ] **Wireframes**: Figma sketches for Creation Flow.
- [ ] **Component**: `GraphEditor.tsx` (Interactive React Flow).
- [ ] **Component**: `ApiGatewayPanel.tsx` (Key management).
