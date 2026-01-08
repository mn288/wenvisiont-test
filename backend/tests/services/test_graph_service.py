from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expects import be_none, equal, expect

from services.graph_service import GraphService


@pytest.fixture
def mock_dependencies():
    with (
        patch("services.graph_service.build_workflow") as MockBuild,
        patch("services.graph_service.AsyncPostgresSaver") as MockSaver,
        patch("services.graph_service.pool") as MockPool,
    ):
        # Mock Workflow
        mock_workflow = MagicMock()
        mock_compiled = MagicMock()
        mock_workflow.compile.return_value = mock_compiled
        MockBuild.return_value = mock_workflow

        # Mock Saver
        mock_saver_instance = AsyncMock()
        MockSaver.return_value = mock_saver_instance

        yield MockBuild, MockSaver, MockPool, mock_workflow, mock_saver_instance


@pytest.mark.asyncio
async def test_singleton_pattern():
    # Reset singleton
    GraphService._instance = None

    s1 = GraphService.get_instance()
    s2 = GraphService.get_instance()

    expect(s1).to(equal(s2))
    expect(s1).not_to(be_none)


@pytest.mark.asyncio
async def test_reload_graph_success(mock_dependencies):
    MockBuild, MockSaver, MockPool, mock_workflow, mock_saver_instance = mock_dependencies

    # Reset singleton to ensure clean state
    GraphService._instance = None
    service = GraphService.get_instance()

    # Should be None initially
    expect(service.compiled_graph).to(be_none)

    graph = await service.reload_graph()

    expect(graph).not_to(be_none)
    expect(service.compiled_graph).not_to(be_none)

    # Verify interactions
    expect(MockBuild.called).to(equal(True))
    expect(MockSaver.called).to(equal(True))
    expect(mock_saver_instance.setup.called).to(equal(True))
    expect(mock_workflow.compile.called).to(equal(True))


@pytest.mark.asyncio
async def test_get_graph_lazy_load(mock_dependencies):
    MockBuild, MockSaver, MockPool, mock_workflow, mock_saver_instance = mock_dependencies

    GraphService._instance = None
    service = GraphService.get_instance()

    # First call triggers reload
    graph1 = await service.get_graph()
    expect(MockBuild.call_count).to(equal(1))

    # Second call should return cached
    graph2 = await service.get_graph()
    expect(MockBuild.call_count).to(equal(1))
    expect(graph1).to(equal(graph2))
