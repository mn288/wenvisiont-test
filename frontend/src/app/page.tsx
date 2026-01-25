'use client';

import { useState, useEffect } from 'react';

import { DashboardLayout } from '@/components/DashboardLayout';
import { HistorySidebar } from '@/components/HistorySidebar';
import { GraphVisualizer } from '@/components/GraphVisualizer'; // NEW
import { FileExplorer } from '@/components/FileExplorer'; // NEW
import { TerminalView } from '@/components/TerminalView';
import { CommandCenter } from '@/components/CommandCenter';
import { ReportView } from '@/components/ReportView';
import { StepDetailsPanel } from '@/components/orchestrator/StepDetailsPanel';

import {
  Cpu,
  Layout,
  Terminal as TerminalIcon,
  FileCode,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

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

  // Layout State (Right Panel)
  const [activeTab, setActiveTab] = useState<'terminal' | 'report'>('terminal');
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);

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

        try {
          const [logs, topology] = await Promise.all([
            fetchStepHistory(state.threadId),
            fetchTopology(state.threadId),
          ]);

          const { visited } = reconstructStateFromLogs(logs, topology);
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

          actions.startStream(`http://localhost:8000/stream?thread_id=${state.threadId}`, false);
        } catch (topologyError) {
          console.error('Failed to reload topology before streaming:', topologyError);
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
          const filteredLogs = logs.filter((log) => {
            if (!selectedStep) return false;
            return log.step_name === selectedStep.name;
          });

          // Sort by timestamp to be sure (though usually already sorted)
          filteredLogs.sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );

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
        <div className="flex h-full min-h-0 flex-col gap-1.5">
          <HistorySidebar
            currentThreadId={state.threadId}
            onSelectConversation={handleHistorySelect}
            onNewChat={() => {
              actions.handleReset();
              actions.setInput('');
              setIsSidebarOpen(false);
            }}
            className="border-none bg-transparent"
          />
        </div>
      }
      fileExplorer={
        state.threadId ? (
          <FileExplorer initialPath={state.threadId} />
        ) : (
          <div className="text-muted-foreground flex h-full items-center justify-center text-xs opacity-50">
            Select a thread...
          </div>
        )
      }
    >
      <div className="relative h-full w-full">
        {/* === LAYER 0: GRAPH BACKGROUND (Spatial Canvas) === */}
        <div className="absolute inset-0 z-0">
          <GraphVisualizer
            activeNodes={state.activeNodes}
            visitedNodes={state.visitedNodes}
            onStepClick={setSelectedStep}
            onRerun={handleRerun}
            agentMap={agentMap}
          />
          {state.visitedNodes.length === 0 && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[0px]">
              <div className="space-y-4 text-center">
                <div className="relative mx-auto h-24 w-24 opacity-60">
                  <div className="bg-primary/20 absolute inset-0 animate-ping rounded-full delay-1000" />
                  <div className="bg-primary/40 absolute inset-4 animate-ping rounded-full delay-500" />
                  <div className="bg-primary/20 absolute inset-8 rounded-full backdrop-blur-md" />
                </div>
                <p className="font-mono text-xs tracking-[0.2em] text-white/50 uppercase">
                  Awaiting Mission Directives
                </p>
              </div>
            </div>
          )}
        </div>

        {/* === LAYER 1: HEADER (Minimal Floating) === */}
        {/* === LAYER 1: Header Removed (Moved to Sidebar) === */}

        {/* === LAYER 2: FLOATING RIGHT DOCK (Terminal/Report) === */}
        <motion.div
          initial={false}
          animate={{
            width: isRightPanelCollapsed ? 60 : 500,
            right: 16,
          }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className={cn(
            'fixed top-20 right-4 bottom-32 z-20 flex flex-col',
            'rounded-2xl border border-white/10 bg-black/60 shadow-2xl backdrop-blur-xl',
            'overflow-hidden'
          )}
        >
          {/* Toggle Button */}
          <button
            onClick={() => setIsRightPanelCollapsed(!isRightPanelCollapsed)}
            className="text-muted-foreground absolute top-3 left-3 z-50 p-2 transition-colors hover:text-white"
          >
            {isRightPanelCollapsed ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
          </button>

          {isRightPanelCollapsed ? (
            /* Collapsed View */
            <div className="mt-16 flex flex-col items-center gap-6">
              <button
                onClick={() => {
                  setActiveTab('terminal');
                  setIsRightPanelCollapsed(false);
                }}
                className={cn(
                  'rounded-lg p-2 transition-all',
                  activeTab === 'terminal'
                    ? 'text-primary bg-primary/10'
                    : 'text-muted-foreground hover:bg-white/10'
                )}
              >
                <TerminalIcon size={20} />
              </button>
              <button
                onClick={() => {
                  setActiveTab('report');
                  setIsRightPanelCollapsed(false);
                }}
                className={cn(
                  'rounded-lg p-2 transition-all',
                  activeTab === 'report'
                    ? 'text-primary bg-primary/10'
                    : 'text-muted-foreground hover:bg-white/10'
                )}
              >
                <Layout size={20} />
              </button>

              {/* Status Dot */}
              <div className="mt-auto mb-6 h-2 w-2 animate-pulse rounded-full bg-green-500" />
            </div>
          ) : (
            /* Expanded View */
            <div className="flex h-full w-full flex-col">
              {/* Custom Tab Bar */}
              <div className="flex shrink-0 gap-4 border-b border-white/5 px-12 py-3">
                <button
                  onClick={() => setActiveTab('terminal')}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold tracking-wider uppercase transition-all',
                    activeTab === 'terminal'
                      ? 'bg-primary/20 text-primary border-primary/20 border'
                      : 'text-muted-foreground hover:text-white'
                  )}
                >
                  <TerminalIcon size={14} /> Terminal
                </button>
                <button
                  onClick={() => setActiveTab('report')}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold tracking-wider uppercase transition-all',
                    activeTab === 'report'
                      ? 'bg-primary/20 text-primary border-primary/20 border'
                      : 'text-muted-foreground hover:text-white'
                  )}
                >
                  <Layout size={14} /> Mission Report
                </button>
              </div>

              {/* Content */}
              <div className="relative min-h-0 flex-1 overflow-hidden p-1">
                {activeTab === 'terminal' ? (
                  <TerminalView
                    logs={state.logs}
                    streamedContent={Object.values(state.streamedContent).join('\n\n')}
                    onLogClick={(node) => setSelectedStep({ name: node })}
                  />
                ) : (
                  <div className="custom-scrollbar h-full overflow-y-auto">
                    {state.finalResponse ? (
                      <ReportView content={state.finalResponse} />
                    ) : (
                      <div className="flex h-full items-center justify-center p-8 text-center">
                        <div className="text-muted-foreground/30 flex flex-col items-center gap-4">
                          <Cpu size={48} strokeWidth={1} />
                          <p className="text-sm">Awaiting Report Generation...</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </motion.div>

        {/* === LAYER 3: COMMAND ISLAND (Bottom Floating) === */}
        <div className="pointer-events-none fixed bottom-6 left-1/2 z-30 w-[90%] max-w-2xl -translate-x-1/2">
          <div className="pointer-events-auto">
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
                if (state.threadId) {
                  import('@/lib/api').then(({ abortJob }) => {
                    abortJob(state.threadId);
                  });
                }
              }}
              onReset={actions.handleReset}
            />
          </div>
        </div>
      </div>

      {/* Step Details Overlay */}
      <StepDetailsPanel
        isOpen={!!selectedStep}
        onClose={() => setSelectedStep(null)}
        stepName={selectedStep?.name || null}
        logs={
          // ... logic remains same ...
          selectedStep && state.streamedContent[selectedStep.name]
            ? [
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
              : selectedStep && state.isLoading
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
