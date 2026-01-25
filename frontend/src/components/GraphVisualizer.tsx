import React, { useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  NodeProps,
  MarkerType,
  ConnectionLineType,
  BaseEdge,
  EdgeLabelRenderer,
  EdgeProps,
  getBezierPath,
  getSmoothStepPath,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  Brain,
  Cpu,
  Layers,
  LayoutTemplate,
  Terminal,
  ShieldAlert,
  Zap,
  CheckCircle2,
  GitBranch,
  Search,
  MessageSquare,
  Database,
} from 'lucide-react';

// --- Utility: Tailwind Merger ---
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- Types ---
// Assuming the shape of your incoming data based on the screenshot/context
export interface VisitedNode {
  id: string;
  label: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  timestamp: string;
  checkpoint_id?: string;
  parentCheckpointId?: string;
  stepName?: string; // Optional context
}

interface GraphVisualizerProps {
  visitedNodes: VisitedNode[];
  activeNodes: string[]; // IDs of currently active steps
  onStepClick: (step: { name: string; checkpointId?: string }) => void;
  onRerun: (checkpointId: string, newInput?: string, stepName?: string) => void;
}

// --- 1. Layout Engine (The "No Overlap" Secret) ---
// We use Dagre to calculate mathematically perfect positions
const nodeWidth = 280;
const nodeHeight = 100;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // Direction: Top to Bottom (TB). Ranksep: Gap between rows. Nodesep: Gap between nodes.
  dagreGraph.setGraph({ rankdir: 'TB', ranksep: 120, nodesep: 60 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      // We pass the computed position to React Flow
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// --- 2. Custom "Cyber" Node Component ---

const CyberNode = React.memo(({ data, selected }: NodeProps) => {
  const { label, status, type, timestamp, isLatest } = data;

  const isRunning = status === 'running';
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed';

  // Dynamic Icon Selection
  const getIcon = () => {
    const l = label.toLowerCase();
    if (l.includes('supervisor')) return <Brain className="text-cyan-400" size={24} />;
    if (l.includes('preprocess') || l.includes('gate'))
      return <GitBranch className="text-violet-400" size={24} />;
    if (l.includes('qa') || l.includes('critic'))
      return <ShieldAlert className="text-emerald-400" size={24} />;
    if (l.includes('search')) return <Search className="text-blue-400" size={20} />;
    if (l.includes('file')) return <Database className="text-amber-400" size={20} />;
    return <Terminal className="text-slate-400" size={20} />;
  };

  // Dynamic Styles based on Role and Status
  const getStyles = () => {
    if (label.toLowerCase().includes('supervisor')) {
      return {
        wrapper: 'border-cyan-500/50 bg-slate-900/90 shadow-[0_0_30px_-5px_rgba(6,182,212,0.3)]',
        header: 'text-cyan-100',
        glow: 'shadow-[0_0_20px_rgba(6,182,212,0.6)]',
      };
    }
    if (isFailed) {
      return {
        wrapper: 'border-red-500/60 bg-red-950/40 shadow-[0_0_20px_-5px_rgba(239,68,68,0.4)]',
        header: 'text-red-100',
        glow: 'shadow-[0_0_20px_rgba(239,68,68,0.6)]',
      };
    }
    return {
      wrapper: 'border-slate-700 bg-slate-950/80 hover:border-slate-500',
      header: 'text-slate-200',
      glow: 'shadow-[0_0_15px_rgba(255,255,255,0.2)]',
    };
  };

  const styles = getStyles();

  return (
    <div
      className={cn(
        'group relative flex h-24 w-[280px] items-center gap-4 rounded-xl border-2 px-5 py-3 backdrop-blur-xl transition-all duration-300',
        styles.wrapper,
        selected ? `border-white/40 ${styles.glow} z-10 scale-105` : '',
        isRunning ? 'animate-pulse border-cyan-400/80 shadow-[0_0_30px_rgba(6,182,212,0.4)]' : ''
      )}
    >
      {/* Input Handle (Top) */}
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-16 !rounded-t-none !rounded-b-lg !border-0 !bg-slate-700 transition-colors group-hover:!bg-slate-500"
      />

      {/* Icon Area */}
      <div
        className={cn(
          'flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-black/20',
          isRunning && 'animate-spin-slow' // Optional custom spin class
        )}
      >
        {getIcon()}
      </div>

      {/* Content Area */}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center justify-between">
          <span
            className={cn('truncate text-xs font-bold tracking-widest uppercase', styles.header)}
          >
            {label}
          </span>
          {isLatest && (
            <div className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_8px_cyan]" />
          )}
        </div>

        <div className="flex items-center justify-between">
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wide uppercase',
              isRunning
                ? 'bg-cyan-500/20 text-cyan-300'
                : isCompleted
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : isFailed
                    ? 'bg-red-500/20 text-red-300'
                    : 'bg-slate-800 text-slate-400'
            )}
          >
            {status}
          </span>
          <span className="font-mono text-[10px] text-slate-500">
            {new Date(timestamp).toLocaleTimeString([], {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </span>
        </div>
      </div>

      {/* Output Handle (Bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-16 !rounded-t-lg !rounded-b-none !border-0 !bg-slate-700 transition-colors group-hover:!bg-slate-500"
      />
    </div>
  );
});
CyberNode.displayName = 'CyberNode';

// --- 3. Custom Animated Edge ---
// Uses SmoothStep for clean orthogonal lines, plus SVG animation for active data flow

const AnimatedSmartEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 20, // Smooth corners
  });

  const isRunning = data?.active;

  return (
    <>
      {/* Background glow path */}
      <BaseEdge
        path={edgePath}
        style={{ strokeWidth: 4, stroke: isRunning ? 'rgba(6,182,212,0.1)' : 'transparent' }}
      />

      {/* Main Path */}
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          strokeWidth: 2,
          stroke: isRunning ? '#22d3ee' : '#475569', // Cyan if running, Slate if idle
          filter: isRunning ? 'drop-shadow(0 0 4px rgba(34,211,238,0.5))' : undefined,
          transition: 'all 0.5s ease',
        }}
      />

      {/* Data Packet Animation */}
      {isRunning && (
        <circle r="4" fill="#fff">
          <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
  );
};

const nodeTypes = { cyber: CyberNode };
const edgeTypes = { smart: AnimatedSmartEdge };

// --- 4. Main Component ---

export function GraphVisualizer({
  visitedNodes,
  activeNodes,
  onStepClick,
  onRerun,
}: GraphVisualizerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Data Transformation Logic
  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    if (!visitedNodes.length) return { layoutedNodes: [], layoutedEdges: [] };

    // 1. Convert VisitedNodes to ReactFlow Nodes
    // We group by ID to avoid duplicates, keeping the *latest* status
    const nodeMap = new Map<string, Node>();

    visitedNodes.forEach((vNode) => {
      // Determine if this is the currently active node in the real-time execution
      const isActive = activeNodes.includes(vNode.id);

      const node: Node = {
        id: vNode.id,
        type: 'cyber',
        data: {
          label: vNode.label || vNode.id,
          status: vNode.status,
          timestamp: vNode.timestamp,
          isLatest: isActive,
          checkpointId: vNode.checkpoint_id,
        },
        position: { x: 0, y: 0 }, // Initial, will be overridden by Dagre
      };
      nodeMap.set(vNode.id, node);
    });

    const rawNodes = Array.from(nodeMap.values());

    // 2. Build Edges based on Checkpoint Parentage
    const rawEdges: Edge[] = [];
    const nodeIds = new Set(nodeMap.keys());
    const edgeFingerprints = new Set<string>();

    // Helper to map checkpoint -> nodeId
    const checkpointToNode = new Map<string, string>();
    visitedNodes.forEach((n) => {
      if (n.checkpoint_id) checkpointToNode.set(n.checkpoint_id, n.id);
    });

    visitedNodes.forEach((node) => {
      if (node.parentCheckpointId) {
        const parentId = checkpointToNode.get(node.parentCheckpointId);

        // Ensure both nodes exist in our current graph view
        if (parentId && nodeIds.has(parentId) && parentId !== node.id) {
          const edgeId = `${parentId}-${node.id}`;

          if (!edgeFingerprints.has(edgeId)) {
            edgeFingerprints.add(edgeId);

            // Check if source or target is active to animate the edge
            const isFlowActive = activeNodes.includes(node.id) && node.status === 'running';

            rawEdges.push({
              id: edgeId,
              source: parentId,
              target: node.id,
              type: 'smart',
              animated: false, // We use custom SVG animation inside the component
              data: { active: isFlowActive },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: isFlowActive ? '#22d3ee' : '#475569',
              },
            });
          }
        }
      }
    });

    // 3. Apply Dagre Layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(rawNodes, rawEdges);
    return { layoutedNodes, layoutedEdges };
  }, [visitedNodes, activeNodes]);

  // Sync state when data changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  return (
    <div className="relative h-[85vh] w-full overflow-hidden rounded-xl border border-slate-800 bg-[#020617] shadow-2xl">
      {/* Ambient Background Grid */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:40px_40px] opacity-20" />

      {/* Radial Gradient overlay for depth */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(6,182,212,0.05)_0%,transparent_70%)]" />

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          onStepClick({
            name: node.id,
            checkpointId: node.data.checkpointId,
          });
        }}
        fitView
        fitViewOptions={{ padding: 0.2, minZoom: 0.1, maxZoom: 1.5 }}
        minZoom={0.2}
        maxZoom={2}
        connectionLineType={ConnectionLineType.SmoothStep}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls
          showInteractive={false}
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          }}
        />
      </ReactFlow>

      {/* Header Overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-col">
        <h2 className="flex items-center gap-2 text-xl font-bold tracking-tight text-white">
          <ActivityIcon />
          Agent Neural Graph
        </h2>
        <div className="mt-1 font-mono text-xs text-slate-500">
          LIVE EXECUTION TRACE // AUTOMATED LAYOUT
        </div>
      </div>
    </div>
  );
}

// Simple Icon Component for the header
const ActivityIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="text-cyan-500"
  >
    <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
  </svg>
);
