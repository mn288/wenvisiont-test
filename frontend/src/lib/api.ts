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
  metadata?: any;
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
    console.warn("Failed to fetch topology, falling back to logs only.");
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
  input?: any;
  output?: any;
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
  };
  task: {
    description: string;
    expected_output: string;
    async_execution: boolean;
  };
}

export async function listAgents(): Promise<AgentConfig[]> {
  const res = await fetch('http://localhost:8000/agents/');
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
  value: any;
}

export async function getConfiguration(key: string): Promise<ConfigurationItem | null> {
  const res = await fetch(`http://localhost:8000/configurations/${key}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to get configuration');
  return res.json();
}

export async function saveConfiguration(key: string, value: any): Promise<ConfigurationItem> {
  const res = await fetch('http://localhost:8000/configurations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  });
  if (!res.ok) throw new Error('Failed to save configuration');
  return res.json();
}
