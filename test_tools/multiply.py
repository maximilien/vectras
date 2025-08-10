def multiply(a, b):
    """Multiply a by b. This function has a bug - multiplies by 0 instead of b."""
    # BUG: Should multiply by b, but multiplies by 0
    result = a * 0  # BUG: Should be a * b
    print(f"Result of {a} * {b} = {result}")
    return result

# Test the buggy function
if __name__ == "__main__":
    try:
        result = multiply(5, 3)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")
