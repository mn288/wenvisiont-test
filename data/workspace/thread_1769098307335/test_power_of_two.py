import pytest
import asyncio
from power_of_two import async_power_of_two

def test_power_of_two_sync():
    """Test the synchronous power_of_two function."""
    assert power_of_two(0) == 1
    assert power_of_two(1) == 2
    assert power_of_two(5) == 32
    assert power_of_two(10) == 1024

def test_power_of_two_sync_negative():
    """Test that negative exponents raise ValueError in sync function."""
    with pytest.raises(ValueError):
        power_of_two(-1)

@pytest.mark.asyncio
async def test_async_power_of_two():
    """Test the async_power_of_two function with valid inputs."""
    result = await async_power_of_two(0)
    assert result == 1

    result = await async_power_of_two(1)
    assert result == 2

    result = await async_power_of_two(5)
    assert result == 32

    result = await async_power_of_two(10)
    assert result == 1024

@pytest.mark.asyncio
async def test_async_power_of_two_negative():
    """Test that async_power_of_two raises ValueError for negative exponents."""
    with pytest.raises(ValueError):
        await async_power_of_two(-1)

@pytest.mark.asyncio
async def test_async_power_of_two_large():
    """Test async_power_of_two with a large exponent to ensure performance."""
    result = await async_power_of_two(20)
    assert result == 1048576

@pytest.mark.asyncio
async def test_async_power_of_two_zero():
    """Test async_power_of_two with zero exponent."""
    result = await async_power_of_two(0)
    assert result == 1

# Optional: Test that the function is truly async and can be awaited
@pytest.mark.asyncio
async def test_async_function_can_be_awaited():
    """Verify that the async function can be awaited and returns a coroutine."""
    coro = async_power_of_two(3)
    assert isinstance(coro, asyncio.coroutine)
    result = await coro
    assert result == 8