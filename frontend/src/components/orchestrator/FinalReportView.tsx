"use client";

import { motion } from "framer-motion";
import { FileBadge, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface FinalReportViewProps {
  finalResponse: string | null;
}

export function FinalReportView({ finalResponse }: FinalReportViewProps) {
  if (!finalResponse) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white rounded-xl shadow-xl border border-primary/20 overflow-hidden"
    >
      <div className="bg-primary/5 p-6 border-b border-primary/10 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary text-white rounded-lg shadow-sm">
            <FileBadge size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-navy">Mission Accomplished</h2>
            <p className="text-sm text-primary font-medium">Final Intelligence Report</p>
          </div>
        </div>
        <button className="text-gray-500 hover:text-primary transition-colors">
          <Download size={20} />
        </button>
      </div>

      <div className="p-8 prose prose-slate max-w-none">
        <ReactMarkdown>{finalResponse}</ReactMarkdown>
      </div>
    </motion.div>
  );
}
