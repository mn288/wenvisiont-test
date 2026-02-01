import { useState, useRef, useEffect, useCallback } from 'react';
import { LogEntry, fetchStepHistory, fetchTopology, listAgentsSummary } from '@/lib/api';
import { reconstructStateFromLogs, VisitedNode } from '@/lib/state-utils';

const THREAD_ID_STORAGE_KEY = 'wenvision_active_thread_id';
const USER_ID_STORAGE_KEY = 'wenvision_user_id';

export const useOrchestrator = () => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [streamedContent, setStreamedContent] = useState<Record<string, any>>({});
  const [finalResponse, setFinalResponse] = useState<string | null>(null);
  const [threadId, setThreadIdInternal] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(THREAD_ID_STORAGE_KEY) || 'default';
    }
    return 'default';
  });

  // Persistent User ID
  const [userId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      let stored = localStorage.getItem(USER_ID_STORAGE_KEY);
      if (!stored) {
        stored = crypto.randomUUID();
        localStorage.setItem(USER_ID_STORAGE_KEY, stored);
      }
      return stored;
    }
    return 'anonymous';
  });

  const [isInitializing, setIsInitializing] = useState(true);

  const [visitedNodes, setVisitedNodes] = useState<VisitedNode[]>([]);
  const [agentRegistry, setAgentRegistry] = useState<
    Record<string, { role: string; label: string }>
  >({});
  const [streamingNode, setStreamingNode] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [toolCall, setToolCall] = useState<{ name: string; args: any; reasoning?: string } | null>(
    null
  );

  const eventSourceRef = useRef<EventSource | null>(null);

  // Wrapper to persist threadId to localStorage
  const setThreadId = useCallback((newThreadId: string) => {
    setThreadIdInternal(newThreadId);
    if (typeof window !== 'undefined') {
      if (newThreadId && newThreadId !== 'default') {
        localStorage.setItem(THREAD_ID_STORAGE_KEY, newThreadId);
      } else {
        localStorage.removeItem(THREAD_ID_STORAGE_KEY);
      }
    }
  }, []);

  // Fetch agents on mount
  useEffect(() => {
    listAgentsSummary()
      .then((data) => {
        const map: Record<string, { role: string; label: string }> = {};
        data.forEach((agent) => {
          map[agent.id] = { role: agent.role, label: agent.label };
        });
        setAgentRegistry(map);
      })
      .catch((err) => console.error('Failed to fetch agents:', err));

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Auto-restore conversation on mount if we have a saved threadId
  useEffect(() => {
    const restoreSession = async () => {
      if (threadId && threadId !== 'default') {
        try {
          const [logs, topology] = await Promise.all([
            fetchStepHistory(threadId),
            fetchTopology(threadId),
          ]);

          if (logs.length > 0 || topology.length > 0) {
            const {
              logs: restoredLogs,
              content: restoredContent,
              visited: restoredVisited,
              response,
            } = reconstructStateFromLogs(logs, topology);

            setLogs(restoredLogs);
            setStreamedContent(restoredContent);
            setVisitedNodes(restoredVisited);
            setFinalResponse(response);
          }
        } catch (err) {
          console.error('Failed to restore session:', err);
          // Clear invalid threadId
          setThreadId('default');
        }
      }
      setIsInitializing(false);
    };

    restoreSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  const startStream = useCallback(
    (url: string, shouldClear = true) => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      setStreamingNode(null);

      setIsLoading(true);
      // Only clear if requested (default behavior for new chats)
      if (shouldClear && !url.includes('resume_feedback')) {
        setLogs([]);
        setFinalResponse(null);
        setActiveNodes([]);
        setActiveAgent(null);
        setStreamedContent({});
        setVisitedNodes([]);
        setToolCall(null);
      }

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        const data = event.data;
        if (data === '[DONE]') {
          eventSource.close();
          eventSourceRef.current = null;
          setIsLoading(false);
          setIsPaused(false);
          setActiveNodes([]);
          setActiveAgent(null);

          const doneMsg = 'Done.';

          // Update logs
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              timestamp: new Date(),
              type: 'output',
              message: doneMsg,
              node: 'qa',
            },
          ]);

          // Update content (Report View) to match refresh behavior
          setStreamedContent((prev) => {
            const newContent = (prev['qa'] || '') + '\n\n' + doneMsg;
            return {
              ...prev,
              qa: newContent,
            };
          });
          setFinalResponse((prev) => (prev || '') + '\n\n' + doneMsg);

          return;
        }

        try {
          const parsed = JSON.parse(data);

          if (parsed.type === 'token') {
            const node = parsed.node || 'unknown';
            setStreamedContent((prev) => {
              const newContent = (prev[node] || '') + parsed.content;
              const newState = {
                ...prev,
                [node]: newContent,
              };

              // NEW: Real-time update of finalResponse for feedback nodes
              if (node === 'qa' || node === 'preprocess') {
                setFinalResponse(newContent);
              }
              return newState;
            });
          } else if (parsed.type === 'node_start') {
            const node = parsed.node;
            setActiveNodes((prev) => [...prev.filter((n) => n !== node), node]);
            if (!streamedContent[node]) {
              setStreamedContent((prev) => ({ ...prev, [node]: '' }));
            }
            setStreamingNode(node);

            let agent = null;
            let label = node;

            if (agentRegistry[node]) {
              agent = agentRegistry[node].role;
              label = node.charAt(0).toUpperCase() + node.slice(1);
            } else if (node === 'qa') {
              agent = 'Quality Assurance';
              label = 'Quality Check';
            } else if (node === 'router') {
              agent = 'Router';
              label = 'Routing';
            } else if (node === 'preprocess') {
              agent = 'Gatekeeper';
              label = 'Preprocessing';
            } else if (node === 'supervisor') {
              agent = 'Supervisor';
              label = 'Supervision';
            } else if (node === 'tool_planning' || node === 'tool_execution') {
              agent = 'MCP Tool Specialist';
              label = 'Tool Execution';
            } else if (node === 'tools') {
              agent = 'MCP Tool Specialist';
              label = 'Tool Execution';
            }

            setActiveAgent(agent);
            setLogs((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                timestamp: new Date(),
                type: 'node-start',
                message: `Activating Node: ${node.toUpperCase()}`,
                node: node,
              },
            ]);

            setVisitedNodes((prev) => {
              // Strategy: Check for duplicates more intelligently
              // 1. Check if we already have this exact node (by step name + checkpoint if available)
              // 2. Only dedupe if the last node is STILL RUNNING and matches
              // 3. Allow fork nodes (same name but different checkpoint/parent context)

              const lastNode = prev.length > 0 ? prev[prev.length - 1] : null;

              // Quick dedupe: if last node is running with same name, update it
              if (lastNode && lastNode.id === node && lastNode.status === 'running') {
                // Update existing running node with input if it was missing
                if (parsed.input && !lastNode.input) {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    input: parsed.input,
                  };
                  return updated;
                }
                return prev;
              }

              // Check if we already have a completed node with the same step_name
              // that might be from existing topology (not from streaming)
              // We should still add the new one if it's a fork/rerun
              // The parent_checkpoint_id will be different, so it's legitimate

              const timestamp = Date.now();
              // Temporary uid based on timestamp, gets updated with checkpoint_id later
              const uid = `${node}_${timestamp}`;

              return [
                ...prev,
                {
                  id: node,
                  label,
                  timestamp,
                  input: parsed.input,
                  status: 'running',
                  parentCheckpointId: parsed.parent_checkpoint_id,
                  uid,
                },
              ];
            });
          } else if (parsed.type === 'node_end') {
            const node = parsed.node;
            setActiveNodes((prev) => prev.filter((n) => n !== node));
            setStreamingNode((prev) => (prev === node ? null : prev));

            // Update visited node with output and completions status
            setVisitedNodes((prev) => {
              const newVisited = [...prev];
              const lastIndex = newVisited.map((n) => n.id).lastIndexOf(node);
              if (lastIndex !== -1) {
                newVisited[lastIndex] = {
                  ...newVisited[lastIndex],
                  output: parsed.output,
                  status: 'completed',
                };
              }
              return newVisited;
            });

            if (node === 'qa' || node === 'preprocess') {
              // Prefer constructed streamed content if available (matches refresh logic)
              if (streamedContent[node]) {
                setFinalResponse(streamedContent[node]);
              } else if (parsed.output) {
                // Fallback to parsed output logic
                let outputStr = parsed.output;

                // If output is an object, extract the actual text content
                if (typeof parsed.output === 'object') {
                  // Try to find text content in common field names
                  if (parsed.output.output) {
                    outputStr = parsed.output.output;
                  } else if (parsed.output.content) {
                    outputStr = parsed.output.content;
                  } else if (parsed.output.text) {
                    outputStr = parsed.output.text;
                  } else if (parsed.output.result) {
                    outputStr = parsed.output.result;
                  } else {
                    // Fallback: stringify as JSON only if we can't find text content
                    outputStr = '```json\n' + JSON.stringify(parsed.output, null, 2) + '\n```';
                  }
                }

                setFinalResponse(outputStr);
              }
            }
          } else if (parsed.type === 'checkpoint') {
            // Dedicated checkpoint event to update IDs
            const { node, checkpoint_id, parent_checkpoint_id } = parsed;
            setVisitedNodes((prev) => {
              const newVisited = [...prev];
              // Find the last instance of this node (it just finished)
              const lastIndex = newVisited.map((n) => n.id).lastIndexOf(node);
              if (lastIndex !== -1) {
                // Update uid to use checkpoint_id for stable identification
                const newUid = checkpoint_id
                  ? `${node}_${checkpoint_id}`
                  : newVisited[lastIndex].uid;
                newVisited[lastIndex] = {
                  ...newVisited[lastIndex],
                  checkpoint_id: checkpoint_id,
                  parentCheckpointId: parent_checkpoint_id,
                  uid: newUid,
                };
              }
              return newVisited;
            });
          } else if (parsed.type === 'interrupt') {
            eventSource.close();
            eventSourceRef.current = null;
            setIsPaused(true);
            setIsLoading(false);

            if (parsed.tool_call) {
              setToolCall(parsed.tool_call);
              setActiveNodes(['tool_execution']);
              setActiveAgent('MCP Tool Specialist');
            }

            if (parsed.next && parsed.next.includes('qa')) {
              setActiveNodes(['qa']);
              setActiveAgent('Quality Assurance');

              // Display QA preview content if available
              if (parsed.qa_preview) {
                const preview = parsed.qa_preview;
                let previewContent = '## Quality Check Ready\n\n';
                previewContent += '### Aggregated Findings:\n\n';

                if (preview.results && preview.results.length > 0) {
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  preview.results.forEach((result: any) => {
                    const role = result.metadata?.agent_role || 'Agent';
                    previewContent += `**${role}:**\n${result.summary}\n\n`;
                  });
                }

                if (preview.context) {
                  previewContent += `\n### Additional Context:\n${preview.context}\n`;
                }

                // Store preview as streamed content for QA node
                setStreamedContent((prev) => ({
                  ...prev,
                  qa: previewContent,
                }));
              }
            }

            setLogs((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                timestamp: new Date(),
                type: 'info',
                message: 'Halted: Human Feedback Required',
              },
            ]);
          } else if (parsed.type === 'error') {
            eventSource.close();
            eventSourceRef.current = null;
            setIsLoading(false);
            setIsPaused(false);
            setLogs((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                timestamp: new Date(),
                type: 'error',
                message: `Error: ${parsed.content}`,
              },
            ]);
            // Also set final response to error to make it visible in main view
            setFinalResponse(`### Execution Error\n\n${parsed.content}`);
          }
        } catch (e) {
          console.error('Parse error', e);
        }
      };

      eventSource.onerror = (e) => {
        console.error('EventSource failed', e);
        eventSource.close();
        eventSourceRef.current = null;
        setIsLoading(false);
        setIsPaused(false);
        setLogs((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            timestamp: new Date(),
            type: 'error',
            message: 'Network Error: Connection Lost',
          },
        ]);
      };
    },
    [agentRegistry, streamedContent]
  );

  const handleStart = useCallback(() => {
    const newThreadId = `thread_${Date.now()}`;
    setThreadId(newThreadId);
    startStream(
      `http://localhost:8000/stream?input_request=${encodeURIComponent(input)}&thread_id=${newThreadId}&user_id=${userId}`
    );
  }, [input, startStream, setThreadId, userId]);

  const handleResume = useCallback(() => {
    setIsPaused(false);
    setLogs((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        timestamp: new Date(),
        type: 'system',
        message: 'Authorization Received. Resuming Operation...',
      },
    ]);
    startStream(
      `http://localhost:8000/stream?resume_feedback=approved&thread_id=${threadId}&user_id=${userId}`
    );
  }, [threadId, startStream, userId]);

  const handleReset = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
    setIsPaused(false);
    setActiveNodes([]);
    setActiveAgent(null);
    setLogs([]);
    setVisitedNodes([]);
    setFinalResponse(null);
    setStreamedContent({});
    setThreadId('default');
    setInput('');
  }, [setThreadId]);

  // Setters for restoration
  const restoreState = useCallback(
    (
      newThreadId: string,
      newInput: string,
      logs: LogEntry[],
      content: Record<string, string>,
      visited: VisitedNode[],
      response: string | null
    ) => {
      setThreadId(newThreadId);
      setInput(newInput);
      setLogs(logs);
      setStreamedContent(content);
      setVisitedNodes(visited);
      setFinalResponse(response);
    },
    [setThreadId]
  );

  return {
    state: {
      input,
      isLoading: isLoading || isInitializing,
      isPaused,
      activeNodes,
      activeAgent,
      logs,
      streamedContent,
      finalResponse,
      threadId,
      visitedNodes,
      agentRegistry,
      streamingNode,
      toolCall,
      isInitializing,
    },
    actions: {
      setInput,
      handleStart,
      handleResume,
      handleReset,
      restoreState,
      startStream,
      setLogs,
      setIsLoading,
      setIsPaused,

      setStreamedContent,
      setVisitedNodes,
    },
  };
};
