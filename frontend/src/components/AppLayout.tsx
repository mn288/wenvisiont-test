'use client';

import { ReactNode, useState } from 'react';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AppLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppLayout({ sidebar, children }: AppLayoutProps) {
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="selection:bg-primary/30 flex h-screen w-full overflow-hidden bg-[#09090b] font-sans text-white selection:text-white">
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-80 transform border-r border-white/10 bg-black/40 shadow-2xl backdrop-blur-xl transition-transform duration-300 ease-in-out md:relative md:translate-x-0 md:shadow-none',
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebar}
      </aside>

      {/* Main Content */}
      <main className="bg-background relative flex h-full min-w-0 flex-1 flex-col">
        {/* Background Gradients (Moved from page.tsx) */}
        <div className="bg-primary/10 pointer-events-none fixed top-0 left-0 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[128px]" />
        <div className="bg-secondary/5 pointer-events-none fixed right-0 bottom-0 h-[500px] w-[500px] translate-x-1/2 translate-y-1/2 rounded-full blur-[128px]" />

        {/* Mobile Header */}
        <div className="sticky top-0 z-30 flex items-center border-b border-white/10 bg-black/40 p-4 backdrop-blur-md md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="-ml-2 rounded-lg p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
          >
            <Menu size={24} />
          </button>
          <span className="ml-3 bg-gradient-to-r from-white to-gray-400 bg-clip-text text-lg font-semibold text-transparent">
            WEnvision
          </span>
        </div>

        <div className="custom-scrollbar relative flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
}
