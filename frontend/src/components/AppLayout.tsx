"use client";

import { ReactNode, useState } from "react";
import { Menu } from "lucide-react";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function AppLayout({ sidebar, children }: AppLayoutProps) {
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-[#09090b] text-white overflow-hidden font-sans selection:bg-primary/30 selection:text-white">
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-80 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 bg-black/40 backdrop-blur-xl border-r border-white/10 shadow-2xl md:shadow-none",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {sidebar}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 relative h-full bg-background">
        {/* Background Gradients (Moved from page.tsx) */}
        <div className="fixed top-0 left-0 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[128px] -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="fixed bottom-0 right-0 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[128px] translate-x-1/2 translate-y-1/2 pointer-events-none" />

        {/* Mobile Header */}
        <div className="md:hidden flex items-center p-4 border-b border-white/10 bg-black/40 backdrop-blur-md sticky top-0 z-30">
          <button 
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            <Menu size={24} />
          </button>
          <span className="ml-3 font-semibold text-lg bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">WEnvision</span>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar relative">
           {children}
        </div>
      </main>
    </div>
  );
}
