import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight, LayoutGrid, Box } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface DashboardLayoutProps {
  sidebar?: React.ReactNode;
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
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

  // If no sidebar is provided, force collapse or hide the expand button
  const hasSidebar = !!sidebar;

  // Effect removed as render logic already handles !hasSidebar case

  const navItems = [
    { icon: LayoutGrid, label: 'Home', href: '/' },
    { icon: Box, label: 'Agent Studio', href: '/studio' },
  ];

  return (
    <div className="bg-background relative h-screen w-full overflow-hidden">
      {/* Desktop Sidebar - FLOATING DOCK */}
      <motion.aside
        initial={false}
        animate={{
          width: isCollapsed || !hasSidebar ? 60 : 340,
        }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className={cn(
          'fixed top-4 bottom-4 left-4 z-40 hidden md:flex',
          'rounded-2xl border border-white/10 bg-black/60 shadow-2xl backdrop-blur-xl',
          'overflow-hidden transition-all duration-300'
        )}
      >
        <div className="flex h-full w-full">
          {/* === Navigation Rail (Always Visible) === */}
          <div className="flex w-[60px] shrink-0 flex-col items-center gap-6 border-r border-white/5 py-6">
            {/* Brand Icon */}
            <div className="bg-primary/20 border-primary/30 shadow-glow relative mb-2 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg border">
              <div className="bg-primary h-4 w-4 rounded-sm" />
            </div>

            {/* Nav Items */}
            <div className="flex w-full flex-col gap-4 px-2">
              {navItems.map((item) => {
                const isActive =
                  item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'group relative flex aspect-square w-full items-center justify-center rounded-lg transition-colors',
                      isActive
                        ? 'bg-primary/20 text-primary'
                        : 'text-muted-foreground hover:bg-white/10 hover:text-white'
                    )}
                    title={item.label}
                  >
                    <item.icon size={20} />
                    {isActive && (
                      <div className="bg-primary absolute top-1/2 left-0 h-3/5 w-0.5 -translate-y-1/2 rounded-r-full" />
                    )}
                  </Link>
                );
              })}
            </div>

            <div className="text-muted-foreground mt-auto flex flex-col gap-4">
              {/* Bottom actions if needed */}
            </div>
          </div>

          {/* === Sidebar Content Panel (Collapsible) === */}
          {!isCollapsed && hasSidebar && (
            <div className="flex min-w-0 flex-1 flex-col">
              {/* Toggle Handle (Inside the content area now, or absolute) */}
              <button
                onClick={() => setIsCollapsed(true)}
                className="absolute top-4 right-4 z-50 flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-zinc-900/50 text-white shadow-sm transition-transform hover:scale-110 hover:bg-zinc-800"
              >
                <ChevronLeft size={14} />
              </button>

              <div className="w-full flex-1 overflow-hidden">
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                  className="h-full w-full"
                >
                  {sidebar}
                </motion.div>
              </div>
            </div>
          )}
        </div>

        {/* Expand Button (When Collapsed) */}
        {isCollapsed && hasSidebar && (
          <button
            onClick={() => setIsCollapsed(false)}
            className="absolute top-1/2 right-[-12px] z-50 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full border border-white/10 bg-zinc-900 text-white shadow-sm transition-transform hover:scale-110"
            style={{ left: '50px' }} // Position it on the edge
          >
            <ChevronRight size={14} />
          </button>
        )}
        {/* Wait, the absolute button for expand needs to be accessible. 
             If width is 60, right edge is 60.
         */}
        {isCollapsed && hasSidebar && (
          <div className="absolute top-6 left-[60px] z-50 translate-x-[-50%]">
            <button
              onClick={() => setIsCollapsed(false)}
              className="flex h-5 w-5 items-center justify-center rounded-full border border-white/10 bg-zinc-800 text-white shadow-sm hover:bg-zinc-700"
              title="Expand Sidebar"
            >
              <ChevronRight size={12} />
            </button>
          </div>
        )}
      </motion.aside>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 md:hidden"
          >
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={onMobileMenuClose}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="bg-background border-border/40 absolute inset-y-0 left-0 w-[280px] overflow-hidden border-r shadow-2xl"
            >
              <div className="relative flex h-full flex-col">
                {/* Mobile Nav Header */}
                <div className="flex items-center gap-2 border-b border-white/10 p-4">
                  <div className="bg-primary/20 flex h-6 w-6 items-center justify-center rounded-sm">
                    <div className="bg-primary h-3 w-3 rounded-[2px]" />
                  </div>
                  <span className="font-bold">WEnvision</span>
                </div>

                {/* Mobile Nav Links */}
                <div className="flex gap-2 border-b border-white/10 p-2">
                  {navItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onMobileMenuClose}
                      className={cn(
                        'flex flex-1 flex-col items-center gap-1 rounded-lg p-2 text-xs font-medium transition-colors',
                        (item.href === '/' ? pathname === '/' : pathname.startsWith(item.href))
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-white/5'
                      )}
                    >
                      <item.icon size={18} />
                      {item.label}
                    </Link>
                  ))}
                </div>

                {hasSidebar && <div className="flex-1 overflow-y-auto">{sidebar}</div>}

                <button
                  onClick={onMobileMenuClose}
                  className="text-muted-foreground absolute top-4 right-4 z-50 p-2 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="relative h-full w-full overflow-hidden">
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
    </div>
  );
};
