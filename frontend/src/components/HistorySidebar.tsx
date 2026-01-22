'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Conversation, fetchConversations, deleteConversation } from '@/lib/api';
import { cn } from '@/lib/utils';
import { MessageSquare, Plus, Loader2, Clock, Trash2 } from 'lucide-react';
import { SettingsDrawer } from './settings/SettingsDrawer';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface HistorySidebarProps {
  currentThreadId?: string;
  onSelectConversation: (conversation: Conversation) => void;
  onNewChat: () => void;
  className?: string;
}

export function HistorySidebar({
  currentThreadId,
  onSelectConversation,
  onNewChat,
  className,
}: HistorySidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [threadToDelete, setThreadToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let isActive = true;
    const loadConversations = async (retryCount = 0) => {
      if (!isActive) return;
      try {
        const data = await fetchConversations();
        if (isActive) {
          setConversations(data);

          // If current thread is new and not yet in the list, retry fetching
          if (
            currentThreadId &&
            currentThreadId !== 'default' &&
            !data.find((c) => c.thread_id === currentThreadId) &&
            retryCount < 10
          ) {
            setTimeout(() => loadConversations(retryCount + 1), 500);
          }
        }
      } catch (error) {
        console.error('Failed to load history:', error);
      } finally {
        if (isActive && retryCount === 0) setLoading(false);
      }
    };
    loadConversations();

    return () => {
      isActive = false;
    };
  }, [currentThreadId]);

  const handleDeleteClick = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    e.preventDefault();
    setThreadToDelete(threadId);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!threadToDelete) return;

    setIsDeleting(true);
    try {
      await deleteConversation(threadToDelete);
      setConversations((prev) => prev.filter((c) => c.thread_id !== threadToDelete));
      if (currentThreadId === threadToDelete) {
        onNewChat();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setThreadToDelete(null);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setThreadToDelete(null);
  };

  return (
    <>
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="border-white/10 bg-gray-900/95 backdrop-blur-xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Delete Conversation</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Are you sure you want to delete this conversation? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={handleCancelDelete}
              className="border-white/10 bg-transparent text-gray-300 hover:bg-white/5 hover:text-white"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-red-600 text-white hover:bg-red-700"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div
        className={cn(
          'border-border bg-card/30 flex h-full flex-col border-r backdrop-blur-xl',
          className
        )}
      >
        <div className="border-border space-y-2 border-b p-4">
          <button
            onClick={onNewChat}
            className="bg-primary/20 hover:bg-primary/30 text-primary-foreground border-primary/20 group flex w-full items-center justify-center gap-2 rounded-xl border py-3 font-medium transition-all duration-200"
          >
            <Plus size={18} className="transition-transform duration-300 group-hover:rotate-90" />
            <span>New Conversation</span>
          </button>
        </div>

        <div className="border-border border-b p-2">
          <Link
            href="/studio"
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-purple-500/20 bg-purple-600/20 py-2 text-xs font-medium text-purple-200 transition-all duration-200 hover:bg-purple-600/30 hover:text-white"
          >
            <span>🤖 Agent Studio</span>
          </Link>
        </div>

        {/* Tabs - REMOVED FILES TAB as it's now global */}
        {/* <div className="flex border-b border-white/10"> ... </div> */}
        <div className="text-muted-foreground border-border border-b px-4 py-2 text-xs font-bold tracking-wider uppercase">
          Recent Missions
        </div>

        <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto p-3">
          {loading ? (
            <div className="text-muted-foreground flex h-40 flex-col items-center justify-center gap-3">
              <Loader2 size={24} className="animate-spin opacity-50" />
              <span className="text-xs">Loading history...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-muted-foreground px-4 py-10 text-center">
              <MessageSquare size={32} className="mx-auto mb-3 opacity-20" />
              <p className="text-sm">No history yet.</p>
              <p className="mt-1 text-xs opacity-50">Start a new chat to begin.</p>
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv)}
                className={cn(
                  'group relative w-full cursor-pointer overflow-hidden rounded-lg p-3 text-left transition-all duration-200',
                  currentThreadId === conv.thread_id
                    ? 'text-foreground border-white/10 bg-white/5 shadow-lg'
                    : 'text-muted-foreground hover:text-foreground border border-transparent hover:bg-white/5'
                )}
              >
                <div className="relative z-10 flex items-start gap-3">
                  <MessageSquare
                    size={16}
                    className={cn(
                      'mt-1 shrink-0 transition-colors',
                      currentThreadId === conv.thread_id
                        ? 'text-primary'
                        : 'text-muted-foreground group-hover:text-foreground'
                    )}
                  />
                  <div className="flex-1 overflow-hidden">
                    <h3 className="mb-1 truncate pr-4 text-sm leading-tight font-medium">
                      {conv.title}
                    </h3>
                    <div className="flex items-center gap-2 text-[10px] opacity-60">
                      <Clock size={10} />
                      <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteClick(e, conv.thread_id)}
                    className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive absolute top-2 right-2 rounded-md p-1.5 opacity-0 transition-all group-hover:opacity-100"
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* Active Indicator */}
                {currentThreadId === conv.thread_id && (
                  <div className="bg-primary absolute top-1/2 left-0 h-8 w-1 -translate-y-1/2 rounded-r-full" />
                )}
              </div>
            ))
          )}
        </div>

        <div className="text-muted-foreground border-border flex items-center justify-between border-t p-3 text-xs">
          <span>GenAI Agent Demo v1.0</span>
          <SettingsDrawer />
        </div>
      </div>
    </>
  );
}
