import pytest

from brain.graph import END, route_preprocess


@pytest.mark.asyncio
async def test_preprocess_rejection_routing():
    """Test that the graph stops if preprocessing fails."""

    # Case 1: Error present
    state_with_error = {"errors": ["Some error"]}
    result = route_preprocess(state_with_error)
    assert result == END

    # Case 2: No error
    state_ok = {"errors": []}
    result_ok = route_preprocess(state_ok)
    assert result_ok == "supervisor"
