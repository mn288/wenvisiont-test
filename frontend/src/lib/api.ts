export interface StepLog {
  id: number;
  thread_id: string;
  step_name: string;
  log_type: string;
  content: string;
  created_at: string;
  checkpoint_id?: string | null;
  parent_checkpoint_id?: string | null;
}

export const TENANT_ID = 'bank-a'; // Default tenant for development

export interface ForkResponse {
  status: string;
  message: string;
  thread_id?: string;
}

export async function forkConversation(
  threadId: string,
  checkpointId: string,
  newInput?: string,
  resetToStep?: string
): Promise<ForkResponse> {
  const res = await fetch(
    `http://localhost:8000/fork?thread_id=${threadId}&checkpoint_id=${checkpointId}${newInput ? `&new_input=${encodeURIComponent(newInput)}` : ''}${resetToStep ? `&reset_to_step=${resetToStep}` : ''}`,
    {
      method: 'POST',
    }
  );
  return res.json();
}

export interface Conversation {
  id: number;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export async function fetchStepHistory(threadId: string): Promise<StepLog[]> {
  const response = await fetch(`http://localhost:8000/history/${threadId}/steps`, {
    cache: 'no-store',
    headers: {
      Pragma: 'no-cache',
      'Cache-Control': 'no-cache',
    },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch step history');
  }
  return response.json();
}

export interface TopologyNode {
  id: string; // checkpoint_id
  parent_id?: string | null;
  node: string;
  parallel_nodes?: string[];
  created_at: string;
  metadata?: Record<string, unknown>;
}

export async function fetchTopology(threadId: string): Promise<TopologyNode[]> {
  const response = await fetch(`http://localhost:8000/history/${threadId}/topology`, {
    cache: 'no-store',
    headers: {
      Pragma: 'no-cache',
      'Cache-Control': 'no-cache',
    },
  });
  if (!response.ok) {
    console.warn('Failed to fetch topology, falling back to logs only.');
    return [];
  }
  return response.json();
}

export async function fetchConversations(): Promise<Conversation[]> {
  const response = await fetch('http://localhost:8000/history/conversations', {
    cache: 'no-store',
    headers: {
      Pragma: 'no-cache',
      'Cache-Control': 'no-cache',
    },
  });
  if (!response.ok) {
    throw new Error('Failed to fetch conversations');
  }
  return response.json();
}

export async function deleteConversation(threadId: string): Promise<void> {
  const response = await fetch(`http://localhost:8000/history/${threadId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete conversation');
  }
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'system' | 'node-start' | 'node-end' | 'error' | 'info' | 'thought' | 'tool';
  message: string;
  node?: string; // Optional context about which node generated this
  input?: unknown;
  output?: unknown;
}
export interface AgentConfig {
  name: string;
  display_name: string;
  description: string;
  output_state_key: string;
  agent: {
    role: string;
    goal: string;
    backstory: string;
    verbose: boolean;
    allow_delegation: boolean;
    tools: string[];
    mcp_servers: string[];
    files_access: boolean;
    s3_access: boolean;
    // DyLAN scoring fields
    importance_score?: number;
    success_rate?: number;
    task_domains?: string[];
    use_reflection?: boolean;
  };
  task: {
    description: string;
    expected_output: string;
    async_execution: boolean;
  };
}

export async function listAgents(): Promise<AgentConfig[]> {
  const res = await fetch('http://localhost:8000/agents/', {
    headers: { 'X-Tenant-ID': TENANT_ID },
  });
  if (!res.ok) throw new Error('Failed to list agents');
  return res.json();
}

export async function getAgent(name: string): Promise<AgentConfig> {
  const res = await fetch(`http://localhost:8000/agents/${name}`);
  if (!res.ok) throw new Error('Failed to get agent');
  return res.json();
}

export async function saveAgent(agent: AgentConfig): Promise<AgentConfig> {
  const res = await fetch('http://localhost:8000/agents/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(agent),
  });
  if (!res.ok) throw new Error('Failed to save agent');
  return res.json();
}

export async function deleteAgent(name: string): Promise<{ status: string }> {
  const res = await fetch(`http://localhost:8000/agents/${name}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete agent');
  return res.json();
}

export async function generateAgent(
  prompt: string,
  filesAccess: boolean,
  s3Access: boolean,
  mcpServers: string[]
): Promise<AgentConfig> {
  const res = await fetch('http://localhost:8000/agents/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      files_access: filesAccess,
      s3_access: s3Access,
      mcp_servers: mcpServers,
    }),
  });
  if (!res.ok) throw new Error('Failed to generate agent');
  return res.json();
}

export async function listMCPServers(): Promise<string[]> {
  const res = await fetch('http://localhost:8000/agents/mcp/servers');
  if (!res.ok) return [];
  return res.json();
}

export interface S3Config {
  bucket_name: string;
  region_name: string;
  access_key_id?: string;
  secret_access_key?: string;
  endpoint_url?: string;
}

export interface InfrastructureConfig {
  s3?: S3Config;
  local_workspace_path?: string;
  allowed_mcp_servers?: string[];
}

export interface FileItem {
  path: string;
  name: string;
  type: string;
}

export async function getInfrastructureConfig(): Promise<InfrastructureConfig> {
  const res = await fetch('http://localhost:8000/infrastructure/config');
  if (!res.ok) throw new Error('Failed to get config');
  return res.json();
}

/**
 * Fetch allowed MCP servers for the current tenant.
 * Returns empty array if no restrictions (all servers allowed).
 */
export async function getTenantAllowedMCPServers(): Promise<string[]> {
  try {
    const config = await getConfiguration('infrastructure_config');
    if (config?.value && typeof config.value === 'object') {
      const val = config.value as { allowed_mcp_servers?: string[] };
      return val.allowed_mcp_servers || [];
    }
  } catch (e) {
    console.warn('Failed to fetch tenant MCP config:', e);
  }
  return [];
}

export async function updateInfrastructureConfig(config: InfrastructureConfig): Promise<void> {
  const res = await fetch('http://localhost:8000/infrastructure/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to update config');
}

export async function verifyS3Connection(config: S3Config): Promise<void> {
  const res = await fetch('http://localhost:8000/infrastructure/verify-s3', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Connection failed');
}

// Configuration API
export interface ConfigurationItem {
  key: string;
  value: unknown;
}

export async function getConfiguration(key: string): Promise<ConfigurationItem | null> {
  const res = await fetch(`http://localhost:8000/configurations/${key}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to get configuration');
  return res.json();
}

export async function saveConfiguration(key: string, value: unknown): Promise<ConfigurationItem> {
  const res = await fetch('http://localhost:8000/configurations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  });
  if (!res.ok) throw new Error('Failed to save configuration');
  return res.json();
}

export interface GraphNode {
  id: string;
  type: string;
  config: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  condition?: string;
}

export interface GraphConfig {
  name: string;
  description: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export async function architectAgent(prompt: string): Promise<GraphConfig> {
  const res = await fetch('http://localhost:8000/architect/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': TENANT_ID,
    },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to architect agent' }));
    throw new Error(error.detail || 'Failed to architect agent');
  }
  return res.json();
}

export async function listWorkflows(): Promise<GraphConfig[]> {
  const res = await fetch('http://localhost:8000/workflows/');
  if (!res.ok) throw new Error('Failed to list workflows');
  return res.json();
}

export async function saveWorkflow(config: GraphConfig): Promise<GraphConfig> {
  const res = await fetch('http://localhost:8000/workflows/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to save workflow');
  return res.json();
}

export async function deleteWorkflow(name: string): Promise<{ message: string }> {
  try {
    const res = await fetch(`http://localhost:8000/workflows/${name}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete workflow');
    return res.json();
  } catch (error) {
    console.error('Error deleting workflow:', error);
    throw error;
  }
}

export interface SystemStats {
  total_invocations: number;
  active_agents: number;
  compliance_score: number;
  system_health: string;
}

export async function getStats(): Promise<SystemStats> {
  const res = await fetch('http://localhost:8000/stats/');
  return res.json();
}

export async function abortJob(threadId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`http://localhost:8000/abort/${threadId}`, {
    method: 'POST',
  });
  if (!res.ok) {
    return { status: 'error', message: 'Failed to abort job' };
  }
  return res.json();
}
