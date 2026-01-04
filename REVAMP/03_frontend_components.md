# Frontend Component Plan - The Command Center

## Overview

The frontend (Next.js 14) requires new pages for the "Agent Studio" and "Superagent Management".

## 1. Directory Structure

```
src/
  app/
    studio/                  # New Layout for Builders
      page.tsx               # Dashboard
      create/                # The Creation Flow
        page.tsx
      [id]/                  # Superagent Details
        page.tsx
        api-access/          # API Key Management
        logs/                # Run History
```

## 2. Key Components (`src/components/studio/`)

### `ArchitectureVisualizer.tsx`

- **Lib**: React Flow.
- **Props**: `GraphConfig`.
- **Features**:
  - Auto-layout (Dagre/Elk) to organize nodes.
  - Interactive: Click node to see/edit details.
  - Status Indication: Show "Thinking", "Running", "Done" states during testing.

### `PromptToAgentWizard.tsx`

- **Step 1**: Text Area ("Describe your workforce").
- **Step 2**: "Architecting..." (Skeleton loader).
- **Step 3**: Display `ArchitectureVisualizer`.
  - Action: "Refine" (Chat with Architect to tweak).
  - Action: "Deploy".

### `ApiAccessPanel.tsx`

- Display: `Endpoint URL` (copyable).
- Display: `API Key` (masked, click to reveal).
- Action: "Rotate Key" (Critical for security).
- Code Snippets: Show `curl` and `python` examples.

## 3. State Management

- **Store**: Zustand `useBuilderStore`.
- **State**: `currentDraftConfig`, `isGenerating`, `validationErrors`.

## Measurable Deliverables

- [ ] **Page**: `/studio/create` functional.
- [ ] **Visualizer**: React Flow rendering a complex JSON graph correctly.
- [ ] **Integration**: Front-to-Back connection for `POST /superagents`.
