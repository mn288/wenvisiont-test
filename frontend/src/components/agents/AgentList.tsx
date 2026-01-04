'use client';

import React, { useEffect, useState } from 'react';
import { listAgents, deleteAgent, AgentConfig } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Trash2, Edit, Plus } from 'lucide-react';

interface AgentListProps {
  onEdit: (name: string) => void;
  onCreate: () => void;
}

export default function AgentList({ onEdit, onCreate }: AgentListProps) {
  const [agents, setAgents] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAgents = async () => {
    try {
      const data = await listAgents();
      setAgents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleDelete = async (name: string) => {
    if (confirm(`Are you sure you want to delete ${name}?`)) {
      await deleteAgent(name);
      fetchAgents();
    }
  };

  if (loading) return <div className="text-white">Loading agents...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Agents</h2>
        <Button onClick={onCreate} className="bg-purple-600 hover:bg-purple-700">
          <Plus className="mr-2 h-4 w-4" /> New Agent
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <Card key={agent.name} className="border-gray-700 bg-gray-800 text-white">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{agent.name}</CardTitle>
              <div className="flex space-x-2">
                <Button variant="ghost" size="icon" onClick={() => onEdit(agent.name)}>
                  <Edit className="h-4 w-4 text-blue-400" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(agent.name)}>
                  <Trash2 className="h-4 w-4 text-red-400" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="truncate text-2xl font-bold">{agent.agent.role}</div>
              <p className="mt-2 line-clamp-3 text-xs text-gray-400">{agent.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
