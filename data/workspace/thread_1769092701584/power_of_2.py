def is_power_of_two(n: int) -> bool:
    """Check if a number is a power of two using bitwise operations.

    Args:
        n (int): The number to check.

    Returns:
        bool: True if n is a power of two, False otherwise.
    """
    return n > 0 and (n & (n - 1)) == 0


def next_power_of_two(n: int) -> int:
    """Find the smallest power of two greater than or equal to n.

    Args:
        n (int): The number to find the next power of two for.

    Returns:
        int: The smallest power of two >= n.
    """
    if n <= 0:
        raise ValueError("Input must be a positive integer.")
    if n & (n - 1) == 0:
        return n
    return 1 << (n - 1).bit_length()

# Example usage
if __name__ == "__main__":
    print(is_power_of_two(8))      # True
    print(is_power_of_two(7))      # False
    print(next_power_of_two(5))    # 8
    print(next_power_of_two(16))   # 16