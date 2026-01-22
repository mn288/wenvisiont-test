import pytest
import asyncio
from power_of_two import power_of_two

@pytest.mark.asyncio
async def test_power_of_two_positive():
    """Test that power_of_two returns correct results for positive exponents."""
    result = await power_of_two(0)
    assert result == 1

    result = await power_of_two(1)
    assert result == 2

    result = await power_of_two(5)
    assert result == 32

    result = await power_of_two(10)
    assert result == 1024

@pytest.mark.asyncio
async def test_power_of_two_negative():
    """Test that power_of_two raises ValueError for negative exponents."""
    with pytest.raises(ValueError, match="Exponent must be non-negative"):
        await power_of_two(-1)

@pytest.mark.asyncio
async def test_power_of_two_large():
    """Test that power_of_two works correctly with a large exponent."""
    result = await power_of_two(20)
    assert result == 1048576

@pytest.mark.asyncio
async def test_power_of_two_zero():
    """Test that power_of_two correctly handles exponent 0."""
    result = await power_of_two(0)
    assert result == 1

# Optional: Test that the function is truly async
@pytest.mark.asyncio
async def test_power_of_two_async_behavior():
    """Test that the function behaves asynchronously by using asyncio.sleep."""
    # This test ensures the async sleep is actually being used
    # and the function is not blocking
    start_time = asyncio.get_event_loop().time()
    result = await power_of_two(5)
    end_time = asyncio.get_event_loop().time()
    
    # Ensure the function took at least some time (due to asyncio.sleep)
    assert end_time - start_time > 0.0005  # Slight buffer for timing
    assert result == 32