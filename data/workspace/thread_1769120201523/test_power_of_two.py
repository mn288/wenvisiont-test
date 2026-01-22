import pytest
import asyncio
from power_of_two import async_power_of_two, power_of_two

def test_power_of_two_sync():
    """Test the synchronous power_of_two function."""
    assert power_of_two(0) == 1
    assert power_of_two(1) == 2
    assert power_of_two(2) == 4
    assert power_of_two(10) == 1024
    assert power_of_two(15) == 32768

def test_power_of_two_sync_negative():
    """Test the synchronous function with negative input."""
    with pytest.raises(TypeError):
        power_of_two(-1)

async def test_async_power_of_two():
    """Test the async_power_of_two function."""
    result = await async_power_of_two(5)
    assert result == 32

async def test_async_power_of_two_large():
    """Test the async function with a large exponent."""
    result = await async_power_of_two(20)
    assert result == 1048576

async def test_async_power_of_two_zero():
    """Test the async function with zero."""
    result = await async_power_of_two(0)
    assert result == 1

async def test_async_power_of_two_negative():
    """Test the async function with negative input."""
    with pytest.raises(TypeError):
        await async_power_of_two(-1)

# Run tests
if __name__ == "__main__":
    asyncio.run(test_async_power_of_two())