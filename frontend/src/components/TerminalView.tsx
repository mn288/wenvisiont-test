import { useEffect, useRef, useState } from 'react';
import { LogEntry } from '@/lib/api';
import {
  Terminal,
  Search,
  FileText,
  ShieldCheck,
  ListStart,
  Brain,
  Cpu,
  Info,
  AlertCircle,
  CheckCircle2,
  ArrowDownCircle,
  Copy,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

interface TerminalViewProps {
  logs: LogEntry[];
  streamedContent: string;
  onLogClick: (node: string) => void;
}

const getIconForType = (type: LogEntry['type'], node?: string) => {
  if (type === 'node-start' && node) {
    const lowerId = node.toLowerCase();
    if (lowerId.includes('research')) return Search;
    if (lowerId.includes('analyst') || lowerId.includes('analyze')) return FileText;
    if (lowerId.includes('critic') || lowerId.includes('qa')) return ShieldCheck;
    if (lowerId.includes('super')) return ListStart;
    if (lowerId.includes('gate') || lowerId.includes('pre')) return Brain;
    if (lowerId.includes('tool')) return Cpu;
  }

  switch (type) {
    case 'error':
      return AlertCircle;
    case 'info':
      return Info;
    case 'system':
      return Terminal;
    case 'node-end':
      return CheckCircle2;
    default:
      return Terminal;
  }
};

export function TerminalView({ logs, streamedContent, onLogClick }: TerminalViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);

  // Auto-scroll logic
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      const element = scrollRef.current;
      // Use instant scrolling to prevent jitter during rapid updates
      element.scrollTop = element.scrollHeight;
    }
  }, [logs, streamedContent, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
      setAutoScroll(isAtBottom);
    }
  };

  const handleCopyLogs = () => {
    const text = logs
      .map((l) => `[${l.timestamp.toISOString()}] ${l.type.toUpperCase()}: ${l.message}`)
      .join('\n');
    navigator.clipboard.writeText(text);
  };

  return (
    <div
      className={clsx(
        'flex h-full flex-col font-mono',
        isExpanded
          ? 'fixed inset-4 z-50 rounded-xl border border-white/10 bg-[#0a0a0a]/95 p-4 shadow-2xl'
          : 'relative'
      )}
    >
      {/* Terminal Header - Only show if expanded or specifically requested. 
          Actually, we usually want the header (controls) but maybe cleaner. 
          For now, keep header but remove outer border/bg of the container. 
      */}

      {/* If Docked, we might not need the header since parent has tabs. 
          But we need the Copy/Maximize buttons.
          Let's make a minimal toolbar instead of a full header box.
      */}

      <div className="flex shrink-0 items-center justify-between px-2 pb-2">
        {/* Left Side: Secure Status */}
        <div className="flex items-center gap-2 opacity-50">
          <div className="flex gap-1">
            <div className="h-2 w-2 rounded-full bg-red-500/50" />
            <div className="h-2 w-2 rounded-full bg-amber-500/50" />
            <div className="h-2 w-2 rounded-full bg-green-500/50" />
          </div>
          <div className="ml-1 h-3 w-px bg-white/10" />
          <span className="text-muted-foreground font-mono text-[10px]">SECURE_SHELL</span>
        </div>

        {/* Right Side: Tools */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopyLogs}
            className="text-muted-foreground/60 rounded-md p-1.5 transition-colors hover:bg-white/10 hover:text-white"
            title="Copy"
          >
            <Copy size={12} />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-muted-foreground/60 rounded-md p-1.5 transition-colors hover:bg-white/10 hover:text-white"
            title={isExpanded ? 'Collapse' : 'Fullscreen'}
          >
            {isExpanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
        </div>
      </div>

      {/* Logs Area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent font-code relative flex-1 space-y-1 overflow-y-auto px-2 pb-2 text-xs leading-relaxed md:text-sm"
      >
        {logs.length === 0 && !streamedContent && (
          <div className="text-muted-foreground/20 flex h-full flex-col items-center justify-center text-center select-none">
            <div className="mb-4 rounded-full bg-white/5 p-4">
              <Terminal size={32} strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium">System Ready</p>
            <p className="text-xs">Waiting for agent initialization...</p>
          </div>
        )}

        {logs.map((log) => {
          const Icon = getIconForType(log.type, log.node);
          return (
            <div
              key={log.id}
              onClick={() => log.node && onLogClick(log.node)}
              className={clsx(
                'group flex items-start gap-3 rounded-lg p-1.5 transition-colors hover:bg-white/5',
                log.node && 'cursor-pointer hover:bg-white/10',
                log.type === 'node-start' && 'bg-blue-500/5 text-blue-300',
                log.type === 'error' && 'bg-red-500/5 font-bold text-red-400',
                log.type === 'info' && 'text-amber-300',
                log.type === 'system' && 'text-muted-foreground italic',
                log.type === 'node-end' && 'text-green-400'
              )}
            >
              <span className="text-muted-foreground/30 mt-0.5 min-w-[70px] font-mono text-[10px] select-none">
                {log.timestamp.toLocaleTimeString([], {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  fractionalSecondDigits: 3,
                })}
              </span>

              <div className="mt-0.5 shrink-0 opacity-70 transition-opacity group-hover:opacity-100">
                <Icon size={14} />
              </div>

              <div className="flex-1 break-words whitespace-pre-wrap">
                {log.type === 'node-start' && (
                  <span className="mr-2 font-bold text-blue-400/50">➜</span>
                )}
                {log.message}
              </div>
            </div>
          );
        })}

        {/* Streaming Content Overlay/Inline */}
        {streamedContent && (
          <div className="text-primary/90 border-primary/20 mt-2 border-l-2 py-1 pl-[98px] leading-6 whitespace-pre-wrap">
            <span className="bg-primary animate-blink mr-2 inline-block h-4 w-1 align-middle" />
            <span className="text-primary/80 font-mono">{streamedContent}</span>
          </div>
        )}
      </div>

      {/* Auto-scroll button if disabled */}
      <AnimatePresence>
        {!autoScroll && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute right-6 bottom-6 z-10"
          >
            <button
              onClick={() => setAutoScroll(true)}
              className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-primary/20 flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium shadow-lg transition-all hover:scale-105 active:scale-95"
            >
              <ArrowDownCircle size={14} />
              <span>Scroll to Bottom</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
