import React, { useEffect, useState } from 'react';
import {
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  FileCode,
  FileJson,
  FileText,
  Image as ImageIcon,
  MoreVertical,
  Download,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ReactMarkdown from 'react-markdown';

interface FileItem {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
}

const getFileIcon = (name: string) => {
  if (name.endsWith('.ts') || name.endsWith('.tsx') || name.endsWith('.js') || name.endsWith('.py'))
    return FileCode;
  if (name.endsWith('.json') || name.endsWith('.yaml') || name.endsWith('.yml')) return FileJson;
  if (name.endsWith('.md') || name.endsWith('.txt')) return FileText;
  if (name.endsWith('.png') || name.endsWith('.jpg')) return ImageIcon;
  return File;
};

export function FileExplorer({ initialPath = '.' }: { initialPath?: string }) {
  const [cwd, setCwd] = useState(initialPath);
  const [items, setItems] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [previewFile, setPreviewFile] = useState<{ name: string; content: string } | null>(null);

  useEffect(() => {
    setCwd(initialPath);
  }, [initialPath]);

  const fetchFiles = async (path: string) => {
    // Removed default parameter to force explicit path
    setIsLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/files/list?path=${encodeURIComponent(path)}`);
      if (res.status === 404) {
        // If folder doesn't exist yet (new thread), just show empty or fallback
        setItems([]);
        return;
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setItems(data);
        // Only update CWD if successful
        setCwd(path);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const readFile = async (path: string) => {
    try {
      const res = await fetch('http://localhost:8000/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      const data = await res.json();
      if (data.content) {
        setPreviewFile({ name: path.split('/').pop() || path, content: data.content });
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchFiles(cwd);
  }, [cwd]); // Trigger fetch when cwd changes (which happens via initialPath or navigation)

  const handleNavigate = (path: string) => {
    if (path === '..') {
      const parts = cwd.split('/');
      parts.pop();
      const newPath = parts.join('/') || '.';
      fetchFiles(newPath);
    } else {
      fetchFiles(path);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-white/10 bg-black/40 shadow-2xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 bg-white/5 px-4 py-3">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="bg-primary/20 rounded-md p-1.5">
            <Folder size={14} className="text-primary" />
          </div>
          <span className="direction-rtl truncate font-mono text-xs text-white/70">
            {cwd === initialPath ? '/' : cwd.replace(initialPath + '/', '')}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => fetchFiles(cwd)}
            className={clsx(
              'text-muted-foreground rounded-md p-1.5 transition-all hover:bg-white/10 hover:text-white',
              isLoading && 'text-primary animate-spin'
            )}
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
      {/* File List */}
      <div className="custom-scrollbar flex-1 space-y-0.5 overflow-y-auto p-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={cwd}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.15 }}
          >
            {cwd !== initialPath && cwd !== '.' && (
              <div
                onClick={() => handleNavigate('..')}
                className="text-muted-foreground group flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition-all hover:bg-white/5 hover:text-white"
              >
                <div className="flex items-center gap-3">
                  <ChevronDown
                    size={16}
                    className="opacity-50 transition-opacity group-hover:opacity-100"
                  />
                  <span className="font-medium">..</span>
                </div>
              </div>
            )}

            {items.length === 0 && !isLoading && (
              <div className="text-muted-foreground py-8 text-center text-xs italic opacity-50">
                Empty directory
              </div>
            )}

            {items.map((item) => {
              const Icon = item.type === 'directory' ? Folder : getFileIcon(item.name);
              return (
                <motion.div
                  layout
                  key={item.path}
                  onClick={() =>
                    item.type === 'directory' ? handleNavigate(item.path) : readFile(item.path)
                  }
                  className={clsx(
                    'group flex cursor-pointer items-center justify-between rounded-md border border-transparent px-3 py-2 text-sm transition-all',
                    item.type === 'directory'
                      ? 'text-blue-100 hover:border-blue-500/20 hover:bg-blue-500/10'
                      : 'text-gray-300 hover:border-white/10 hover:bg-white/5'
                  )}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <Icon
                      size={16}
                      className={clsx(
                        'transition-colors',
                        item.type === 'directory'
                          ? 'text-blue-400 group-hover:text-blue-300'
                          : 'text-gray-500 group-hover:text-gray-300'
                      )}
                    />
                    <span className="truncate font-medium opacity-90 group-hover:opacity-100">
                      {item.name}
                    </span>
                  </div>
                  {item.type === 'directory' && (
                    <ChevronRight
                      size={14}
                      className="-translate-x-2 text-blue-400 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-50"
                    />
                  )}
                </motion.div>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* File Preview Dialog */}
      <Dialog open={!!previewFile} onOpenChange={(o) => !o && setPreviewFile(null)}>
        <DialogContent className="flex max-h-[85vh] max-w-4xl flex-col gap-0 overflow-hidden border-white/10 bg-[#0F0F10] p-0">
          <DialogHeader className="flex flex-row items-center justify-between border-b border-white/5 bg-white/5 px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="rounded-lg border border-white/5 bg-white/5 p-2">
                {previewFile &&
                  React.createElement(getFileIcon(previewFile.name), {
                    size: 18,
                    className: 'text-primary',
                  })}
              </div>
              <div className="flex flex-col">
                <DialogTitle className="font-mono text-sm">{previewFile?.name}</DialogTitle>
                <span className="text-muted-foreground text-[10px] tracking-widest uppercase">
                  {previewFile?.name.split('.').pop()} FILE
                </span>
              </div>
            </div>
            {/* Could add download button here */}
          </DialogHeader>
          <div className="custom-scrollbar flex-1 overflow-auto bg-[#0a0a0a] p-6 text-sm text-gray-300">
            {previewFile?.name.endsWith('.md') ? (
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{previewFile.content}</ReactMarkdown>
              </div>
            ) : (
              <>
                <SyntaxHighlighter
                  language={previewFile?.name.split('.').pop() || 'text'}
                  style={vscDarkPlus}
                  customStyle={{
                    background: 'transparent',
                    margin: 0,
                    padding: 0,
                    fontSize: '13px',
                  }}
                  showLineNumbers={true}
                  wrapLines={true}
                >
                  {previewFile?.content || ''}
                </SyntaxHighlighter>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
