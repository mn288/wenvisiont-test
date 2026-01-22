'use client';

import { motion } from 'framer-motion';
import { FileBadge, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface FinalReportViewProps {
  finalResponse: string | null;
}

export function FinalReportView({ finalResponse }: FinalReportViewProps) {
  if (!finalResponse) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="border-primary/20 overflow-hidden rounded-xl border bg-white shadow-xl"
    >
      <div className="bg-primary/5 border-primary/10 flex items-center justify-between border-b p-6">
        <div className="flex items-center gap-3">
          <div className="bg-primary rounded-lg p-2 text-white shadow-sm">
            <FileBadge size={24} />
          </div>
          <div>
            <h2 className="text-navy text-xl font-bold">Mission Accomplished</h2>
            <p className="text-primary text-sm font-medium">Final Intelligence Report</p>
          </div>
        </div>
        <button className="hover:text-primary text-gray-500 transition-colors">
          <Download size={20} />
        </button>
      </div>

      <div className="prose prose-slate max-w-none p-8">
        <ReactMarkdown>{finalResponse}</ReactMarkdown>
      </div>
    </motion.div>
  );
}
