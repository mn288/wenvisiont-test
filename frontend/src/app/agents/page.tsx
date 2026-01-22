'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import AgentList from '@/components/agents/AgentList';
import AgentEditor from '@/components/agents/AgentEditor';
import AgentGenerator from '@/components/agents/AgentGenerator';

import { ArrowLeft } from 'lucide-react';

export default function AgentsPage() {
  const router = useRouter();
  const [view, setView] = useState<'list' | 'edit' | 'create'>('list');
  const [editingAgent, setEditingAgent] = useState<string | undefined>(undefined);
  const [showGenerator, setShowGenerator] = useState(false);

  const handleEdit = (name: string) => {
    setEditingAgent(name);
    setView('edit');
  };

  const handleCreate = () => {
    setEditingAgent(undefined);
    setView('edit'); // Reuse editor for create
  };

  const handleCloseEditor = () => {
    setView('list');
    setEditingAgent(undefined);
  };

  const handleGeneratorSuccess = () => {
    // Refresh list is handled by AgentList re-mounting or we can lift state
    // Simplest: just go back to list, list component fetches on mount
    setView('list');
  };

  return (
    <div className="h-screen overflow-auto bg-gray-950 p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 p-4 backdrop-blur">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/')}
              className="rounded-full bg-gray-800 p-2 text-gray-400 transition hover:bg-gray-700 hover:text-white"
              title="Back to Dashboard"
            >
              <ArrowLeft size={20} />
            </button>
            <div>
              <h1 className="bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-3xl font-bold text-transparent">
                Agent Studio
              </h1>
              <p className="text-gray-400">Manage, Configure, and Generate AI Agents</p>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowGenerator(true)}
              className="rounded bg-gradient-to-r from-blue-600 to-cyan-600 px-4 py-2 font-medium text-white transition hover:from-blue-700 hover:to-cyan-700"
            >
              ✨ Generate Agent
            </button>
          </div>
        </div>

        {view === 'list' && <AgentList onEdit={handleEdit} onCreate={handleCreate} />}

        {view === 'edit' && (
          <AgentEditor name={editingAgent} onClose={handleCloseEditor} onSave={handleCloseEditor} />
        )}

        <AgentGenerator
          open={showGenerator}
          onClose={() => setShowGenerator(false)}
          onGenerate={handleGeneratorSuccess}
        />
      </div>
    </div>
  );
}
