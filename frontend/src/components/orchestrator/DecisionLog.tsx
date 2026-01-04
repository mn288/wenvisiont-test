'use client';

import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

interface DecisionLogProps {
  logs: string[];
}

export function DecisionLog({ logs }: DecisionLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-navy flex h-[300px] flex-col overflow-hidden rounded-xl border border-gray-800 shadow-lg">
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 px-4 py-2">
        <Terminal size={14} className="text-emerald-500" />
        <span className="font-mono text-xs text-gray-400">System Activity Log</span>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-4 font-mono text-sm">
        {logs.length === 0 ? (
          <div className="text-gray-600 italic">Ready for input...</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="border-primary/30 border-l-2 pl-3 text-gray-300">
              <span className="mr-2 text-xs text-gray-500">{new Date().toLocaleTimeString()}</span>
              {log}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
