import React, { useState } from 'react';
import { X, FileCode } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
// import Link from 'next/link'; // Removed as TopNavigation handles links
// import { usePathname } from 'next/navigation'; // Handled in TopNavigation
import { TopNavigation } from '@/components/TopNavigation';

interface DashboardLayoutProps {
  sidebar?: React.ReactNode;
  children: React.ReactNode;
  isMobileMenuOpen?: boolean; // Kept for interface compatibility but mapped to drawers
  onMobileMenuClose?: () => void;
  // New props for the specific content we expect (can also reuse 'sidebar' prop for History)
  fileExplorer?: React.ReactNode;
}

export const DashboardLayout = ({
  sidebar,
  children,
  isMobileMenuOpen, // We map this to history drawer for backward compat if needed
  onMobileMenuClose,
  fileExplorer,
}: DashboardLayoutProps) => {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isFilesOpen, setIsFilesOpen] = useState(false);

  // Sync with parent control if provided (backward compat)
  React.useEffect(() => {
    if (isMobileMenuOpen !== undefined) {
      setIsHistoryOpen(isMobileMenuOpen);
    }
  }, [isMobileMenuOpen]);

  const handleCloseHistory = () => {
    setIsHistoryOpen(false);
    onMobileMenuClose?.();
  };

  return (
    <div className="bg-background relative flex h-screen w-full flex-col overflow-hidden">
      {/* 1. Top Navigation Bar */}
      <TopNavigation
        onToggleHistory={() => setIsHistoryOpen(!isHistoryOpen)}
        onToggleFiles={() => setIsFilesOpen(!isFilesOpen)}
        isHistoryOpen={isHistoryOpen}
        isFilesOpen={isFilesOpen}
      />

      {/* 2. Main Content Area */}
      <main className="relative mt-16 w-full flex-1 overflow-hidden">
        {/* Background Grid */}
        <div
          className="pointer-events-none absolute inset-0 z-0 opacity-[0.02]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        <div className="relative z-0 h-full w-full">{children}</div>
      </main>

      {/* 3. History Drawer (Left) */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              onClick={handleCloseHistory}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-16 bottom-0 left-0 z-50 w-80 border-r border-white/10 bg-black/90 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-white/10 p-4">
                  <span className="font-bold text-white/80">Mission History</span>
                  <button
                    onClick={handleCloseHistory}
                    className="text-muted-foreground hover:text-white"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">{sidebar}</div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* 4. File Explorer Drawer (Right) */}
      <AnimatePresence>
        {isFilesOpen && (
          <>
            {/* Note: Maybe don't blur for files so we can see graph? Let's try explicit close for now. */}
            {/* Actually, overlays are safer to prevent interactions with graph while working on files. */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
              onClick={() => setIsFilesOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-16 right-0 bottom-0 z-50 w-80 border-l border-white/10 bg-black/90 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-white/10 p-4">
                  <div className="flex items-center gap-2">
                    <FileCode size={18} className="text-primary" />
                    <span className="font-bold text-white/80">Workspace</span>
                  </div>
                  <button
                    onClick={() => setIsFilesOpen(false)}
                    className="text-muted-foreground hover:text-white"
                  >
                    <X size={18} />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                  {fileExplorer || (
                    <div className="text-muted-foreground flex h-full items-center justify-center text-sm">
                      No files loaded.
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
