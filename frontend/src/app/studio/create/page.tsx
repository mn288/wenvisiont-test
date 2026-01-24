'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { architectAgent, generateAgent, GraphConfig, AgentConfig } from '@/lib/api';
import { ArchitectureVisualizer } from '@/components/studio/ArchitectureVisualizer';
import { ArrowLeft, Sparkles, AlertCircle, Check, Network, User } from 'lucide-react';
import Link from 'next/link';
import { saveAgent } from '@/lib/api';

type Mode = 'superagent' | 'standalone';

export default function CreateAgentWizard() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>('superagent');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);

  // Results
  const [graphConfig, setGraphConfig] = useState<GraphConfig | null>(null);
  const [agentConfig, setAgentConfig] = useState<AgentConfig | null>(null);

  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setGraphConfig(null);
    setAgentConfig(null);

    try {
      if (mode === 'superagent') {
        const result = await architectAgent(prompt);
        setGraphConfig(result);
      } else {
        const result = await generateAgent(prompt, true, false, []);
        setAgentConfig(result);
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to generate.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    // If standalone, save the agent configuration.
    if (mode === 'standalone' && agentConfig) {
      try {
        await saveAgent(agentConfig);
      } catch (e) {
        setError(`Failed to save agent: ${(e as Error).message}`);
        return;
      }
    }
    // For Superagents, save the graph configuration.
    if (mode === 'superagent' && graphConfig) {
      try {
        const { saveWorkflow } = await import('@/lib/api');
        await saveWorkflow(graphConfig);
      } catch (e) {
        console.error(e);
        setError('Failed to save workflow.');
        return;
      }
    }

    router.push('/studio');
  };

  return (
    <div className="flex min-h-screen flex-col bg-[#0a0a0a] text-white">
      {/* Header */}
      <header className="flex h-16 items-center border-b border-white/10 bg-black/40 px-6 backdrop-blur">
        <Link
          href="/studio"
          className="text-muted-foreground mr-4 rounded-full p-2 transition-colors hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft size={20} />
        </Link>
        <h1 className="font-bold">Create New {mode === 'superagent' ? 'Superagent' : 'Agent'}</h1>
      </header>

      <main className="flex flex-1 flex-col overflow-hidden lg:flex-row">
        {/* Left Panel: Input */}
        <div className="z-10 flex w-full flex-col border-r border-white/10 bg-[#0c0c0c] p-6 lg:w-1/3">
          <div className="mb-8">
            <h2 className="mb-2 text-xl font-bold">Create New Workforce</h2>
            <div className="mb-4 flex inline-flex gap-2 rounded-lg bg-white/5 p-1">
              <button
                onClick={() => {
                  setMode('superagent');
                  setGraphConfig(null);
                  setAgentConfig(null);
                }}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-bold transition-all ${mode === 'superagent' ? 'bg-primary text-black' : 'hover:bg-white/10'}`}
              >
                <Network size={16} /> Superagent Team
              </button>
              <button
                onClick={() => {
                  setMode('standalone');
                  setGraphConfig(null);
                  setAgentConfig(null);
                }}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-bold transition-all ${mode === 'standalone' ? 'bg-primary text-black' : 'hover:bg-white/10'}`}
              >
                <User size={16} /> Standalone Agent
              </button>
            </div>
            <p className="text-muted-foreground text-sm">
              {mode === 'superagent'
                ? 'Our Architect AI will design a team of specialized agents based on your requirements.'
                : 'Create a single specialized agent with specific tools and goals.'}
            </p>
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              mode === 'superagent'
                ? 'e.g. I need a team to monitor credit risk...'
                : 'e.g. A senior python developer who writes clean code...'
            }
            className="focus:border-primary mb-4 h-40 w-full resize-none rounded-lg border border-white/10 bg-white/5 p-4 text-white placeholder:text-white/20 focus:outline-none"
          />

          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="bg-primary text-primary-foreground hover:bg-primary/90 flex w-full items-center justify-center gap-2 rounded-lg py-3 font-bold transition-all disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/50 border-t-white"></div>
                {mode === 'superagent' ? 'Architecting...' : 'Generating...'}
              </>
            ) : (
              <>
                <Sparkles size={18} />
                {mode === 'superagent' ? 'Generate Architecture' : 'Generate Agent'}
              </>
            )}
          </button>

          {/* Guide Info */}
          <div className="text-muted-foreground mt-auto pt-8 text-xs">
            <p className="mb-2 font-bold tracking-wider text-white/20 uppercase">Tips</p>
            <ul className="list-inside list-disc space-y-1">
              <li>Be specific about the roles (e.g. &quot;Senior Analyst&quot;).</li>
              <li>Mention the input data sources if known.</li>
              <li>Describe the desired output format.</li>
            </ul>
          </div>
        </div>

        {/* Right Panel: Visualization */}
        <div className="relative flex-1 bg-[#151515]">
          {graphConfig || agentConfig ? (
            <div className="flex h-full flex-col">
              {/* Toolbar */}
              <div className="flex h-14 items-center justify-between border-b border-white/10 bg-white/5 px-6">
                <div>
                  <span className="text-muted-foreground block text-xs font-bold tracking-wider uppercase">
                    Generated Blueprint
                  </span>
                  <span className="font-bold">
                    {graphConfig?.name || agentConfig?.display_name}
                  </span>
                </div>
                <button
                  onClick={handleDeploy}
                  className="flex items-center gap-2 rounded-md bg-green-600 px-4 py-1.5 text-sm font-bold text-white hover:bg-green-500"
                >
                  <Check size={16} />
                  Deploy System
                </button>
              </div>
              {/* Visualizer */}
              <div className="flex-1 overflow-auto p-4">
                {graphConfig && <ArchitectureVisualizer config={graphConfig} />}
                {agentConfig && (
                  <div className="mx-auto mt-10 max-w-xl rounded-xl border border-white/10 bg-white/5 p-6">
                    <h3 className="mb-4 text-xl font-bold">{agentConfig.display_name}</h3>
                    <div className="space-y-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Role:</span>{' '}
                        <span className="ml-2 text-white">{agentConfig.agent.role}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Goal:</span>{' '}
                        <span className="ml-2 text-white">{agentConfig.agent.goal}</span>
                      </div>
                      <div className="text-muted-foreground rounded border border-white/5 bg-black/20 p-3 font-mono text-xs whitespace-pre-wrap">
                        {agentConfig.agent.backstory}
                      </div>
                      <div className="mt-4">
                        <span className="text-muted-foreground">Task:</span>
                        <p className="mt-1 text-white">{agentConfig.task.description}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              {/* Description Footer */}
              <div className="text-muted-foreground border-t border-white/10 bg-white/5 p-4 text-sm">
                {graphConfig?.description || agentConfig?.description}
              </div>
            </div>
          ) : (
            <div className="text-muted-foreground flex h-full flex-col items-center justify-center p-8">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white/5">
                <Sparkles size={32} className="text-white/10" />
              </div>
              <p>Ready to design your architecture.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
