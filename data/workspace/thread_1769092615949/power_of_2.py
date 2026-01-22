def power_of_two(n: int) -> int:
    """Calculate 2 raised to the power of n using bit shifting for efficiency.

    Args:
        n (int): The exponent.

    Returns:
        int: 2^n.

    Raises:
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("Exponent must be non-negative.")
    return 1 << n


def generate_powers_of_two(count: int) -> list[int]:
    """Generate a list of the first `count` powers of 2.

    Args:
        count (int): Number of powers to generate.

    Returns:
        list[int]: List of 2^0, 2^1, ..., 2^(count-1).
    """
    if count < 0:
        raise ValueError("Count must be non-negative.")
    return [1 << i for i in range(count)]

# Example usage
if __name__ == "__main__":
    print("First 10 powers of 2:")
    for i, power in enumerate(generate_powers_of_two(10)):
        print(f"2^{i} = {power}")