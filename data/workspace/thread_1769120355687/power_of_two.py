import asyncio

async def power_of_two(n: int) -> int:
    """
    Asynchronously computes 2 raised to the power of n.

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
    
    return 2 ** n

# Example usage and test
if __name__ == "__main__":
    async def main():
        result = await power_of_two(10)
        print(f"2^10 = {result}")
    
    asyncio.run(main())