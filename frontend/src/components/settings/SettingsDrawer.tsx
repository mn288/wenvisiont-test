import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../ui/sheet';
import { Settings, Loader2, CheckCircle2, XCircle, Plus, Trash2 } from 'lucide-react';
import {
  getInfrastructureConfig,
  updateInfrastructureConfig,
  verifyS3Connection,
  S3Config,
  getConfiguration,
  saveConfiguration,
} from '@/lib/api';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// MCP Types
interface MCPServer {
  id: number;
  name: string;
  type: 'stdio' | 'sse' | 'https';
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
}

export const SettingsDrawer = () => {
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState<S3Config>({
    bucket_name: '',
    region_name: 'us-east-1',
    access_key_id: '',
    secret_access_key: '',
  });
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');

  // MCP State
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [mcpLoading, setMcpLoading] = useState(false);
  const [newServer, setNewServer] = useState<Partial<MCPServer>>({
    name: '',
    type: 'https',
    url: '',
  });

  // Infra Config State
  const [infraConfigText, setInfraConfigText] = useState('');
  const [infraLoading, setInfraLoading] = useState(false);

  useEffect(() => {
    if (open) {
      loadConfig();
      fetchMcpServers();
      loadInfraConfig();
    }
  }, [open]);

  const loadInfraConfig = async () => {
    try {
      const config = await getConfiguration('infrastructure_config');
      if (config && config.value) {
        setInfraConfigText(String(config.value));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveInfra = async () => {
    setInfraLoading(true);
    try {
      await saveConfiguration('infrastructure_config', infraConfigText);
      alert('Configuration saved!');
    } catch {
      alert('Failed to save configuration');
    } finally {
      setInfraLoading(false);
    }
  };

  const loadConfig = async () => {
    try {
      const data = await getInfrastructureConfig();
      if (data.s3) {
        setConfig((prev) => ({ ...prev, ...data.s3 }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMcpServers = async () => {
    setMcpLoading(true);
    try {
      const res = await fetch('http://localhost:8000/mcp/servers');
      if (res.ok) {
        const data = await res.json();
        setMcpServers(data);
      }
    } catch (error) {
      console.error('Failed to fetch servers:', error);
    } finally {
      setMcpLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await updateInfrastructureConfig({ s3: config });
      setOpen(false);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setStatus('testing');
    try {
      await verifyS3Connection(config);
      setStatus('success');
    } catch {
      setStatus('error');
    }
  };

  const handleAddMcpServer = async () => {
    try {
      const payload = {
        name: newServer.name,
        type: 'https',
        url: newServer.url,
      };

      const res = await fetch('http://localhost:8000/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        fetchMcpServers();
        setNewServer({ name: '', type: 'https', url: '' });
      } else {
        const err = await res.text();
        alert(`Error: ${err}`);
      }
    } catch (error) {
      console.error('Failed to add server:', error);
    }
  };

  const handleDeleteMcpServer = async (id: number) => {
    if (!confirm('Are you sure you want to delete this server?')) return;
    try {
      const res = await fetch(`http://localhost:8000/mcp/servers/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setMcpServers(mcpServers.filter((s) => s.id !== id));
      }
    } catch (error) {
      console.error('Failed to delete server:', error);
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button className="text-muted-foreground rounded-md p-2 transition-colors hover:bg-white/10 hover:text-white">
          <Settings size={20} />
        </button>
      </SheetTrigger>
      <SheetContent className="border-border/40 bg-background/95 w-[400px] border-l backdrop-blur-xl">
        <SheetHeader>
          <SheetTitle>Settings & Infrastructure</SheetTitle>
        </SheetHeader>

        <Tabs defaultValue="aws" className="mt-6">
          <TabsList className="w-full">
            <TabsTrigger value="aws" className="flex-1">
              AWS S3
            </TabsTrigger>
            <TabsTrigger value="mcp" className="flex-1">
              MCP Servers
            </TabsTrigger>
            <TabsTrigger value="local" className="flex-1">
              Local
            </TabsTrigger>
            <TabsTrigger value="infra" className="flex-1">
              Infra
            </TabsTrigger>
          </TabsList>

          <TabsContent value="aws" className="mt-4 space-y-4">
            <div className="space-y-2">
              <Label>Bucket Name</Label>
              <Input
                value={config.bucket_name}
                onChange={(e) => setConfig({ ...config, bucket_name: e.target.value })}
                placeholder="my-agent-bucket"
              />
            </div>
            <div className="space-y-2">
              <Label>Region</Label>
              <Input
                value={config.region_name}
                onChange={(e) => setConfig({ ...config, region_name: e.target.value })}
                placeholder="us-east-1"
              />
            </div>
            <div className="space-y-2">
              <Label>Access Key ID</Label>
              <Input
                value={config.access_key_id}
                onChange={(e) => setConfig({ ...config, access_key_id: e.target.value })}
                placeholder="AKIA..."
              />
            </div>
            <div className="space-y-2">
              <Label>Secret Access Key</Label>
              <Input
                type="password"
                value={config.secret_access_key}
                onChange={(e) => setConfig({ ...config, secret_access_key: e.target.value })}
                placeholder="********"
              />
            </div>

            <div className="flex items-center justify-between pt-4">
              <div className="flex items-center gap-2">
                {status === 'testing' && (
                  <Loader2 size={16} className="animate-spin text-blue-400" />
                )}
                {status === 'success' && (
                  <span className="flex items-center gap-1 text-xs text-green-400">
                    <CheckCircle2 size={14} /> Connected
                  </span>
                )}
                {status === 'error' && (
                  <span className="flex items-center gap-1 text-xs text-red-400">
                    <XCircle size={14} /> Failed
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTest}
                  disabled={status === 'testing'}
                >
                  Test
                </Button>
                <Button size="sm" onClick={handleSave} disabled={loading}>
                  {loading ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="mcp" className="mt-4 space-y-4">
            <div className="space-y-3">
              <div className="space-y-2">
                <Label>Server Name</Label>
                <Input
                  value={newServer.name}
                  onChange={(e) => setNewServer({ ...newServer, name: e.target.value })}
                  placeholder="My Server"
                />
              </div>
              <div className="space-y-2">
                <Label>HTTPS URL</Label>
                <Input
                  value={newServer.url}
                  onChange={(e) => setNewServer({ ...newServer, url: e.target.value })}
                  placeholder="https://my-mcp-server.com/sse"
                />
              </div>
            </div>

            <Button
              onClick={handleAddMcpServer}
              className="w-full"
              disabled={!newServer.name || !newServer.url}
            >
              <Plus size={16} className="mr-2" /> Add Server
            </Button>

            <div className="border-border/40 space-y-2 border-t pt-4">
              <h4 className="text-muted-foreground text-xs font-semibold tracking-wider uppercase">
                Configured Servers
              </h4>
              {mcpLoading && <p className="text-muted-foreground text-xs">Loading...</p>}
              {!mcpLoading && mcpServers.length === 0 && (
                <p className="text-muted-foreground text-xs">No servers configured.</p>
              )}

              {mcpServers.map((server) => (
                <div
                  key={server.id}
                  className="bg-muted/20 border-border/40 flex items-center justify-between rounded-md border p-2.5"
                >
                  <div>
                    <div className="text-sm font-medium">{server.name}</div>
                    <div className="text-muted-foreground font-mono text-[10px]">
                      {server.type} • {server.url}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteMcpServer(server.id)}
                    className="text-muted-foreground p-1 transition-colors hover:text-red-400"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="local">
            <div className="bg-muted/20 border-border/40 text-muted-foreground rounded-md border p-4 text-sm">
              <p>Local workspace is managed automatically per session.</p>
              <p className="mt-2 font-mono text-xs">
                /tmp/agent_studio/&#123;thread_id&#125;/workspace
              </p>
            </div>
          </TabsContent>

          <TabsContent value="infra">
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label>Global Infrastructure Context</Label>
                <p className="text-muted-foreground text-xs">
                  This text will be injected into the agent generation prompt to inform the LLM
                  about available infrastructure.
                </p>
                <Textarea
                  value={infraConfigText}
                  onChange={(e) => setInfraConfigText(e.target.value)}
                  placeholder="# Example:\nFilesystem: /data\nS3 Bucket: my-bucket"
                  className="min-h-[200px] font-mono text-xs"
                />
              </div>
              <Button onClick={handleSaveInfra} disabled={infraLoading} className="w-full">
                {infraLoading ? 'Saving...' : 'Save Context'}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
};
