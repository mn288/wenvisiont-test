'use client';

import { motion } from 'framer-motion';
import { Activity, Database, FileText, Wrench, TrendingUp } from 'lucide-react';
import clsx from 'clsx';
import { useEffect, useState } from 'react';

interface AgentSummary {
  id: string;
  label: string;
  role: string;
  description: string;
  importance_score: number;
  success_rate: number;
  task_domains: string[];
}

interface CrewMonitorProps {
  activeAgent: string | null;
  isCrewActive: boolean;
}

// Fallback static agents (used if API fails)
const fallbackAgents = [
  {
    id: 'Researcher',
    name: 'Senior Researcher',
    role: 'Information Gathering',
    icon: Database,
    color: 'bg-blue-100 text-blue-600',
  },
  {
    id: 'Analyst',
    name: 'Tech Analyst',
    role: 'Synthesis & Reporting',
    icon: FileText,
    color: 'bg-purple-100 text-purple-600',
  },
  {
    id: 'MCP Tool Specialist',
    name: 'MCP Tool Specialist',
    role: 'Tool Execution',
    icon: Wrench,
    color: 'bg-amber-100 text-amber-600',
  },
];

const iconMap: Record<string, typeof Database> = {
  research: Database,
  analysis: FileText,
  code: Wrench,
  default: TrendingUp,
};

const colorMap: Record<string, string> = {
  research: 'bg-blue-100 text-blue-600',
  analysis: 'bg-purple-100 text-purple-600',
  code: 'bg-amber-100 text-amber-600',
  default: 'bg-teal-100 text-teal-600',
};

function getIconForDomains(domains: string[]) {
  for (const domain of domains) {
    if (iconMap[domain.toLowerCase()]) return iconMap[domain.toLowerCase()];
  }
  return iconMap.default;
}

function getColorForDomains(domains: string[]) {
  for (const domain of domains) {
    if (colorMap[domain.toLowerCase()]) return colorMap[domain.toLowerCase()];
  }
  return colorMap.default;
}

export function CrewMonitor({ activeAgent, isCrewActive }: CrewMonitorProps) {
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/agents/summary')
      .then((res) => res.json())
      .then((data) => {
        setAgents(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch agents:', err);
        setLoading(false);
      });
  }, []);

  // Use fallback if no dynamic agents
  const displayAgents =
    agents.length > 0
      ? agents
      : fallbackAgents.map((a) => ({
          id: a.id,
          label: a.name,
          role: a.role,
          description: '',
          importance_score: 0.5,
          success_rate: 1.0,
          task_domains: [],
        }));

  return (
    <div className="h-full rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-navy text-xl font-bold">CrewAI Agents</h2>
        {isCrewActive && (
          <span className="relative flex h-3 w-3">
            <span className="bg-secondary absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"></span>
            <span className="bg-secondary relative inline-flex h-3 w-3 rounded-full"></span>
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-sm text-gray-400">Loading agents...</div>
      ) : (
        <div className="flex flex-wrap gap-4">
          {displayAgents.map((agent) => {
            const isActive = activeAgent === agent.role || activeAgent === agent.id;
            const Icon = getIconForDomains(agent.task_domains || []);
            const colorClass = getColorForDomains(agent.task_domains || []);
            const score = (agent.importance_score * agent.success_rate * 100).toFixed(0);

            return (
              <div
                key={agent.id}
                className={clsx(
                  'relative max-w-[250px] min-w-[180px] flex-1 overflow-hidden rounded-xl border-2 p-4 transition-all duration-300',
                  isActive ? 'border-secondary bg-secondary/5' : 'border-gray-100 bg-gray-50'
                )}
              >
                {/* Background Activity Pulse */}
                {isActive && (
                  <motion.div
                    className="bg-secondary/5 absolute inset-0"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                  />
                )}

                <div className="relative z-10 flex flex-col items-center gap-3 text-center">
                  <div className={clsx('rounded-full p-3', colorClass)}>
                    <Icon size={24} />
                  </div>

                  <div>
                    <h3 className="text-navy text-sm font-bold">{agent.label}</h3>
                    <p className="text-xs tracking-wider text-gray-500 uppercase">{agent.role}</p>
                  </div>

                  {/* DyLAN Score Display */}
                  <div className="flex items-center gap-2 text-xs">
                    <div className="flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1">
                      <TrendingUp size={10} className="text-teal-500" />
                      <span className="font-medium text-gray-600">{score}%</span>
                    </div>
                    {agent.task_domains && agent.task_domains.length > 0 && (
                      <div className="max-w-[80px] truncate rounded-full bg-gray-100 px-2 py-1 text-gray-500">
                        {agent.task_domains[0]}
                      </div>
                    )}
                  </div>

                  <div className="mt-1 h-5">
                    {isActive ? (
                      <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-secondary flex items-center gap-2 text-xs font-bold"
                      >
                        <Activity size={12} className="animate-spin" />
                        WORKING
                      </motion.div>
                    ) : (
                      <span className="text-xs font-medium text-gray-400">IDLE</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
