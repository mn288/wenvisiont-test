import { StepLog, LogEntry, TopologyNode } from '@/lib/api';

export interface VisitedNode {
  id: string;
  label: string;
  timestamp: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  input?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  output?: any;
  status?: 'running' | 'completed' | 'failed' | 'interrupted';
  checkpoint_id?: string;
  parentCheckpointId?: string;
  /** Unique identifier for this specific node execution (step_name + checkpoint_id or timestamp) */
  uid: string;
  /** For forked nodes, the uid of the parent node they branched from */
  forkParentUid?: string;
}

export interface ReconstructedState {
  logs: LogEntry[];
  content: Record<string, string>;
  visited: VisitedNode[];
  response: string | null;
}

export function reconstructStateFromLogs(
  stepLogs: StepLog[],
  topology: TopologyNode[] = []
): ReconstructedState {
  const restoredLogs: LogEntry[] = [];
  const restoredContent: Record<string, string> = {};
  const restoredVisited: VisitedNode[] = [];

  // Set of known checkpoints to avoid duplicating visual nodes if logs are messy
  const seenCheckpoints = new Set<string>();

  // 1. First Pass: Build Skeleton from Topology (Source of Truth for Graph)
  // If provided, we use this to ensure every checkpoint is represented
  topology.forEach((tNode) => {
    // Hide internal node __start__ and __end__ ?
    if (tNode.node === '__start__') return;

    const timestamp = new Date(tNode.created_at).getTime();

    if (tNode.parallel_nodes && tNode.parallel_nodes.length > 0) {
      // Flatten combined node into individual visual nodes
      tNode.parallel_nodes.forEach((subNode) => {
        restoredVisited.push({
          id: subNode,
          label: subNode.charAt(0).toUpperCase() + subNode.slice(1),
          timestamp: timestamp,
          status: 'completed',
          checkpoint_id: tNode.id,
          parentCheckpointId: tNode.parent_id || undefined,
          uid: `${tNode.id}_${subNode}`, // Synthetic UID for parallel siblings
        });
      });
      seenCheckpoints.add(tNode.id);
    } else {
      const nodeName = tNode.node || 'unknown';
      restoredVisited.push({
        id: nodeName,
        label: nodeName.charAt(0).toUpperCase() + nodeName.slice(1),
        timestamp: timestamp,
        status: 'completed',
        checkpoint_id: tNode.id,
        parentCheckpointId: tNode.parent_id || undefined,
        uid: `${tNode.id}_${nodeName}`, // Consistent UID format
      });
      seenCheckpoints.add(tNode.id);
    }
  });

  // 2. Second Pass: Process Logs to fill content and add any missing nodes (e.g. streaming partials)
  stepLogs.forEach((log) => {
    // A. Reconstruct Content / messages
    if (['token', 'thought', 'info', 'output', 'message'].includes(log.log_type)) {
      const skipPhrases = ['Finalizing...', 'Planning Tool...', 'Orchestrating...', 'Validating:'];

      const isStatusMessage = skipPhrases.some((phrase) => log.content.startsWith(phrase));

      if (!isStatusMessage && (log.step_name === 'qa' || log.step_name === 'preprocess')) {
        restoredContent[log.step_name] = (restoredContent[log.step_name] || '') + log.content;
      }
    }

    // Ignore __start__ logs for visited nodes
    if (log.step_name === '__start__' || log.step_name === '__START__') return;

    // B. Reconstruct Visited Nodes (if not in topology)
    if (log.log_type === 'node_start') {
      const timestamp = new Date(log.created_at).getTime();

      // Check if we already have a node for this checkpoint/step
      // (Topology pass might have added it, possibly with parallel suffix logic, OR it's a new streaming node)

      // If checkpoint_id exists, we check if ANY node with that checkpoint_id AND step_name exists.
      // UID format in Pass 1: ${tNode.id}_${subNode} or ${tNode.id}_${nodeName}
      // If log comes in, we want to match:
      // if log.step_name == "senior_python_engineer", check if visited has cid=X and id="senior_python_engineer"

      const existingNode = restoredVisited.find((v) => {
        if (log.checkpoint_id) {
          return v.checkpoint_id === log.checkpoint_id && v.id === log.step_name;
        }
        // If no checkpoint_id in log (legacy?), fallback to timestamp/name dedup
        return v.id === log.step_name && Math.abs(v.timestamp - timestamp) < 1000;
      });

      if (!existingNode) {
        // Add new node found in logs but not topological history (e.g. active stream)
        const uid = log.checkpoint_id
          ? `${log.checkpoint_id}_${log.step_name}`
          : `${log.step_name}_${timestamp}`;

        restoredVisited.push({
          id: log.step_name,
          label: log.step_name.charAt(0).toUpperCase() + log.step_name.slice(1),
          timestamp,
          status: 'completed',
          checkpoint_id: log.checkpoint_id || undefined,
          parentCheckpointId: log.parent_checkpoint_id || undefined,
          uid,
        });
        if (log.checkpoint_id) seenCheckpoints.add(log.checkpoint_id);
      }

      restoredLogs.push({
        id: log.id.toString(),
        timestamp: new Date(log.created_at),
        type: 'node-start',
        message: `Activating Node: ${log.step_name.toUpperCase()}`,
        node: log.step_name,
      });
    } else {
      // Just add to logs
      restoredLogs.push({
        id: log.id.toString(),
        timestamp: new Date(log.created_at),
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        type: log.log_type as any, // lazy cast
        message: log.content,
        node: log.step_name,
      });
    }
  });

  // Sort visited by time to help layout (Dagre handles topo, but order helps)
  restoredVisited.sort((a, b) => a.timestamp - b.timestamp);

  // Restore final response
  let response = null;
  if (restoredContent['qa']) response = restoredContent['qa'];
  else if (restoredContent['preprocess']) response = restoredContent['preprocess'];

  return {
    logs: restoredLogs,
    content: restoredContent,
    visited: restoredVisited,
    response: response,
  };
}
