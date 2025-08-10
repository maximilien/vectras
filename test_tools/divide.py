def divide(n1, n2):
    """Divide n1 by n2. This function has a bug - it divides by 0 instead of n2."""
    # BUG: This should be n2, not 0
    result = n1 / 0
    print(f"Result of {n1} / {n2} = {result}")
    return result

# Test the function
if __name__ == "__main__":
    try:
        result = divide(355, 113)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")