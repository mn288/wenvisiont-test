import React, { useState, useEffect } from 'react';
import { Plus, Trash2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { getMcpServers, createMcpServer, deleteMcpServer, MCPServer } from '@/lib/api/mcp';

export const MCPSettings = () => {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newServer, setNewServer] = useState<{ name: string; url: string }>({
    name: '',
    url: '',
  });
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    fetchServers();
  }, []);

  const fetchServers = async () => {
    setLoading(true);
    try {
      const data = await getMcpServers();
      setServers(data);
    } catch (err: unknown) {
      console.error(err);
      setError('Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  const handleAddServer = async () => {
    if (!newServer.name || !newServer.url) return;
    setAdding(true);
    setError(null);
    try {
      await createMcpServer({
        name: newServer.name,
        type: 'sse', // Defaulting to SSE for now as per UI simple input
        url: newServer.url,
      });
      setNewServer({ name: '', url: '' });
      fetchServers();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to add server');
      }
    } finally {
      setAdding(false);
    }
  };

  const handleDeleteServer = async (name: string) => {
    if (!confirm(`Delete MCP server "${name}"?`)) return;
    try {
      await deleteMcpServer(name);
      setServers(servers.filter((s) => s.name !== name));
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to delete server');
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Add Server Form */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium">Add New Server</h3>
        <div className="space-y-2">
          <Label>Name</Label>
          <Input
            value={newServer.name}
            onChange={(e) => setNewServer({ ...newServer, name: e.target.value })}
            placeholder="e.g. math-server"
          />
        </div>
        <div className="space-y-2">
          <Label>SSE URL</Label>
          <Input
            value={newServer.url}
            onChange={(e) => setNewServer({ ...newServer, url: e.target.value })}
            placeholder="http://localhost:8000/sse"
          />
        </div>
        <Button
          onClick={handleAddServer}
          className="w-full"
          disabled={!newServer.name || !newServer.url || adding}
        >
          {adding ? (
            'Verifying...'
          ) : (
            <>
              <Plus size={16} className="mr-2" /> Add Server
            </>
          )}
        </Button>
      </div>

      {/* Server List */}
      <div className="border-border/40 mt-6 border-t pt-4">
        <h4 className="text-muted-foreground mb-3 text-xs font-semibold tracking-wider uppercase">
          Configured Servers
        </h4>

        {loading && <p className="text-muted-foreground text-xs">Loading...</p>}

        {!loading && servers.length === 0 && (
          <div className="text-muted-foreground text-xs italic">No servers configured.</div>
        )}

        <div className="space-y-2">
          {servers.map((server) => (
            <div
              key={server.id}
              className="border-border/40 bg-muted/20 flex items-center justify-between rounded-md border p-3"
            >
              <div>
                <div className="text-sm font-medium">{server.name}</div>
                <div className="text-muted-foreground font-mono text-[10px]">
                  {server.type} • {server.url || server.command}
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDeleteServer(server.name)}
                className="text-muted-foreground h-8 w-8 hover:bg-transparent hover:text-red-400"
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
