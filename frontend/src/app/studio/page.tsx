'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  listAgents,
  listWorkflows,
  deleteAgent,
  getStats,
  AgentConfig,
  GraphConfig,
  SystemStats,
} from '@/lib/api';
import { Plus, Users, Shield, Zap, Box, Network } from 'lucide-react';
import { AgentEditor } from '@/components/studio/AgentEditor';
import { WorkflowViewer } from '@/components/studio/WorkflowViewer';

export default function StudioDashboard() {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [workflows, setWorkflows] = useState<GraphConfig[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<AgentConfig | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<GraphConfig | null>(null);

  useEffect(() => {
    Promise.all([listAgents(), listWorkflows(), getStats()])
      .then(([a, w, s]) => {
        setAgents(a);
        setWorkflows(w);
        setStats(s);
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] p-8 text-white">
      <header className="mb-12 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agent Studio</h1>
          <p className="text-muted-foreground mt-1">Manage your financial superagents.</p>
        </div>
        <Link
          href="/studio/create"
          className="bg-primary hover:bg-primary/90 text-primary-foreground border-primary/50 flex items-center gap-2 rounded-md border px-4 py-2 font-medium transition-colors"
        >
          <Plus size={18} />
          New Superagent
        </Link>
      </header>

      {/* Stats / Overview */}
      <div className="mb-12 grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="mb-2 flex items-center gap-4">
            <div className="rounded-lg bg-blue-500/20 p-2 text-blue-400">
              <Users size={24} />
            </div>
            <span className="text-muted-foreground text-sm font-medium">Active Agents</span>
          </div>
          <div className="text-3xl font-bold">{stats?.active_agents || 0}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="mb-2 flex items-center gap-4">
            <div className="rounded-lg bg-green-500/20 p-2 text-green-400">
              <Shield size={24} />
            </div>
            <span className="text-muted-foreground text-sm font-medium">Compliance Score</span>
          </div>
          <div className="text-3xl font-bold">{stats?.compliance_score || 98}%</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="mb-2 flex items-center gap-4">
            <div className="rounded-lg bg-purple-500/20 p-2 text-purple-400">
              <Zap size={24} />
            </div>
            <span className="text-muted-foreground text-sm font-medium">Total Invocations</span>
          </div>
          <div className="text-3xl font-bold">{stats?.total_invocations || 0}</div>
        </div>
      </div>

      {/* Agents List */}
      <h2 className="mb-6 text-xl font-bold">Deployed Workforce</h2>
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="border-primary h-8 w-8 animate-spin rounded-full border-t-2"></div>
        </div>
      ) : (
        <div className="space-y-12">
          {/* Superagents Section */}
          {workflows.length > 0 && (
            <div>
              <h3 className="text-muted-foreground mb-4 text-lg text-xs font-bold tracking-wider uppercase">
                Superagent Teams
              </h3>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {workflows.map((wf) => (
                  <div
                    key={wf.name}
                    className="group flex flex-col rounded-xl border border-white/10 bg-white/5 p-6 transition-colors hover:border-white/20"
                  >
                    <div className="mb-4 flex items-start justify-between">
                      <div className="rounded-lg bg-white/5 p-3 transition-colors group-hover:bg-white/10">
                        <Network size={24} className="text-purple-400" />
                      </div>
                      <div className="rounded bg-purple-500/20 px-2 py-1 text-xs font-bold text-purple-400 uppercase">
                        Superagent
                      </div>
                    </div>
                    <h3 className="mb-1 text-lg font-bold">{wf.name}</h3>
                    <p className="text-muted-foreground mb-4 line-clamp-2 h-10 text-sm">
                      {wf.description}
                    </p>
                    <div className="mb-6 flex flex-1 flex-wrap content-start gap-2">
                      <span className="rounded border border-white/5 bg-white/5 px-2 py-1 text-xs text-white/50">
                        {wf.nodes.length} Nodes
                      </span>
                    </div>
                    <div className="mt-auto flex gap-2">
                      <button
                        onClick={() => setSelectedWorkflow(wf)}
                        className="flex-1 rounded bg-white/10 py-2 text-sm font-medium transition-colors hover:bg-white/20"
                      >
                        View Graph
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Atomic Agents Section */}
          <div>
            <h3 className="text-muted-foreground mb-4 text-lg text-xs font-bold tracking-wider uppercase">
              Specialized Agents
            </h3>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <div
                  key={agent.name}
                  className="group flex flex-col rounded-xl border border-white/10 bg-white/5 p-6 transition-colors hover:border-white/20"
                >
                  <div className="mb-4 flex items-start justify-between">
                    <div className="rounded-lg bg-white/5 p-3 transition-colors group-hover:bg-white/10">
                      <Box size={24} className="text-white/70" />
                    </div>
                    <div className="rounded bg-green-500/20 px-2 py-1 text-xs font-bold text-green-400 uppercase">
                      Active
                    </div>
                  </div>
                  <h3 className="mb-1 text-lg font-bold">{agent.display_name}</h3>
                  <p className="text-muted-foreground mb-4 line-clamp-2 h-10 text-sm">
                    {agent.description}
                  </p>

                  <div className="mb-6 flex flex-1 flex-wrap content-start gap-2">
                    <span className="rounded border border-blue-500/20 bg-blue-500/10 px-2 py-1 text-xs text-blue-400">
                      {agent.agent.role}
                    </span>
                    {agent.agent.tools.length > 0 && (
                      <span className="rounded border border-white/5 bg-white/5 px-2 py-1 text-xs text-white/50">
                        {agent.agent.tools.length} Tools
                      </span>
                    )}
                  </div>

                  <div className="mt-auto flex gap-2">
                    <button
                      onClick={() => setSelectedAgent(agent)}
                      className="flex-1 rounded bg-white/10 py-2 text-sm font-medium transition-colors hover:bg-white/20"
                    >
                      Inspect
                    </button>
                    <button className="bg-primary/20 hover:bg-primary/30 text-primary flex-1 rounded py-2 text-sm font-medium transition-colors">
                      Invoke
                    </button>
                  </div>
                </div>
              ))}
              {/* Create New Card */}
              <Link
                href="/studio/create"
                className="flex min-h-[280px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-white/10 p-6 text-center transition-colors hover:bg-white/5"
              >
                <div className="mb-4 rounded-full bg-white/5 p-4">
                  <Plus size={32} className="text-white/40" />
                </div>
                <h3 className="mb-1 text-lg font-bold">Deploy New Agent</h3>
                <p className="text-muted-foreground w-2/3 text-sm">
                  Launch a new specialized workforce from a simple prompt.
                </p>
              </Link>
            </div>
          </div>
        </div>
      )}

      {selectedAgent && (
        <AgentEditor
          agent={selectedAgent}
          isOpen={!!selectedAgent}
          onClose={() => setSelectedAgent(null)}
          onSave={(updated) => {
            setAgents((prev) => prev.map((a) => (a.name === updated.name ? updated : a)));
            setSelectedAgent(null);
          }}
          onDelete={async (name) => {
            try {
              await deleteAgent(name);
              setAgents((prev) => prev.filter((a) => a.name !== name));
            } catch (e) {
              throw e; // Propagate to Editor to show error
            }
          }}
        />
      )}

      {selectedWorkflow && (
        <WorkflowViewer
          config={selectedWorkflow}
          isOpen={!!selectedWorkflow}
          onClose={() => setSelectedWorkflow(null)}
        />
      )}
    </div>
  );
}
