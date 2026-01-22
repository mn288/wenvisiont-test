import asyncio

def power_of_two(n: int) -> int:
    """Calculate 2 raised to the power of n synchronously."""
    return 2 ** n

async def async_power_of_two(n: int) -> int:
    """Calculate 2 raised to the power of n asynchronously using asyncio.

    Args:
        n (int): The exponent.

    Returns:
        int: The result of 2^n.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("Exponent must be non-negative.")

    # Simulate async work with a delay
    await asyncio.sleep(0.001)
    return power_of_two(n)

# Example usage and testing
if __name__ == "__main__":
    async def main():
        result = await async_power_of_two(10)
        print(f"2^10 = {result}")

    asyncio.run(main())