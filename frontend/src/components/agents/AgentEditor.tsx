'use client';

import React, { useState, useEffect } from 'react';
import { getAgent, saveAgent, AgentConfig, listMCPServers } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Editor from '@monaco-editor/react';
import yaml from 'js-yaml';

interface AgentEditorProps {
  name?: string; // If undefined, creating new
  onClose: () => void;
  onSave: () => void;
}

const DEFAULT_CONFIG: AgentConfig = {
  name: 'new_agent',
  display_name: 'New Agent',
  description: 'Description',
  output_state_key: 'output',
  agent: {
    role: 'Role',
    goal: 'Goal',
    backstory: 'Backstory',
    verbose: true,
    allow_delegation: false,
    tools: [],
    mcp_servers: [],
    files_access: false,
    s3_access: false,
  },
  task: {
    description: 'Task description',
    expected_output: 'Expected output',
    async_execution: true,
  },
};

export default function AgentEditor({ name, onClose, onSave }: AgentEditorProps) {
  const [config, setConfig] = useState<AgentConfig>(DEFAULT_CONFIG);
  const [yamlContent, setYamlContent] = useState('');
  const [activeTab, setActiveTab] = useState('form');
  const [mcpOptions, setMcpOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listMCPServers().then(setMcpOptions);
    if (name) {
      const loadAgent = async () => {
        // Yield to avoid sync setState in effect
        await Promise.resolve();
        setLoading(true);
        try {
          const data = await getAgent(name);
          setConfig(data);
          setYamlContent(yaml.dump(data));
        } finally {
          setLoading(false);
        }
      };
      loadAgent();
    } else {
      setYamlContent(yaml.dump(DEFAULT_CONFIG));
    }
  }, [name]);

  const handleSave = async () => {
    try {
      const finalConfig = activeTab === 'yaml' ? (yaml.load(yamlContent) as AgentConfig) : config;
      await saveAgent(finalConfig);
      onSave();
      onClose();
    } catch (e: unknown) {
      alert('Failed to save: ' + e);
    }
  };

  const handleYamlChange = (value: string | undefined) => {
    if (value) setYamlContent(value);
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const updateConfig = (field: string, value: any) => {
    const newConfig = { ...config };
    // Deep merge helper not really needed if we do simple paths
    // Simple path logic
    if (field.startsWith('agent.')) {
      const key = field.split('.')[1];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (newConfig.agent as any)[key] = value;
    } else if (field.startsWith('task.')) {
      const key = field.split('.')[1];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (newConfig.task as any)[key] = value;
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (newConfig as any)[field] = value;
    }
    setConfig(newConfig);
    // Update YAML
    try {
      setYamlContent(yaml.dump(newConfig));
    } catch {}
  };

  if (loading) return <div className="text-white">Loading...</div>;

  return (
    <div className="space-y-4 text-white">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">{name ? 'Edit Agent' : 'Create Agent'}</h2>
        <div className="space-x-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} className="bg-green-600 hover:bg-green-700">
            Save
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-gray-800">
          <TabsTrigger value="form">Form View</TabsTrigger>
          <TabsTrigger value="yaml">YAML View</TabsTrigger>
        </TabsList>

        <TabsContent value="form">
          <Card className="border-gray-700 bg-gray-800">
            <CardContent className="space-y-4 pt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Name (Snake Case)</Label>
                  <Input
                    value={config.name}
                    onChange={(e) => updateConfig('name', e.target.value)}
                    className="border-gray-600 bg-gray-900"
                  />
                </div>
                <div>
                  <Label>Display Name</Label>
                  <Input
                    value={config.display_name}
                    onChange={(e) => updateConfig('display_name', e.target.value)}
                    className="border-gray-600 bg-gray-900"
                  />
                </div>
              </div>

              <div>
                <Label>Role</Label>
                <Input
                  value={config.agent.role}
                  onChange={(e) => updateConfig('agent.role', e.target.value)}
                  className="border-gray-600 bg-gray-900"
                />
              </div>
              <div>
                <Label>Goal</Label>
                <Textarea
                  value={config.agent.goal}
                  onChange={(e) => updateConfig('agent.goal', e.target.value)}
                  className="border-gray-600 bg-gray-900"
                />
              </div>
              <div>
                <Label>Backstory</Label>
                <Textarea
                  value={config.agent.backstory}
                  onChange={(e) => updateConfig('agent.backstory', e.target.value)}
                  className="h-24 border-gray-600 bg-gray-900"
                />
              </div>

              <div className="border-t border-gray-700 pt-4">
                <h3 className="mb-2 font-bold">Tools & Capabilities</h3>
                <div className="mb-2 flex items-center space-x-2">
                  <Switch
                    checked={config.agent.files_access}
                    onCheckedChange={(c) => updateConfig('agent.files_access', c)}
                  />
                  <Label>Allow File System Access</Label>
                </div>
                <div className="mb-4 flex items-center space-x-2">
                  <Switch
                    checked={config.agent.s3_access}
                    onCheckedChange={(c) => updateConfig('agent.s3_access', c)}
                  />
                  <Label>Allow S3 Access</Label>
                </div>

                <Label>MCP Servers</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {mcpOptions.map((srv) => (
                    <div key={srv} className="flex items-center space-x-1 rounded bg-gray-900 p-2">
                      <input
                        type="checkbox"
                        checked={config.agent.mcp_servers?.includes(srv)}
                        onChange={(e) => {
                          const current = config.agent.mcp_servers || [];
                          if (e.target.checked) {
                            updateConfig('agent.mcp_servers', [...current, srv]);
                          } else {
                            updateConfig(
                              'agent.mcp_servers',
                              current.filter((x) => x !== srv)
                            );
                          }
                        }}
                      />
                      <span>{srv}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="yaml">
          <div className="h-[500px] overflow-hidden rounded border border-gray-700">
            <Editor
              height="100%"
              defaultLanguage="yaml"
              value={yamlContent}
              theme="vs-dark"
              onChange={handleYamlChange}
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
