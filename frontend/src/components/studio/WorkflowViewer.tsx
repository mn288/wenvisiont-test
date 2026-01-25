import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { GraphConfig } from '@/lib/api';
import { ArchitectureVisualizer } from './ArchitectureVisualizer';
import { Button } from '@/components/ui/button';
import { AgentEditModal } from '@/components/agents/AgentEditModal';

interface WorkflowViewerProps {
  config: GraphConfig;
  isOpen: boolean;
  onClose: () => void;
  onDelete?: (name: string) => void;
}

export function WorkflowViewer({ config, isOpen, onClose, onDelete }: WorkflowViewerProps) {
  const [editingAgentName, setEditingAgentName] = useState<string | null>(null);

  const handleNodeClick = (nodeId: string, nodeType: string, nodeLabel: string) => {
    // Only allow editing for certain types (exclude supervisor if generated purely by code, but here types are agent names)
    // We assume any nodeType that is NOT 'supervisor' might be an agent.
    // However, if the type is literally 'supervisor', it might not be a CRUD-able agent in the registry (it's hardcoded logic).
    // Let's filter out 'supervisor' type if it's the internal logic one.
    if (nodeType === 'supervisor') {
      // Internal supervisor usually doesn't have a config page yet.
      // If the user wants to config the supervisor, we might need a separate SupervisorEditor.
      // For now, ignore.
      return;
    }

    // Check if it's a Team (Superagent Team)
    // If nodeType matches a known workflow name, we could open THAT workflow?
    // But modifying `config.nodes` logic: nodeType is the registry name.

    // Optimistic: Try to open editor for it.
    setEditingAgentName(nodeType);
  };

  return (
    <>
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
            <ArchitectureVisualizer config={config} onNodeClick={handleNodeClick} />
          </div>

          <div className="flex justify-end gap-2 border-t border-white/10 bg-white/5 px-6 py-4">
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
            {onDelete && (
              <Button
                variant="destructive"
                onClick={() => {
                  if (
                    confirm(
                      'Are you sure you want to delete this workflow? This action cannot be undone.'
                    )
                  ) {
                    onDelete(config.name);
                    onClose();
                  }
                }}
              >
                Delete Workflow
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Nested Editor Dialog */}
      <Dialog open={!!editingAgentName} onOpenChange={(o) => !o && setEditingAgentName(null)}>
        <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto border border-gray-700 bg-gray-900 text-white">
          <DialogHeader className="sr-only">
            <DialogTitle>Edit Agent</DialogTitle>
          </DialogHeader>
          {editingAgentName && (
            <AgentEditModal
              agentName={editingAgentName}
              isOpen={!!editingAgentName}
              onClose={() => setEditingAgentName(null)}
              onSave={() => {
                setEditingAgentName(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
