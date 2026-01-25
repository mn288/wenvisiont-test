'use client';

import { useState, useEffect } from 'react';
import { AgentConfig, saveAgent, getAgent } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Save, AlertCircle, FileCode, LayoutTemplate, Network } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import yaml from 'js-yaml';

interface AgentEditModalProps {
  // Can provide either full agent object OR just the name to fetch
  agent?: AgentConfig;
  agentName?: string;

  isOpen: boolean;
  onClose: () => void;
  onSave?: (updatedAgent: AgentConfig) => void;
  onDelete?: (agentName: string) => void;
}

export function AgentEditModal({
  agent: initialAgent,
  agentName,
  isOpen,
  onClose,
  onSave,
  onDelete,
}: AgentEditModalProps) {
  const [agent, setAgent] = useState<AgentConfig | null>(initialAgent || null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // YAML Mode State
  const [isYamlMode, setIsYamlMode] = useState(false);
  const [yamlContent, setYamlContent] = useState('');

  // Fetch if only name provided
  useEffect(() => {
    if (isOpen && !initialAgent && agentName) {
      setLoading(true);
      getAgent(agentName)
        .then((data) => {
          setAgent(data);
          setError(null);
        })
        .catch((err) => {
          setError(`Failed to load agent: ${err.message}`);
        })
        .finally(() => setLoading(false));
    } else if (isOpen && initialAgent) {
      setAgent(initialAgent);
    }
  }, [isOpen, initialAgent, agentName]);

  // When switching modes, sync content
  useEffect(() => {
    if (isYamlMode && agent) {
      try {
        // Convert current agent state to YAML
        const dumped = yaml.dump(agent);
        setYamlContent(dumped);
        setError(null);
      } catch (e) {
        setError(`Failed to convert to YAML: ${(e as Error).message}`);
      }
    }
  }, [isYamlMode, agent]);

  const handleSave = async () => {
    if (!agent) return;

    setSaving(true);
    setError(null);
    try {
      let agentToSave = agent;

      // If in YAML mode, parse YAML first
      if (isYamlMode) {
        try {
          const parsed = yaml.load(yamlContent) as AgentConfig;
          if (!parsed || typeof parsed !== 'object') {
            throw new Error('Invalid YAML structure');
          }
          agentToSave = parsed;
        } catch (e) {
          throw new Error(`Invalid YAML: ${(e as Error).message}`);
        }
      }

      const saved = await saveAgent(agentToSave);
      if (onSave) onSave(saved);
      onClose();
    } catch (err) {
      setError((err as Error).message || 'Failed to save agent');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!agent) return;
    if (!onDelete) return;
    if (!confirm(`Are you sure you want to delete ${agent.name}? This cannot be undone.`)) return;

    setDeleting(true);
    try {
      await onDelete(agent.name);
      onClose(); // Close on success
    } catch (err) {
      setError((err as Error).message || 'Failed to delete agent');
    } finally {
      setDeleting(false);
    }
  };

  const updateAgentField = (
    field: keyof AgentConfig['agent'],
    value: string | boolean | string[] | number
  ) => {
    if (!agent) return;
    setAgent((prev) =>
      !prev
        ? null
        : {
            ...prev,
            agent: {
              ...prev.agent,
              [field]: value,
            },
          }
    );
  };

  const updateTaskField = (field: keyof AgentConfig['task'], value: string | boolean) => {
    if (!agent) return;
    setAgent((prev) =>
      !prev
        ? null
        : {
            ...prev,
            task: {
              ...prev.task,
              [field]: value,
            },
          }
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col overflow-hidden border border-white/10 bg-[#0c0c0c] text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>{agent ? `Edit Agent: ${agent.name}` : 'Loading...'}</span>
            <div className="flex rounded-lg border border-white/10 bg-white/5 p-1">
              <button
                onClick={() => setIsYamlMode(false)}
                disabled={!agent}
                className={`rounded-md p-1.5 transition-all ${!isYamlMode ? 'bg-primary text-black' : 'text-white/50 hover:text-white'}`}
                title="Form View"
              >
                <LayoutTemplate size={16} />
              </button>
              <button
                onClick={() => setIsYamlMode(true)}
                disabled={!agent}
                className={`rounded-md p-1.5 transition-all ${isYamlMode ? 'bg-primary text-black' : 'text-white/50 hover:text-white'}`}
                title="YAML View"
              >
                <FileCode size={16} />
              </button>
            </div>
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex justify-center p-8">
              <div className="h-8 w-8 animate-spin rounded-full border-t-2 border-white"></div>
            </div>
          )}

          {agent && !loading && (
            <div className="space-y-4">
              {isYamlMode ? (
                <div className="space-y-2">
                  <Textarea
                    value={yamlContent}
                    onChange={(e) => setYamlContent(e.target.value)}
                    className="h-[500px] border-white/10 bg-[#111] font-mono text-xs leading-relaxed text-blue-100/90"
                    spellCheck={false}
                  />
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Display Name</Label>
                      <Input
                        value={agent.display_name}
                        onChange={(e) => setAgent({ ...agent, display_name: e.target.value })}
                        className="border-white/10 bg-white/5"
                      />
                    </div>
                    <div>
                      <Label>Role</Label>
                      <Input
                        value={agent.agent.role}
                        onChange={(e) => updateAgentField('role', e.target.value)}
                        className="border-white/10 bg-white/5"
                      />
                    </div>
                  </div>

                  <div>
                    <Label>Description</Label>
                    <Textarea
                      value={agent.description}
                      onChange={(e) => setAgent({ ...agent, description: e.target.value })}
                      className="h-20 border-white/10 bg-white/5"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-primary font-bold">Goal</Label>
                    <Textarea
                      value={agent.agent.goal}
                      onChange={(e) => updateAgentField('goal', e.target.value)}
                      className="h-24 border-white/10 bg-white/5"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-primary font-bold">Backstory</Label>
                    <Textarea
                      value={agent.agent.backstory}
                      onChange={(e) => updateAgentField('backstory', e.target.value)}
                      className="h-32 border-white/10 bg-white/5"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="font-bold text-blue-400">Task Description</Label>
                    <p className="text-muted-foreground text-xs">Use {'{request}'} placeholder.</p>
                    <Textarea
                      value={agent.task.description}
                      onChange={(e) => updateTaskField('description', e.target.value)}
                      className="h-32 border-white/10 bg-white/5"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="font-bold text-blue-400">Expected Output</Label>
                    <Textarea
                      value={agent.task.expected_output}
                      onChange={(e) => updateTaskField('expected_output', e.target.value)}
                      className="h-20 border-white/10 bg-white/5"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/5 p-3">
                      <Label>Files Access</Label>
                      <Switch
                        checked={agent.agent.files_access}
                        onCheckedChange={(c) => updateAgentField('files_access', c)}
                      />
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-white/5 bg-white/5 p-3">
                      <Label>S3 Access</Label>
                      <Switch
                        checked={agent.agent.s3_access}
                        onCheckedChange={(c) => updateAgentField('s3_access', c)}
                      />
                    </div>
                  </div>

                  {/* DyLAN / MoA Configuration */}
                  <div className="space-y-4 rounded-xl border border-white/10 bg-white/5 p-4">
                    <h3 className="flex items-center gap-2 font-bold text-purple-400">
                      <Network size={16} /> DyLAN & MoA Configuration
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Importance Score (0.0 - 1.0)</Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="1"
                          value={agent.agent.importance_score}
                          onChange={(e) =>
                            updateAgentField('importance_score', parseFloat(e.target.value))
                          }
                          className="border-white/10 bg-white/5"
                        />
                      </div>
                      <div>
                        <Label>Success Rate (History)</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={agent.agent.success_rate}
                          onChange={(e) =>
                            updateAgentField('success_rate', parseFloat(e.target.value))
                          }
                          className="border-white/10 bg-white/5"
                        />
                      </div>
                    </div>

                    <div>
                      <Label>Task Domains (comma separated)</Label>
                      <Input
                        value={agent.agent.task_domains?.join(', ') || ''}
                        onChange={(e) =>
                          updateAgentField(
                            'task_domains',
                            e.target.value.split(',').map((s) => s.trim())
                          )
                        }
                        placeholder="e.g. coding, research, finance"
                        className="border-white/10 bg-white/5"
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Enable Reflection (Self-Correction)</Label>
                        <p className="text-muted-foreground text-xs">
                          Agent will critique its own output before finishing.
                        </p>
                      </div>
                      <Switch
                        checked={agent.agent.use_reflection}
                        onCheckedChange={(c) => updateAgentField('use_reflection', c)}
                      />
                    </div>
                  </div>
                </>
              )}

              {error && (
                <div className="flex items-center gap-2 rounded border border-red-500/20 bg-red-500/10 p-3 text-red-400">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-none justify-between gap-2 border-t border-white/10 bg-white/5 p-4">
          <div>
            {onDelete && agent && (
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={deleting || saving}
                className="bg-red-500/10 text-red-500 hover:bg-red-500/20"
              >
                {deleting ? 'Deleting...' : 'Delete Agent'}
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose} disabled={saving || deleting}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving || deleting || !agent}
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              {saving ? (
                'Saving...'
              ) : (
                <>
                  <Save size={16} className="mr-2" /> Save Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
