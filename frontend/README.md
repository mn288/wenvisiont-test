# AWP Frontend

Modern AI Agent Interface built with **Next.js 16**, **React 19**, and **TailwindCSS v4**.

## ✨ Features

- **Agent Studio**: A visual, node-based editor for designing and monitoring Agent workflows.
  - Powerd by `ReactFlow` with `Dagre` for automatic Mesh/Lane layout optimization.
  - **Live Execution Tracking**: Visualizes active paths, running states, and failures in real-time.
  - **Time Travel**: Fork/Rerun conversations from any previous step with modified inputs.
- **Smart Chat**: Real-time streaming chat interface for interacting with the Swarm.
- **Observability Dashboard**: Integrated views for tracing and debugging agent actions.
- **Dynamic UI**: Fluid animations and highly responsive design using Framer Motion.

## 🛠 Technology Stack

### Core

- **Framework**: [Next.js 16](https://nextjs.org/) (App Router).
- **UI Library**: [React 19](https://react.dev/).
- **Styling**: [TailwindCSS v4](https://tailwindcss.com/) (PostCSS).
- **Language**: TypeScript (Strict Mode).

### Components & Libraries

- **Visual Graph**: `reactflow` & `@xyflow/react` (Agent Studio).
- **UI Primitives**: Radix UI (Headless accessibility).
- **Icons**: Lucide React.
- **Markdown**: `react-markdown` with code highlighting.
- **Animations**: `framer-motion`.
- **State**: React Server Components + Client Hooks.

## 🚀 Getting Started

### Prerequisites

- Node.js 20+
- pnpm (recommended) or npm

### Local Development

1.  **Install Dependencies**:

    ```bash
    npm install
    # or
    pnpm install
    ```

2.  **Run Development Server**:
    ```bash
    npm run dev
    ```
    Access the app at `http://localhost:3000`.

## 📂 Project Structure

- `src/app`: Next.js App Router pages and layouts.
- `src/components`: Reusable UI components (in standard `shadcn` pattern).
- `src/lib`: Utility functions and API clients.
- `src/types`: TypeScript interfaces and Zod schemas.

---

Part of the **AWP** System.
