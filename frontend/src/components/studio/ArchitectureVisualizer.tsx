import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { GraphConfig } from '@/lib/api';
import { User, Bot, Network, BrainCircuit, Layers, AlertCircle } from 'lucide-react';

const nodeWidth = 250;
const nodeHeight = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({ rankdir: 'LR', ranksep: 100, nodesep: 50 });

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
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: newNodes, edges };
};

const CustomNode = ({ data }: { data: { label: string; type: string } }) => {
  // Determine Type-based Styling
  const type = data.type?.toLowerCase() || '';
  const label = data.label?.toLowerCase() || '';

  let Icon = Bot;
  let colorClass = 'text-blue-400 bg-blue-500/20';
  let borderClass = 'border-blue-500/30';

  // Use local variable for display to avoid mutating props
  let displayLabel = data.label;

  // Defensive: Handle undefined or invalid types
  if (!type || type === 'undefined' || !label || label === 'undefined') {
    Icon = AlertCircle;
    colorClass = 'text-red-400 bg-red-500/20';
    borderClass = 'border-red-500/50';
    // Override label for clarity
    if (label === 'undefined') displayLabel = 'Unknown Node';
  } else if (
    type.includes('supervisor') ||
    label.includes('supervisor') ||
    label.includes('manager')
  ) {
    Icon = BrainCircuit;
    colorClass = 'text-purple-400 bg-purple-500/20';
    borderClass = 'border-purple-500/50';
  } else if (type.includes('team') || type.includes('workflow') || label.includes('team')) {
    Icon = Network;
    colorClass = 'text-orange-400 bg-orange-500/20';
    borderClass = 'border-orange-500/50';
  } else if (type.includes('research') || type.includes('analyze')) {
    Icon = Layers;
    colorClass = 'text-indigo-400 bg-indigo-500/20';
    borderClass = 'border-white/20';
  } else if (type.includes('qa') || type.includes('quality')) {
    Icon = User;
    colorClass = 'text-green-400 bg-green-500/20';
    borderClass = 'border-white/20';
  }

  return (
    <div
      className={`flex min-w-[150px] items-center gap-2 rounded-lg border bg-[#1a1a1a] px-4 py-2 shadow-lg transition-all hover:border-white/40 ${borderClass}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-white/50" />
      <div className={`rounded p-2 ${colorClass}`}>
        <Icon size={16} />
      </div>
      <div>
        <div className="text-[10px] font-bold tracking-wider text-white/50 uppercase">
          {data.type}
        </div>
        <div className="text-sm font-bold text-white">{displayLabel}</div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-white/50" />
    </div>
  );
};

interface ArchitectureVisualizerProps {
  config: GraphConfig;
  onNodeClick?: (nodeId: string, nodeType: string, nodeLabel: string) => void;
}

const nodeTypes = {
  custom: CustomNode,
};

export function ArchitectureVisualizer({ config, onNodeClick }: ArchitectureVisualizerProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!config) return { nodes: [], edges: [] };

    const nodes: Node[] = config.nodes.map((n) => ({
      id: n.id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: { label: n.id, type: n.type },
    }));

    const edges: Edge[] = config.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: '#a855f7', strokeWidth: 2 },
    }));

    return getLayoutedElements(nodes, edges);
  }, [config]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="h-full w-full overflow-hidden rounded-xl border border-white/5 bg-black/20">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => {
          if (onNodeClick) {
            onNodeClick(node.id, node.data.type, node.data.label);
          }
        }}
      >
        <Background color="#ffffff" gap={20} size={1} style={{ opacity: 0.1 }} />
        <Controls className="border-white/10 bg-black/50" />
      </ReactFlow>
    </div>
  );
}
