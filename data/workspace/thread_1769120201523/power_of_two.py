import asyncio

def power_of_two(n: int) -> int:
    """Calculate 2 raised to the power of n synchronously."""
    return 2 ** n

async def async_power_of_two(n: int) -> int:
    """Calculate 2 raised to the power of n asynchronously using asyncio.sleep for demonstration."""
    await asyncio.sleep(0.001)  # Simulate async work
    return power_of_two(n)

# Example usage
if __name__ == "__main__":
    async def main():
        result = await async_power_of_two(10)
        print(f"2^10 = {result}")
    
    asyncio.run(main())