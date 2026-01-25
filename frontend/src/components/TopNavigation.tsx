import React from 'react';
import { Menu, FileCode, Terminal, Layout, Settings, Box, LayoutGrid } from 'lucide-react';
import { SettingsDrawer } from '@/components/settings/SettingsDrawer';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

interface TopNavigationProps {
  onToggleHistory: () => void;
  onToggleFiles: () => void;
  isHistoryOpen: boolean;
  isFilesOpen: boolean;
}

export function TopNavigation({
  onToggleHistory,
  onToggleFiles,
  isHistoryOpen,
  isFilesOpen,
}: TopNavigationProps) {
  const pathname = usePathname();

  const navItems = [
    { icon: LayoutGrid, label: 'Home', href: '/' },
    { icon: Box, label: 'Agent Studio', href: '/studio' },
  ];

  return (
    <header className="fixed top-0 right-0 left-0 z-50 flex h-16 items-center justify-between border-b border-white/5 bg-black/80 px-4 backdrop-blur-md">
      {/* Left: Branding & History Toggle */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleHistory}
          className={cn(
            'text-muted-foreground hover:text-white',
            isHistoryOpen && 'text-primary bg-primary/10'
          )}
          title="Toggle History"
        >
          <Menu size={20} />
        </Button>

        <div className="flex items-center gap-3">
          <div className="bg-primary/20 border-primary/30 shadow-glow flex h-8 w-8 items-center justify-center rounded-lg border">
            <div className="bg-primary h-4 w-4 rounded-sm" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white/90">WEnvision</span>
        </div>

        {/* Separator */}
        <div className="mx-2 h-6 w-px bg-white/10" />

        {/* Navigation Links */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                (item.href === '/' ? pathname === '/' : pathname.startsWith(item.href))
                  ? 'bg-white/10 text-white'
                  : 'text-muted-foreground hover:bg-white/5 hover:text-white'
              )}
            >
              <item.icon size={16} />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Right: Tools & Settings */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleFiles}
          className={cn(
            'text-muted-foreground gap-2 hover:text-white',
            isFilesOpen && 'text-primary bg-primary/10'
          )}
        >
          <FileCode size={18} />
          <span className="hidden sm:inline">Workspace</span>
        </Button>

        <div className="mx-2 h-6 w-px bg-white/10" />

        <SettingsDrawer />
      </div>
    </header>
  );
}
