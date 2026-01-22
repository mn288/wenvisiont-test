import pytest
import asyncio
from power_of_two import power_of_two


def test_power_of_two_sync():
    """Test the function with synchronous calls for known values."""
    assert power_of_two(0) == 1
    assert power_of_two(1) == 2
    assert power_of_two(2) == 4
    assert power_of_two(3) == 8
    assert power_of_two(10) == 1024


def test_power_of_two_async():
    """Test the function using async context."""
    async def run_test():
        result = await power_of_two(5)
        assert result == 32
    
    asyncio.run(run_test())


def test_power_of_two_negative():
    """Test that negative exponents raise ValueError."""
    with pytest.raises(ValueError, match="Exponent must be non-negative"):
        asyncio.run(power_of_two(-1))


def test_power_of_two_large():
    """Test with a large exponent to ensure performance and correctness."""
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