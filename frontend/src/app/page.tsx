'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { DashboardLayout } from '@/components/DashboardLayout';
import { HistorySidebar } from '@/components/HistorySidebar';
import { GraphVisualizer } from '@/components/GraphVisualizer'; // NEW
import { FileExplorer } from '@/components/FileExplorer'; // NEW
import { TerminalView } from '@/components/TerminalView';
import { CommandCenter } from '@/components/CommandCenter';
import { ReportView } from '@/components/ReportView';
import { StepDetailsPanel } from '@/components/orchestrator/StepDetailsPanel';

import { Cpu, Activity, Menu, Layout, Terminal as TerminalIcon, FileCode } from 'lucide-react';

import { useOrchestrator } from '@/hooks/useOrchestrator';
import {
  fetchStepHistory,
  StepLog,
  Conversation,
  forkConversation,
  listAgents,
  fetchTopology,
} from '@/lib/api';
import { reconstructStateFromLogs } from '@/lib/state-utils';

export default function Home() {
  const { state, actions } = useOrchestrator();
  const [selectedStep, setSelectedStep] = useState<{ name: string; checkpointId?: string } | null>(
    null
  );
  const [stepLogs, setStepLogs] = useState<StepLog[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [agentMap, setAgentMap] = useState<Record<string, string>>({});

  // Layout State (Tabs for right panel?)
  const [activeTab, setActiveTab] = useState<'terminal' | 'report'>('terminal');

  useEffect(() => {
    listAgents()
      .then((agents) => {
        const map: Record<string, string> = {};
        agents.forEach((a) => {
          map[a.name] = a.display_name;
        });
        setAgentMap(map);
      })
      .catch((err) => console.error('Failed to fetch agents map', err));
  }, []);

  const handleHistorySelect = async (conversation: Conversation) => {
    actions.handleReset();
    const selectedThread = conversation.thread_id;
    actions.setIsLoading(true);

    try {
      const [logs, topology] = await Promise.all([
        fetchStepHistory(selectedThread),
        fetchTopology(selectedThread),
      ]);

      const {
        logs: restoredLogs,
        content: restoredContent,
        visited: restoredVisited,
        response,
      } = reconstructStateFromLogs(logs, topology);

      actions.restoreState(
        selectedThread,
        conversation.title,
        restoredLogs,
        restoredContent,
        restoredVisited,
        response
      );
      setIsSidebarOpen(false);
    } catch (e) {
      console.error('Failed to load history', e);
      actions.setLogs((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          timestamp: new Date(),
          type: 'error',
          message: 'Failed to load conversation history',
        },
      ]);
    } finally {
      actions.setIsLoading(false);
    }
  };

  const handleRerun = async (checkpointId: string, newInput?: string, stepName?: string) => {
    if (!state.threadId) return;

    actions.setIsLoading(true);

    // For fork/rerun, we preserve the FULL tree history
    // New nodes will be appended and connected via parentCheckpointId to the fork point
    // This creates a proper branching visualization
    const now = new Date();
    actions.setLogs((prev) => [
      ...prev,
      {
        id: now.getTime().toString(),
        timestamp: now,
        type: 'system',
        message: `Forking timeline from '${stepName || 'checkpoint'}'...`,
      },
    ]);

    try {
      const res = await forkConversation(state.threadId, checkpointId, newInput, stepName);
      if (res.status === 'forked') {
        actions.setLogs((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            timestamp: new Date(),
            type: 'system',
            message: 'Timeline Branching Authorized.',
          },
        ]);

        // CRITICAL: Reload topology to get the fork point structure before streaming
        // This ensures new streaming nodes know about existing graph context
        try {
          const [logs, topology] = await Promise.all([
            fetchStepHistory(state.threadId),
            fetchTopology(state.threadId),
          ]);

          const { visited } = reconstructStateFromLogs(logs, topology);
          // Update visitedNodes with full topology including fork point
          actions.setVisitedNodes(visited);

          actions.setLogs((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              timestamp: new Date(),
              type: 'system',
              message: `Resuming execution from ${stepName}...`,
            },
          ]);

          // Start streaming with context - don't clear existing nodes
          actions.startStream(`http://localhost:8000/stream?thread_id=${state.threadId}`, false);
        } catch (topologyError) {
          console.error('Failed to reload topology before streaming:', topologyError);
          // Fallback: stream anyway but warn
          actions.setLogs((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              timestamp: new Date(),
              type: 'info',
              message: 'Warning: Could not reload graph structure',
            },
          ]);
          actions.startStream(`http://localhost:8000/stream?thread_id=${state.threadId}`, false);
        }
      } else {
        actions.setLogs((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            timestamp: new Date(),
            type: 'error',
            message: `Rerun failed: ${res.message}`,
          },
        ]);
      }
    } catch (e) {
      console.error(e);
      actions.setLogs((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          timestamp: new Date(),
          type: 'error',
          message: 'Fatal Error: Rerun Failed',
        },
      ]);
      actions.setIsLoading(false);
    }
  };

  // Poll for logs for the selected step
  useEffect(() => {
    if (!selectedStep || !state.threadId) return;

    let isMounted = true;
    const fetchLogs = async (isInitial = false) => {
      if (isInitial) setIsLoadingLogs(true);
      try {
        const logs = await fetchStepHistory(state.threadId);
        if (isMounted) {
          // Strategy: Try strict checkpoint matching first, fall back to name-only matching
          let filteredLogs = logs.filter((log) => {
            if (!selectedStep) return false;
            const nameMatch = log.step_name === selectedStep.name;
            const checkpointMatch = selectedStep.checkpointId
              ? log.checkpoint_id === selectedStep.checkpointId
              : !log.checkpoint_id;
            return nameMatch && checkpointMatch;
          });

          // Fallback: if no logs found with checkpoint matching and we have a checkpointId,
          // it might be a new rerun node without database logs yet - show all logs for this step
          if (filteredLogs.length === 0 && selectedStep.checkpointId) {
            filteredLogs = logs.filter((log) => log.step_name === selectedStep.name);
          }

          setStepLogs(filteredLogs);
        }
      } catch (error) {
        console.error('Failed to fetch logs', error);
      } finally {
        if (isInitial && isMounted) setIsLoadingLogs(false);
      }
    };

    fetchLogs(true);
    let interval: NodeJS.Timeout | null = null;
    if (state.isLoading) {
      interval = setInterval(() => fetchLogs(false), 2000);
    }

    return () => {
      isMounted = false;
      if (interval) clearInterval(interval);
    };
  }, [selectedStep, state.threadId, state.isLoading]);

  return (
    <DashboardLayout
      isMobileMenuOpen={isSidebarOpen}
      onMobileMenuClose={() => setIsSidebarOpen(false)}
      sidebar={
        <div className="flex h-full flex-col gap-4">
          {/* History Section */}
          <div className="min-h-0 flex-1 overflow-hidden">
            <HistorySidebar
              currentThreadId={state.threadId}
              onSelectConversation={handleHistorySelect}
              onNewChat={() => {
                actions.handleReset();
                actions.setInput('');
                setIsSidebarOpen(false);
              }}
            />
          </div>

          {/* File Explorer Section */}
          <div className="flex h-[40%] min-h-[200px] shrink-0 flex-col border-t border-white/10 pt-4">
            <div className="text-primary flex items-center gap-2 px-4 pb-2 text-xs font-bold tracking-wider uppercase">
              <FileCode size={12} />
              Workspace Files
            </div>
            {/* Only render FileExplorer on client to avoid hydration mismatch with local storage state */}
            <div className="min-h-0 flex-1 px-2">
              {state.threadId ? (
                <FileExplorer initialPath={state.threadId} />
              ) : (
                <div className="text-muted-foreground flex h-full items-center justify-center text-xs opacity-50">
                  Select a thread...
                </div>
              )}
            </div>
          </div>
        </div>
      }
    >
      <div className="flex h-full flex-col">
        {/* Top Header - Minimal */}
        <header className="z-20 flex shrink-0 items-center justify-between border-b border-white/5 bg-black/40 px-4 py-3 backdrop-blur-md md:px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="text-muted-foreground -ml-2 p-2 hover:text-white md:hidden"
            >
              <Menu size={24} />
            </button>
            <div className="bg-primary/20 border-primary/30 shadow-glow relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border">
              <Image src="/logo.png" alt="wenvision Logo" fill className="object-cover p-1" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white/90 md:text-xl">
                Agentic <span className="text-primary">Studio</span>
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Future: User Profile or Settings here */}
          </div>
        </header>

        {/* Main Workspace (Split View) */}
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
          {/* Center: Graph + Input Area (Flexible) */}
          <div className="relative flex min-w-0 flex-1 flex-col bg-[#0a0a0a]">
            {/* Graph Visualization */}
            <div className="relative min-h-0 flex-1">
              <div className="absolute inset-0">
                <GraphVisualizer
                  activeNodes={state.activeNodes}
                  visitedNodes={state.visitedNodes}
                  onStepClick={setSelectedStep}
                  onRerun={handleRerun}
                  agentMap={agentMap}
                />
              </div>
              {/* Overlay Waiting State */}
              {state.visitedNodes.length === 0 && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-[1px]">
                  <div className="space-y-2 text-center">
                    <Activity size={32} className="mx-auto animate-pulse text-white/20" />
                    <p className="font-mono text-sm text-white/40">READY FOR INSTRUCTION</p>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Input Area - Fixed */}
            <div className="z-20 shrink-0 border-t border-white/5 bg-[#0a0a0a]/90 p-4 pb-6 backdrop-blur-lg">
              <CommandCenter
                input={state.input}
                setInput={actions.setInput}
                isLoading={state.isLoading}
                isPaused={state.isPaused}
                onStart={actions.handleStart}
                onResume={actions.handleResume}
                onCancel={() => {
                  actions.setIsPaused(false);
                  actions.setIsLoading(false);
                }}
                onReset={actions.handleReset}
              />
            </div>
          </div>

          {/* Right Panel: Logs & Reports */}
          <div className="flex w-full flex-col border-l border-white/10 bg-[#0c0c0c] lg:w-[450px] xl:w-[500px]">
            {/* Tabs */}
            <div className="flex shrink-0 border-b border-white/5">
              <button
                onClick={() => setActiveTab('terminal')}
                className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold tracking-wider uppercase transition-colors ${activeTab === 'terminal' ? 'text-primary border-primary border-b-2 bg-white/5' : 'text-muted-foreground hover:bg-white/5'}`}
              >
                <TerminalIcon size={14} /> Live Terminal
              </button>
              <button
                onClick={() => setActiveTab('report')}
                className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold tracking-wider uppercase transition-colors ${activeTab === 'report' ? 'text-primary border-primary border-b-2 bg-white/5' : 'text-muted-foreground hover:bg-white/5'}`}
              >
                <Layout size={14} /> Mission Report
              </button>
            </div>

            <div className="relative min-h-0 flex-1 overflow-hidden">
              {activeTab === 'terminal' ? (
                <TerminalView
                  logs={state.logs}
                  streamedContent={Object.values(state.streamedContent).join('\n\n')}
                  onLogClick={(node) => setSelectedStep({ name: node })}
                />
              ) : (
                <div className="custom-scrollbar h-full overflow-y-auto p-4">
                  {state.finalResponse ? (
                    <ReportView content={state.finalResponse} />
                  ) : (
                    <div className="flex h-full items-center justify-center p-8 text-center">
                      <div className="space-y-4">
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5">
                          <Cpu size={24} className="text-white/20" />
                        </div>
                        <p className="text-muted-foreground text-sm text-balance">
                          Mission report will verify and display here upon completion.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Step Details Overlay */}
      <StepDetailsPanel
        isOpen={!!selectedStep}
        onClose={() => setSelectedStep(null)}
        stepName={selectedStep?.name || null}
        logs={
          selectedStep && state.streamedContent[selectedStep.name]
            ? // If we have streaming content, always include it (especially important for live rerun nodes)
              [
                ...stepLogs,
                {
                  id: -1,
                  thread_id: state.threadId,
                  step_name: selectedStep.name,
                  log_type: 'thought',
                  content: state.streamedContent[selectedStep.name],
                  created_at: new Date().toISOString(),
                },
              ]
            : stepLogs.length > 0
              ? stepLogs
              : // If no logs at all, show a helpful message
                selectedStep && state.isLoading
                ? [
                    {
                      id: -2,
                      thread_id: state.threadId,
                      step_name: selectedStep.name,
                      log_type: 'info',
                      content: 'Waiting for execution to begin...',
                      created_at: new Date().toISOString(),
                    },
                  ]
                : stepLogs
        }
        isLoading={isLoadingLogs}
        toolCall={selectedStep?.name === 'tool_execution' ? state.toolCall : null}
        onRerun={handleRerun}
        originalInput={state.input}
      />
    </DashboardLayout>
  );
}
