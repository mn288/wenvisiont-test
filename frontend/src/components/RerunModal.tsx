import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { History, Play, X, AlertTriangle } from 'lucide-react';

interface RerunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (newInput: string) => void;
  originalInput?: string;
  stepName: string;
}

export function RerunModal({
  isOpen,
  onClose,
  onConfirm,
  originalInput = '',
  stepName,
}: RerunModalProps) {
  const [input, setInput] = useState(originalInput);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="glass-panel w-full max-w-lg overflow-hidden rounded-xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between border-b border-white/5 bg-slate-900/50 p-6">
            <div className="flex gap-3">
              <div className="bg-primary/20 text-primary flex h-10 w-10 items-center justify-center rounded-lg p-2">
                <History size={20} />
              </div>
              <div>
                <h3 className="text-foreground text-lg font-bold">Time Travel</h3>
                <p className="text-muted-foreground text-sm">
                  Restarting from{' '}
                  <span className="bg-primary/10 text-primary-400 rounded px-1 font-mono font-medium">
                    {stepName}
                  </span>
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Content */}
          <div className="space-y-4 p-6">
            <div className="flex gap-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-200">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <p>
                Rerunning will create a new timeline from this point. Previous future events in the
                current view might be hidden or replaced.
              </p>
            </div>

            {/* Show original instruction if available */}
            {originalInput && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-300">
                  Original Instruction
                </label>
                <div className="rounded-lg border border-white/10 bg-slate-950/50 p-3 text-sm text-slate-400">
                  {originalInput}
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-300">
                Additional Context (Optional)
              </label>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="focus:border-primary-500 focus:ring-primary-500 h-32 w-full resize-none rounded-lg border border-white/10 bg-slate-950/50 p-3 font-sans text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:ring-1"
                placeholder="Add additional context or refinements to append to the original instruction..."
              />
              <p className="text-muted-foreground text-xs">
                {originalInput
                  ? 'This text will be appended to the original instruction above.'
                  : 'Enter additional context to guide the rerun execution.'}
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 border-t border-white/5 bg-slate-900/50 p-4">
            <button
              onClick={onClose}
              className="rounded-lg px-4 py-2 font-medium text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              onClick={() => onConfirm(input)}
              className="group bg-primary hover:bg-primary-600 flex items-center gap-2 rounded-lg px-4 py-2 font-medium text-white shadow-[0_0_20px_-5px_var(--color-primary)] transition-all hover:shadow-[0_0_25px_-5px_var(--color-primary)]"
            >
              <Play
                size={16}
                fill="currentColor"
                className="transition-transform group-hover:translate-x-0.5"
              />
              Confirm Rerun
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
