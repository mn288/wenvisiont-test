import React, { useCallback, useEffect, useState } from 'react';
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
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { clsx } from 'clsx';
import {
  Activity,
  Brain,
  Cpu,
  FileText,
  ListStart,
  Network,
  RotateCcw,
  Search,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { VisitedNode } from '@/lib/state-utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// --- Utils ---

const nodeWidth = 220;
const nodeHeight = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 100, // Increased for better horizontal separation of forks
    ranksep: 100, // Increased for better vertical/horizontal hierarchy
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: direction === 'LR' ? Position.Left : Position.Top,
      sourcePosition: direction === 'LR' ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: newNodes, edges };
};

const getIconForNode = (label: string) => {
  const lower = label.toLowerCase();
  if (lower.includes('research')) return Search;
  if (lower.includes('analyst') || lower.includes('analyze')) return FileText;
  if (lower.includes('strateg')) return Network;
  if (lower.includes('critic') || lower.includes('qa')) return ShieldCheck;
  if (lower.includes('super')) return ListStart;
  if (lower.includes('gate') || lower.includes('pre')) return Brain;
  if (lower.includes('tool')) return Cpu;
  return Activity;
};

// --- Custom Components ---

const CustomNode = React.memo(({ data, id }: NodeProps) => {
  const IconComponent = getIconForNode(data.label);
  const isRunning = data.status === 'running';
  const isCompleted = data.status === 'completed';
  const isFailed = data.status === 'failed';
  const isActive = data.active;

  return (
    <div
      className={clsx(
        'relative flex min-w-[200px] items-center rounded-xl border-2 p-3 backdrop-blur-md transition-all duration-300',
        data.isSelected
          ? 'border-purple-500 bg-purple-500/20 shadow-[0_0_25px_-5px_rgb(168,85,247)]'
          : data.isInPath
            ? 'border-purple-400/50 bg-purple-900/30 shadow-[0_0_15px_-3px_rgb(168,85,247)]'
            : isActive
              ? 'border-primary bg-black/80 shadow-[0_0_20px_-5px_var(--color-primary)]'
              : 'border-white/10 bg-black/60 hover:border-white/30',
        isRunning && 'border-secondary animate-pulse shadow-[0_0_15px_-3px_var(--color-secondary)]',
        isCompleted && !isActive && !data.isInPath && 'border-green-500/30 text-green-100',
        isFailed && 'border-red-500/50'
      )}
    >
      <Handle type="target" position={Position.Left} className="!h-3 !w-3 !border-0 !bg-white/20" />

      <div
        className={clsx(
          'mr-3 flex h-10 w-10 items-center justify-center rounded-lg shadow-inner',
          isActive ? 'bg-primary/20 text-primary' : 'text-muted-foreground bg-white/5',
          isRunning && 'text-secondary bg-secondary/10',
          isCompleted && !isActive && 'bg-green-500/10 text-green-400'
        )}
      >
        {React.createElement(IconComponent, { size: 20 })}
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex items-center justify-between">
          <span className="mr-2 truncate text-xs font-bold tracking-wider text-white/90 uppercase">
            {data.label}
          </span>
          {data.onRerun && !['preprocess', 'supervisor'].some((r: string) => id.includes(r)) && (
            <div
              role="button"
              title="Fork from here"
              onClick={(e) => {
                e.stopPropagation();
                data.onRerun(data.checkpointId, undefined, data.stepName);
              }}
              className="bg-primary/20 hover:bg-primary text-primary rounded p-1 transition-colors hover:text-white"
            >
              <RotateCcw size={10} />
            </div>
          )}
        </div>

        <div className="text-muted-foreground flex items-center gap-2 font-mono text-[10px]">
          {isRunning ? (
            <span className="text-secondary flex items-center gap-1">
              <Activity size={8} className="animate-spin" /> Running
            </span>
          ) : isCompleted ? (
            <span className="flex items-center gap-1 text-green-400">
              <CheckCircle2 size={8} /> Completed
            </span>
          ) : (
            <span className="flex items-center gap-1 text-red-400">
              <AlertCircle size={8} /> Failed
            </span>
          )}
          <span className="opacity-50">
            {new Date(data.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              fractionalSecondDigits: undefined,
            })}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !border-0 !bg-white/20"
      />
    </div>
  );
});
CustomNode.displayName = 'CustomNode';

// --- Main Component ---

interface GraphVisualizerProps {
  visitedNodes: VisitedNode[];
  activeNodes: string[];
  onStepClick: (step: { name: string; checkpointId?: string }) => void;
  onRerun: (checkpointId: string, newInput?: string, stepName?: string) => void;
  agentMap?: Record<string, string>;
}

const nodeTypes = {
  custom: CustomNode,
};

const proOptions = { hideAttribution: true };

export function GraphVisualizer({
  visitedNodes,
  activeNodes,
  onStepClick,
  onRerun,
  agentMap = {},
}: GraphVisualizerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeUid, setSelectedNodeUid] = useState<string | null>(null);
  const [hoveredNodeUid, setHoveredNodeUid] = useState<string | null>(null);

  // Rerun Dialog State
  const [rerunDialog, setRerunDialog] = useState<{
    isOpen: boolean;
    checkpointId: string;
    nodeId: string;
  }>({
    isOpen: false,
    checkpointId: '',
    nodeId: '',
  });
  const [rerunInput, setRerunInput] = useState('');

  const handleRerunClick = useCallback((checkpointId: string, _?: string, nodeId?: string) => {
    setRerunDialog({ isOpen: true, checkpointId, nodeId: nodeId || '' });
  }, []);

  const confirmRerun = () => {
    if (rerunDialog.checkpointId) {
      onRerun(rerunDialog.checkpointId, rerunInput || undefined, rerunDialog.nodeId);
    }
    setRerunDialog((prev) => ({ ...prev, isOpen: false }));
    setRerunInput('');
  };

  // Helper to trace path from root to a specific node UID
  const tracePath = useCallback((targetUid: string, visitedNodes: VisitedNode[]): Set<string> => {
    const pathUids = new Set<string>();
    const uidToNode = new Map(visitedNodes.map((n) => [n.uid, n]));

    let currentUid: string | undefined = targetUid;
    while (currentUid) {
      pathUids.add(currentUid);
      const node = uidToNode.get(currentUid);
      if (!node || !node.parentCheckpointId) break;

      // Find parent node(s) with matching checkpoint
      const parentNode = visitedNodes.find((n) => n.checkpoint_id === node.parentCheckpointId);
      currentUid = parentNode?.uid;
    }
    return pathUids;
  }, []);

  // Transform VisitedNodes to ReactFlow Elements
  // Memoize calculation to avoid re-layouting on every render unless nodes change
  const buildGraph = useCallback(() => {
    if (visitedNodes.length === 0) return { nodes: [], edges: [] };

    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    const nodeMap = new Map<string, Node>();

    // Calculate path for either selected or hovered node (click takes precedence)
    const activeNodeUid = selectedNodeUid || hoveredNodeUid;
    const highlightedPath = activeNodeUid
      ? tracePath(activeNodeUid, visitedNodes)
      : new Set<string>();

    // 1. Create Nodes
    visitedNodes.forEach((vNode) => {
      const displayName = agentMap[vNode.id] || vNode.label || vNode.id;
      const isInPath = highlightedPath.has(vNode.uid);
      const isSelected = vNode.uid === selectedNodeUid;
      const isHovered = vNode.uid === hoveredNodeUid;

      const node: Node = {
        id: vNode.uid, // Use UID for uniqueness
        type: 'custom',
        position: { x: 0, y: 0 }, // Handled by layout
        data: {
          label: displayName,
          status: vNode.status,
          timestamp: vNode.timestamp,
          stepName: vNode.id,
          active: activeNodes.includes(vNode.id) && vNode.status === 'running', // Only highlight if actually running
          checkpointId: vNode.checkpoint_id,
          onRerun: handleRerunClick,
          isInPath,
          isSelected,
          isHovered,
        },
      };
      newNodes.push(node);
      nodeMap.set(vNode.uid, node);
    });

    // 2. Create Edges
    // Map checkpoint_id -> uid[]
    // Because parallel nodes share the same checkpoint_id, we must map 1 checkpoint -> N UIDs
    const checkpointToUids = new Map<string, string[]>();
    visitedNodes.forEach((n) => {
      if (n.checkpoint_id) {
        const existing = checkpointToUids.get(n.checkpoint_id) || [];
        existing.push(n.uid);
        checkpointToUids.set(n.checkpoint_id, existing);
      }
    });

    // Find the latest fork point (most recent node with timestamp)
    const latestForkTimestamp =
      visitedNodes.length > 0
        ? Math.max(...visitedNodes.slice(-5).map((n) => n.timestamp)) // Last 5 nodes to identify recent fork
        : 0;
    const forkThreshold = latestForkTimestamp - 5000; // 5 second window for fork detection

    visitedNodes.forEach((node) => {
      // Strategy: Strict Parent Checkpoint Linkage
      if (node.parentCheckpointId) {
        const parentUids = checkpointToUids.get(node.parentCheckpointId);

        // If parent is visible in the graph (could be multiple if parent was parallel)
        if (parentUids && parentUids.length > 0) {
          // Lane Heuristic:
          // If we have parallel parents (Mesh), and one of them has the SAME label/agent as current node,
          // we prefer connecting to that one (Lane) instead of all of them (Mesh).
          // This cleans up "A, B -> A, B" loops into "A->A, B->B".

          const currentLabel = nodeMap.get(node.uid)?.data?.label;
          const sameLabelParents = parentUids.filter((pid) => {
            const pNode = nodeMap.get(pid);
            return pNode && pNode.data.label === currentLabel;
          });

          const parentsToConnect = sameLabelParents.length > 0 ? sameLabelParents : parentUids;

          parentsToConnect.forEach((parentUid) => {
            if (nodeMap.has(parentUid)) {
              // Determine if this edge is part of the latest fork
              const isLatestFork = node.timestamp > forkThreshold;

              // Check if this edge is part of the highlighted path
              const isInPath = highlightedPath.has(parentUid) && highlightedPath.has(node.uid);

              newEdges.push({
                id: `e-${parentUid}-${node.uid}`,
                source: parentUid,
                target: node.uid,
                animated: isLatestFork || isInPath, // Animate latest fork or path edges
                style: {
                  stroke: isInPath ? '#a855f7' : isLatestFork ? '#22d3ee' : '#ffffff30', // Purple for path, cyan for fork, white for others
                  strokeWidth: isInPath ? 3 : isLatestFork ? 2.5 : 2,
                },
                type: 'default',
              });
            }
          });
        }
      }
    });

    return getLayoutedElements(newNodes, newEdges);
  }, [
    visitedNodes,
    activeNodes,
    agentMap,
    handleRerunClick,
    selectedNodeUid,
    hoveredNodeUid,
    tracePath,
  ]);

  useEffect(() => {
    const { nodes: layoutedNodes, edges: layoutedEdges } = buildGraph();
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [buildGraph, setNodes, setEdges]);

  // Auto-Focus active node?
  // Maybe later.

  return (
    <div className="h-full min-h-[400px] w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => {
          // Toggle selection: if clicking same node, deselect; otherwise select
          setSelectedNodeUid((prev) => (prev === node.id ? null : node.id));
          onStepClick({
            name: node.data.stepName,
            checkpointId: node.data.checkpointId,
          });
        }}
        onNodeMouseEnter={(_, node) => {
          // Only show hover path if nothing is selected (click takes precedence)
          if (!selectedNodeUid) {
            setHoveredNodeUid(node.id);
          }
        }}
        onNodeMouseLeave={() => {
          setHoveredNodeUid(null);
        }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        attributionPosition="bottom-right"
        proOptions={proOptions}
      >
        <Background color="#ffffff" gap={20} size={1} style={{ opacity: 0.05 }} />
        <Controls
          className="overflow-hidden rounded-lg border border-white/10 bg-black/50 [&>button]:!border-none [&>button]:!bg-transparent [&>button]:!text-white [&>button:hover]:!bg-white/10"
          showInteractive={false}
        />
      </ReactFlow>

      <Dialog
        open={rerunDialog.isOpen}
        onOpenChange={(o) => setRerunDialog((prev) => ({ ...prev, isOpen: o }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Fork Conversation</DialogTitle>
            <DialogDescription>
              Rerun the conversation from this step. This will create a new branch in the timeline.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>New Input (Optional)</Label>
            <Input
              value={rerunInput}
              onChange={(e) => setRerunInput(e.target.value)}
              placeholder="Modify the instructions for this step..."
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRerunDialog((prev) => ({ ...prev, isOpen: false }))}
            >
              Cancel
            </Button>
            <Button onClick={confirmRerun}>Confirm Fork</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
