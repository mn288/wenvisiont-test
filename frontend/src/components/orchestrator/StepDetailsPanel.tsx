'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Clock, Terminal, RotateCcw, MessageSquare, List } from 'lucide-react';
import { StepLog } from '@/lib/api';
import clsx from 'clsx';
import { RerunModal } from '../RerunModal';
import { useState } from 'react';

interface StepDetailsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  stepName: string | null;
  logs: StepLog[];
  isLoading: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  toolCall?: { name: string; args: any; reasoning?: string } | null;
  onRerun?: (checkpointId: string, newInput?: string, stepName?: string) => void;
  originalInput?: string;
}

export function StepDetailsPanel({
  isOpen,
  onClose,
  stepName,
  logs,
  isLoading,
  toolCall,
  onRerun,
  originalInput,
}: StepDetailsPanelProps) {
  const [isRerunOpen, setIsRerunOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'log' | 'chat'>('chat');
  const checkpointId = logs.find((l) => l.checkpoint_id)?.checkpoint_id;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 bottom-0 z-50 flex w-full max-w-md flex-col border-l border-white/10 bg-[#0f1117] shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 bg-white/5 p-6 backdrop-blur-md">
              <div>
                <h3 className="text-primary/80 mb-1 text-xs font-semibold tracking-widest uppercase">
                  Step Analysis
                </h3>
                <h2 className="text-foreground text-2xl font-bold tracking-tight capitalize">
                  {stepName || 'Unknown Step'}
                </h2>
              </div>

              {/* View Toggle */}
              <div className="mr-4 flex gap-1 rounded-lg bg-white/5 p-1">
                <button
                  onClick={() => setViewMode('chat')}
                  className={clsx(
                    'rounded-md p-1.5 transition-all',
                    viewMode === 'chat'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-gray-400 hover:text-white'
                  )}
                  title="Conversation View"
                >
                  <MessageSquare size={16} />
                </button>
                <button
                  onClick={() => setViewMode('log')}
                  className={clsx(
                    'rounded-md p-1.5 transition-all',
                    viewMode === 'log'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-gray-400 hover:text-white'
                  )}
                  title="System Logs"
                >
                  <List size={16} />
                </button>
              </div>

              <div className="flex gap-2">
                {onRerun &&
                  checkpointId &&
                  stepName &&
                  !['supervisor', 'preprocess'].includes(stepName.toLowerCase()) && (
                    <button
                      onClick={() => setIsRerunOpen(true)}
                      className="text-primary hover:bg-primary/10 rounded-full p-2 transition-colors"
                      title="Rerun from this step"
                    >
                      <RotateCcw size={20} />
                    </button>
                  )}
                <button
                  onClick={onClose}
                  className="rounded-full p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="custom-scrollbar flex-1 space-y-6 overflow-y-auto p-6">
              {/* Tool Approval UI */}
              {toolCall && (
                <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/10 p-4">
                  <div className="mb-2 flex items-center gap-2 text-xs font-bold tracking-wider text-amber-500 uppercase">
                    <Terminal size={14} />
                    Proposed Tool Execution
                  </div>
                  <div className="text-foreground mb-2 text-lg font-bold">{toolCall.name}</div>
                  <div className="rounded border border-amber-500/20 bg-black/40 p-3 font-mono text-sm whitespace-pre-wrap text-amber-200/80">
                    {JSON.stringify(toolCall.args, null, 2)}
                  </div>
                  {toolCall.reasoning && (
                    <div className="mt-3 text-sm text-gray-400 italic">
                      &quot;{toolCall.reasoning}&quot;
                    </div>
                  )}
                  <div className="mt-4 flex gap-2">
                    <div className="flex animate-pulse items-center gap-1 text-xs text-amber-500">
                      <Clock size={12} />
                      Waiting for approval to execute...
                    </div>
                  </div>
                </div>
              )}

              {/* Logs / Chat */}
              {logs.length === 0 && isLoading ? (
                <div className="flex h-40 flex-col items-center justify-center text-gray-500">
                  <Clock className="text-primary mb-2 animate-spin" size={24} />
                  <p>Decrypting logs...</p>
                </div>
              ) : logs.length === 0 ? (
                <div className="rounded-lg border border-dashed border-white/10 py-10 text-center text-gray-500">
                  No activity recorded.
                </div>
              ) : viewMode === 'chat' ? (
                // CHAT VIEW
                <div className="space-y-6">
                  {logs.filter((l) => l.log_type === 'message').length === 0 ? (
                    <div className="py-10 text-center text-gray-500 italic">
                      No conversation history found. Switch to Logs view.
                    </div>
                  ) : (
                    logs
                      .filter((l) => l.log_type === 'message')
                      .map((log) => (
                        <div
                          key={log.id}
                          className={clsx(
                            'flex w-full',
                            log.step_name === 'preprocess' ? 'justify-end' : 'justify-start'
                          )}
                        >
                          <div
                            className={clsx(
                              'max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed shadow-lg backdrop-blur-sm',
                              log.step_name === 'preprocess'
                                ? 'bg-primary/90 text-primary-foreground border-primary/50 rounded-tr-sm border'
                                : 'rounded-tl-sm border border-white/10 bg-white/10 text-gray-100'
                            )}
                          >
                            <div className="mb-1 flex items-center gap-2 text-[10px] font-bold tracking-wider uppercase opacity-70">
                              {log.step_name === 'preprocess' ? (
                                <>
                                  <span>User</span>
                                  <span className="text-[9px] opacity-50">
                                    {new Date(log.created_at).toLocaleTimeString()}
                                  </span>
                                </>
                              ) : (
                                <>
                                  <span>{log.step_name}</span>
                                  <span className="text-[9px] opacity-50">
                                    {new Date(log.created_at).toLocaleTimeString()}
                                  </span>
                                </>
                              )}
                            </div>
                            <div className="whitespace-pre-wrap">{log.content}</div>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              ) : (
                // LOGS VIEW
                <div className="space-y-4">
                  {logs.map((log) => (
                    <div key={log.id} className="group">
                      <div className="mb-2 flex items-center gap-2">
                        <span
                          className={clsx(
                            'rounded border px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase',
                            log.log_type === 'thought'
                              ? 'border-blue-500/20 bg-blue-500/10 text-blue-400'
                              : log.log_type === 'tool'
                                ? 'border-purple-500/20 bg-purple-500/10 text-purple-400'
                                : log.log_type === 'message'
                                  ? 'border-green-500/20 bg-green-500/10 text-green-400'
                                  : 'border-gray-500/20 bg-gray-500/10 text-gray-400'
                          )}
                        >
                          {log.log_type}
                        </span>
                        <span className="font-mono text-[10px] text-gray-500">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </span>
                      </div>

                      <div
                        className={clsx(
                          'rounded-lg border p-3 font-mono text-sm leading-relaxed',
                          log.log_type === 'thought'
                            ? 'border-white/10 bg-white/5 text-gray-300 italic'
                            : 'border-white/5 bg-black/40 text-gray-400'
                        )}
                      >
                        {log.content}
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="text-primary/50 flex items-center justify-center py-4 text-xs">
                      <Clock className="mr-2 animate-spin" size={14} />
                      <span>Syncing stream...</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <RerunModal
              isOpen={isRerunOpen}
              onClose={() => setIsRerunOpen(false)}
              stepName={stepName || ''}
              originalInput={originalInput}
              onConfirm={(newInput) => {
                setIsRerunOpen(false);
                if (onRerun && checkpointId && stepName) {
                  onRerun(checkpointId, newInput, stepName);
                }
              }}
            />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
