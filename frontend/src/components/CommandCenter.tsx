import { Play, Square, Send, Command, PauseCircle } from 'lucide-react';
import { clsx } from 'clsx';

interface CommandCenterProps {
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  isPaused: boolean;
  onStart: () => void;
  onResume: () => void;
  onCancel: () => void;
  onReset: () => void;
}

export function CommandCenter({
  input,
  setInput,
  isLoading,
  isPaused,
  onStart,
  onResume,
  onCancel,
  onReset,
}: CommandCenterProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isLoading && !isPaused) {
      onStart();
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl">
      {/* Status Bar */}
      <div className="mb-2 flex items-end justify-between px-2">
        <div className="text-muted-foreground flex items-center gap-2 font-mono text-xs tracking-wider uppercase">
          <span
            className={clsx(
              'h-1.5 w-1.5 rounded-full',
              isLoading ? 'animate-pulse bg-amber-500' : 'bg-green-500'
            )}
          />
          {isLoading ? 'System Processing...' : isPaused ? 'Awaiting Input' : 'System Ready'}
        </div>
      </div>

      <div className="group relative">
        <div className="from-primary via-secondary to-accent absolute -inset-1 rounded-xl bg-gradient-to-r opacity-20 blur-md transition duration-500 group-hover:opacity-40" />

        <div className="relative flex flex-col overflow-hidden rounded-xl border border-white/10 bg-[#0a0a0a]/90 shadow-2xl backdrop-blur-xl">
          {/* Input Area */}
          <div className="flex items-center p-2">
            <div className="text-muted-foreground/50 pr-3 pl-4">
              <Command size={18} />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Initialize mission parameters..."
              className="text-foreground flex-1 border-none bg-transparent px-2 py-4 text-lg font-medium placeholder-white/20 outline-none"
              disabled={isLoading || isPaused}
              autoFocus
            />

            {/* Actions */}
            <div className="flex items-center gap-2 pr-2">
              {isPaused ? (
                <>
                  <button
                    onClick={onResume}
                    className="flex h-10 items-center gap-2 rounded-lg bg-green-500 px-3 font-bold text-white shadow-[0_0_15px_-3px_rgba(34,197,94,0.4)] transition-all hover:bg-green-400 sm:px-4"
                  >
                    <Play size={16} fill="currentColor" />
                    <span className="hidden text-xs tracking-wider sm:inline">RESUME</span>
                  </button>
                  <button
                    onClick={onCancel}
                    className="flex h-10 items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 font-bold text-gray-400 transition-all hover:bg-white/10 hover:text-white sm:px-4"
                  >
                    <Square size={16} />
                    <span className="hidden text-xs tracking-wider sm:inline">CANCEL</span>
                  </button>
                </>
              ) : isLoading ? (
                <button
                  onClick={onReset}
                  className="flex h-10 animate-pulse items-center gap-2 rounded-lg border border-red-500/50 bg-red-500/10 px-3 font-bold text-red-500 transition-all hover:bg-red-500/20 sm:px-4"
                >
                  <Square size={16} fill="currentColor" />
                  <span className="hidden text-xs tracking-wider sm:inline">ABORT</span>
                </button>
              ) : (
                <button
                  onClick={onStart}
                  disabled={!input.trim()}
                  className="bg-primary hover:bg-primary-400 flex h-10 items-center gap-2 rounded-lg px-4 font-bold text-white shadow-[0_0_20px_-5px_var(--color-primary)] transition-all disabled:cursor-not-allowed disabled:opacity-50 sm:px-6"
                >
                  <Send size={16} />
                  <span className="hidden text-xs tracking-wider sm:inline">ACTIVATE</span>
                </button>
              )}
            </div>
          </div>

          {/* Hint Bar */}
          {isPaused && (
            <div className="animate-in slide-in-from-top-2 flex items-center gap-3 border-t border-amber-500/20 bg-amber-500/10 p-2 px-4">
              <PauseCircle size={16} className="animate-pulse text-amber-500" />
              <p className="font-mono text-xs text-amber-200/80">
                HUMAN_INTERVENTION_REQUIRED: Please review the active plan and authorize to proceed.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
