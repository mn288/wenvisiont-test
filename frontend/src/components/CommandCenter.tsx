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
    <div className="w-full">
      <div className="group relative">
        {/* Glow Effect */}
        <div className="from-primary/30 via-secondary/30 to-accent/30 absolute -inset-0.5 rounded-full bg-gradient-to-r opacity-20 blur-md transition duration-500 group-hover:opacity-40" />

        <div className="relative flex items-center overflow-hidden rounded-full border border-white/10 bg-[#0a0a0a]/80 shadow-2xl backdrop-blur-xl">
          {/* Leading Status Icon */}
          <div className="flex items-center pl-4">
            <div
              className={clsx(
                'h-2 w-2 rounded-full shadow-[0_0_8px_currentColor]',
                isLoading
                  ? 'animate-pulse bg-amber-500 text-amber-500'
                  : isPaused
                    ? 'bg-blue-500 text-blue-500'
                    : 'bg-green-500 text-green-500'
              )}
            />
          </div>

          {/* Input Area */}
          <div className="flex flex-1 items-center px-2">
            <div className="text-muted-foreground/30 px-2">
              <Command size={16} />
            </div>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isLoading
                  ? 'Processing mission...'
                  : isPaused
                    ? 'Waiting for authorization...'
                    : 'Initialize mission parameters...'
              }
              className="text-foreground w-full border-none bg-transparent py-4 text-base font-medium placeholder-white/20 outline-none"
              disabled={isLoading || isPaused}
              autoFocus
              autoComplete="off"
            />
          </div>

          {/* Actions & Hint */}
          <div className="flex items-center gap-1 pr-1.5 pl-2">
            {/* Dynamic Action Button */}
            {isPaused ? (
              <>
                <button
                  onClick={onResume}
                  className="flex h-9 items-center gap-2 rounded-full bg-green-500 px-4 font-bold text-white shadow-[0_0_15px_-3px_rgba(34,197,94,0.4)] transition-all hover:bg-green-400"
                >
                  <Play size={14} fill="currentColor" />
                  <span className="text-xs tracking-wider">RESUME</span>
                </button>
                <button
                  onClick={onCancel}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-white/5 text-gray-400 transition-all hover:bg-white/10 hover:text-white"
                  title="Cancel"
                >
                  <Square size={14} />
                </button>
              </>
            ) : isLoading ? (
              <button
                onClick={onReset}
                className="flex h-9 items-center gap-2 rounded-full border border-red-500/50 bg-red-500/10 px-4 font-bold text-red-500 transition-all hover:bg-red-500/20"
              >
                <Square size={14} fill="currentColor" />
                <span className="text-xs tracking-wider">ABORT</span>
              </button>
            ) : (
              <button
                onClick={onStart}
                disabled={!input.trim()}
                className="bg-primary hover:bg-primary-400 flex h-9 items-center gap-2 rounded-full px-4 font-bold text-white shadow-[0_0_20px_-5px_var(--color-primary)] transition-all disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Send size={14} />
                <span className="text-xs tracking-wider">ACTIVATE</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Contextual Hints (Floating below) */}
      {isPaused && (
        <div className="mt-2 flex justify-center">
          <div className="flex items-center gap-2 rounded-full border border-amber-500/20 bg-black/60 px-4 py-1 font-mono text-xs text-amber-200/80 shadow-lg backdrop-blur-md">
            <PauseCircle size={12} className="animate-pulse text-amber-500" />
            HUMAN_INTERVENTION_REQUIRED
          </div>
        </div>
      )}
    </div>
  );
}
