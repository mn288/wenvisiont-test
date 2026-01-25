from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.agents import NodeConfig


class GraphNode(BaseModel):
    id: str = Field(..., description="Unique ID for this node instance in the graph")
    type: str = Field(..., description="The type of agent/node from the registry (e.g. 'researcher', 'writer')")
    config: Optional[Dict[str, Any]] = Field(default={}, description="Specific configuration overrides if allowed")


class GraphEdge(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Condition logic if applicable")


class GraphConfig(BaseModel):
    name: str = Field(..., description="Name of the Superagent")
    description: str = Field(..., description="Description of what this Superagent does")
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    definitions: List[NodeConfig] = Field(default_factory=list, description="Definitions of any new agents created by the architect")


class ArchitectRequest(BaseModel):
    prompt: str = Field(..., description="User prompt describing the desired workflow")
