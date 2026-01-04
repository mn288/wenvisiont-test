'use client';

import { motion } from 'framer-motion';
import { Activity, Database, FileText, Wrench } from 'lucide-react';
import clsx from 'clsx';

interface CrewMonitorProps {
  activeAgent: string | null; // "Researcher" | "Analyst" | null
  isCrewActive: boolean;
}

const agents = [
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

export function CrewMonitor({ activeAgent, isCrewActive }: CrewMonitorProps) {
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

      <div className="flex gap-6">
        {agents.map((agent) => {
          const isActive = activeAgent === agent.id;

          return (
            <div
              key={agent.id}
              className={clsx(
                'relative flex-1 overflow-hidden rounded-xl border-2 p-4 transition-all duration-300',
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
                <div className={clsx('rounded-full p-3', agent.color)}>
                  <agent.icon size={24} />
                </div>

                <div>
                  <h3 className="text-navy font-bold">{agent.name}</h3>
                  <p className="text-xs tracking-wider text-gray-500 uppercase">{agent.role}</p>
                </div>

                <div className="mt-2 h-6">
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
    </div>
  );
}
