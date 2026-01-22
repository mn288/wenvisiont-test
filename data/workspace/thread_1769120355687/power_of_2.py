def is_power_of_two(n):
    """Check if a number is a power of two."""
    if n <= 0:
        return False
    return (n & (n - 1)) == 0

# Example usage
if __name__ == "__main__":
    print(is_power_of_two(8))  # True
    print(is_power_of_two(7))  # False