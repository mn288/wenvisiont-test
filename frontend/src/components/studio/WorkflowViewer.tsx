import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { GraphConfig } from '@/lib/api';
import { ArchitectureVisualizer } from './ArchitectureVisualizer';
import { Button } from '@/components/ui/button';

interface WorkflowViewerProps {
  config: GraphConfig;
  isOpen: boolean;
  onClose: () => void;
}

export function WorkflowViewer({ config, isOpen, onClose }: WorkflowViewerProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[85vh] max-w-4xl overflow-hidden border border-white/10 bg-[#0c0c0c] p-0 text-white">
        <DialogHeader className="border-b border-white/10 px-6 py-4">
          <DialogTitle className="flex items-center justify-between">
            <div className="flex flex-col gap-1">
              <span>{config.name}</span>
              <span className="text-muted-foreground text-xs font-normal">
                {config.description}
              </span>
            </div>
            <div className="text-muted-foreground flex items-center gap-2 text-xs">
              <span className="rounded bg-white/5 px-2 py-1">{config.nodes.length} Nodes</span>
              <span className="rounded bg-white/5 px-2 py-1">{config.edges.length} Edges</span>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="h-[600px] w-full bg-[#151515] p-4">
          <ArchitectureVisualizer config={config} />
        </div>

        <div className="flex justify-end gap-2 border-t border-white/10 bg-white/5 px-6 py-4">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
