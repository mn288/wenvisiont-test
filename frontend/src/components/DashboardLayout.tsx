import React from 'react';

import { X } from 'lucide-react';

interface DashboardLayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  isMobileMenuOpen?: boolean;
  onMobileMenuClose?: () => void;
}

export const DashboardLayout = ({
  sidebar,
  children,
  isMobileMenuOpen,
  onMobileMenuClose,
}: DashboardLayoutProps) => {
  return (
    <div className="bg-background flex h-screen w-full overflow-hidden">
      {/* Sidebar Area - Fixed Desktop */}
      <aside className="border-border/40 bg-card/30 z-50 hidden h-full w-[280px] shrink-0 flex-col border-r backdrop-blur-xl md:flex">
        {sidebar}
      </aside>

      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onMobileMenuClose}
          />
          <div className="bg-background border-border/40 animate-in slide-in-from-left absolute inset-y-0 left-0 w-[280px] border-r shadow-2xl duration-300">
            <div className="relative h-full">
              <button
                onClick={onMobileMenuClose}
                className="text-muted-foreground absolute top-4 right-4 z-50 p-2 hover:text-white"
              >
                <X size={20} />
              </button>
              {sidebar}
            </div>
          </div>
        </div>
      )}

      {/* Main Content - Scrollable */}
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Subtle Grid Background */}
        <div
          className="pointer-events-none absolute inset-0 z-0 opacity-[0.03]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />

        {/* Content Container */}
        <div className="relative z-10 flex-1 overflow-x-hidden overflow-y-auto scroll-smooth">
          {children}
        </div>
      </main>
    </div>
  );
};
