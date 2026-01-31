from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brain.nodes.tools import tool_execution_node
from models.state import Citation


@pytest.mark.asyncio
async def test_citation_bubbling():
    # 1. Setup Mock Tool with Structured Output
    mock_tool = MagicMock()
    mock_tool.name = "mock_retriever"
    # Mocking ainvoke to return a dict with citations
    mock_tool.ainvoke = AsyncMock(
        return_value={
            "content": "Found some info.",
            "citations": [
                {
                    "source_id": "doc1",
                    "uri": "http://example.com/1",
                    "title": "Example Doc 1",
                    "snippet": "This is a snippet.",
                    "score": 0.9,
                }
            ],
        }
    )

    # Mock tool_service to return our mock tool
    with (
        patch("brain.nodes.tools.tool_service") as mock_service,
        patch("brain.nodes.tools.LogHandler") as mock_logger_cls,
    ):
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger
        mock_service.get_tool = AsyncMock(return_value=mock_tool)

        # 2. Setup Input State
        state = {"tool_call": {"name": "mock_retriever", "args": {"query": "test"}}}

        config = {"configurable": {"thread_id": "test_thread"}}

        # 3. Execute Node
        result = await tool_execution_node(state, config)

        # 4. Assertions
        assert "results" in result
        assert len(result["results"]) == 1

        agent_result = result["results"][0]
        # Check AgentResult has citations
        assert "citations" in agent_result
        assert len(agent_result["citations"]) == 1
        assert agent_result["citations"][0]["uri"] == "http://example.com/1"

        # Check Graph Update has citations list
        assert "citations" in result
        assert len(result["citations"]) == 1
        # Result contains Citation objects
        assert isinstance(result["citations"][0], Citation)
        assert result["citations"][0].uri == "http://example.com/1"


@pytest.mark.asyncio
async def test_citation_json_string_parsing():
    # 1. Setup Mock Tool with JSON String Output
    mock_tool = MagicMock()
    mock_tool.name = "mock_json_tool"

    json_output = """
    {
        "content": "Json content",
        "citations": [
            {
                "source_id": "doc2",
                "uri": "http://example.com/2", 
                "title": "Json Doc"
            }
        ]
    }
    """
    mock_tool.ainvoke = AsyncMock(return_value=json_output)

    with (
        patch("brain.nodes.tools.tool_service") as mock_service,
        patch("brain.nodes.tools.LogHandler") as mock_logger_cls,
    ):
        mock_logger = AsyncMock()
        mock_logger_cls.return_value = mock_logger
        mock_service.get_tool = AsyncMock(return_value=mock_tool)

        state = {"tool_call": {"name": "mock_json_tool", "args": {}}}
        config = {"configurable": {"thread_id": "test_thread"}}

        result = await tool_execution_node(state, config)

        agent_result = result["results"][0]
        assert len(agent_result["citations"]) == 1
        assert agent_result["citations"][0]["uri"] == "http://example.com/2"
