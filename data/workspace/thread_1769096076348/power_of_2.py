def is_power_of_two(n: int) -> bool:
    """Check if a number is a power of two using bitwise operations.

    Args:
        n (int): The number to check.

    Returns:
        bool: True if n is a power of two, False otherwise.
    """
    return n > 0 and (n & (n - 1)) == 0


def power_of_two_generator(max_exponent: int):
    """Generate powers of two up to a given exponent.

    Args:
        max_exponent (int): The maximum exponent to generate.

    Yields:
        int: Powers of two from 2^0 to 2^max_exponent.
    """
    for i in range(max_exponent + 1):
        yield 2 ** i

# Example usage
if __name__ == "__main__":
    # Test is_power_of_two
    test_numbers = [1, 2, 3, 4, 16, 17, 32, 100]
    for num in test_numbers:
        print(f"{num} is a power of two: {is_power_of_two(num)}")

    # Generate powers of two
    print("\nPowers of two up to 2^8:")
    for power in power_of_two_generator(8):
        print(power)