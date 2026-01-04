'use client';

import React, { useState, useEffect } from 'react';
import { generateAgent, saveAgent, listMCPServers, AgentConfig } from '@/lib/api';
import { Button } from '@/components/ui/button';

import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

interface AgentGeneratorProps {
  open: boolean;
  onClose: () => void;
  onGenerate: (config?: AgentConfig) => void;
}

export default function AgentGenerator({ open, onClose, onGenerate }: AgentGeneratorProps) {
  const [prompt, setPrompt] = useState('');
  const [filesAccess, setFilesAccess] = useState(false);
  const [s3Access, setS3Access] = useState(false);
  const [mcpServers, setMcpServers] = useState<string[]>([]);

  const [availableMcp, setAvailableMcp] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listMCPServers().then(setAvailableMcp);
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const config = await generateAgent(prompt, filesAccess, s3Access, mcpServers);
      // Auto-save? Or let user review?
      // Let's explicitly save so it persists
      await saveAgent(config);
      onGenerate(config);
      onClose();
    } catch (e) {
      alert('Failed to generate: ' + e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="border-gray-700 bg-gray-800 text-white">
        <DialogHeader>
          <DialogTitle>Generate Agent with AI</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label>Describe your agent</Label>
            <Textarea
              placeholder="e.g. A python coding assistant that can read files and explain code."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="h-32 border-gray-600 bg-gray-900"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Switch checked={filesAccess} onCheckedChange={setFilesAccess} />
            <Label>Allow File System Access</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Switch checked={s3Access} onCheckedChange={setS3Access} />
            <Label>Allow S3 Access</Label>
          </div>

          <div>
            <Label>Attach MCP Servers</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {availableMcp.map((srv) => (
                <div
                  key={srv}
                  className="flex items-center space-x-1 rounded bg-gray-900 p-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={mcpServers.includes(srv)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setMcpServers([...mcpServers, srv]);
                      } else {
                        setMcpServers(mcpServers.filter((x) => x !== srv));
                      }
                    }}
                  />
                  <span>{srv}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={loading || !prompt}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {loading ? 'Generating...' : 'Generate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
