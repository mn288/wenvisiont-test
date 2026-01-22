import pytest
import asyncio
from power_of_two import power_of_two


def test_power_of_two_sync():
    """Test the function with synchronous calls to verify correctness."""
    assert power_of_two(0) == 1
    assert power_of_two(1) == 2
    assert power_of_two(2) == 4
    assert power_of_two(10) == 1024


def test_power_of_two_async():
    """Test the function with async calls to verify async behavior."""
    async def run_test():
        result = await power_of_two(5)
        assert result == 32
        
        result = await power_of_two(0)
        assert result == 1
        
        result = await power_of_two(1)
        assert result == 2
    
    asyncio.run(run_test())


def test_power_of_two_negative():
    """Test that negative input raises ValueError."""
    with pytest.raises(ValueError):
        asyncio.run(power_of_two(-1))


def test_power_of_two_large():
    """Test with a larger exponent to ensure performance and correctness."""
    async def run_test():
        result = await power_of_two(20)
        assert result == 1048576
    
    asyncio.run(run_test())


def test_power_of_two_zero():
    """Test that 2^0 = 1."""
    async def run_test():
        result = await power_of_two(0)
        assert result == 1
    
    asyncio.run(run_test())