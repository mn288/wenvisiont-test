'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2, FileText, Sparkles, Wrench } from 'lucide-react';

import ReactMarkdown from 'react-markdown';

interface AgentActionCardProps {
  activeAgent: string | null;
  logs: string[];
  streamedContent?: string;
}

export function AgentActionCard({ activeAgent, logs, streamedContent }: AgentActionCardProps) {
  // Extract latest relevant output based on agent
  // This is a heuristic until we get structured outputs pushed to frontend
  const latestLog = logs[logs.length - 1];
  // If streamedContent is present, show it. Otherwise show latest log.
  const displayContent = streamedContent || latestLog;
  const isOutput = latestLog?.includes('research_output') || latestLog?.includes('crew_output');

  if (!activeAgent) return null;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeAgent}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="relative overflow-hidden rounded-xl border border-gray-100 bg-white p-6 shadow-lg"
      >
        <div className="bg-secondary absolute top-0 left-0 h-full w-1" />

        <div className="mb-4 flex items-center gap-3">
          <div className="bg-secondary/10 text-secondary rounded-lg p-2">
            {activeAgent === 'Researcher' ? (
              <Sparkles size={20} />
            ) : activeAgent === 'Tech Analyst' ? (
              <FileText size={20} />
            ) : (
              <Wrench size={20} />
            )}
          </div>
          <div>
            <h3 className="text-navy text-lg font-bold">
              {activeAgent === 'Researcher'
                ? 'Market Research'
                : activeAgent === 'Tech Analyst'
                  ? 'Strategic Analysis'
                  : 'Tool Execution'}
            </h3>
            <p className="text-xs tracking-wider text-gray-400 uppercase">
              {activeAgent === 'Researcher'
                ? 'Gathering Intelligence...'
                : activeAgent === 'Tech Analyst'
                  ? 'Synthesizing Report...'
                  : 'Executing Actions...'}
            </p>
          </div>
        </div>

        <div className="h-40 overflow-y-auto rounded-lg border border-gray-100 bg-gray-50 p-4 font-mono text-sm text-gray-600">
          {isOutput ? (
            <div className="flex items-start gap-2 text-green-600">
              <Check size={16} className="mt-0.5" />
              <span>Task Completed. Output generated.</span>
            </div>
          ) : (
            <div className="text-secondary flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              <span>Agent is working...</span>
            </div>
          )}
          <div className="mt-4 border-t border-gray-200 pt-4">
            <p className="mb-1 text-xs text-gray-400">LIVE STREAM:</p>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{displayContent}</ReactMarkdown>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
