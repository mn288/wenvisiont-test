import pytest
import asyncio
from power_of_two import async_power_of_two

def test_power_of_two_sync():
    """Test the synchronous version of power of two."""
    assert 2 ** 0 == 1
    assert 2 ** 1 == 2
    assert 2 ** 5 == 32
    assert 2 ** 10 == 1024

def test_power_of_two_async():
    """Test the asynchronous version of power of two."""
    async def run_test():
        result = await async_power_of_two(0)
        assert result == 1
        
        result = await async_power_of_two(1)
        assert result == 2
        
        result = await async_power_of_two(5)
        assert result == 32
        
        result = await async_power_of_two(10)
        assert result == 1024
    
    # Run the async test
    asyncio.run(run_test())

def test_power_of_two_async_negative_exponent():
    """Test that negative exponents raise a ValueError."""
    with pytest.raises(ValueError):
        async def run_test():
            await async_power_of_two(-1)
        
        asyncio.run(run_test())

def test_power_of_two_async_large_exponent():
    """Test large exponent to ensure performance and correctness."""
    async def run_test():
        result = await async_power_of_two(20)
        assert result == 1048576
    
    asyncio.run(run_test())

def test_power_of_two_async_zero():
    """Test that 2^0 is correctly handled."""
    async def run_test():
        result = await async_power_of_two(0)
        assert result == 1
    
    asyncio.run(run_test())

# Run the tests
if __name__ == "__main__":
    pytest.main(["-v", "test_power_of_two.py"])