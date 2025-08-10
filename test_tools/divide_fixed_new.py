def divide(n1, n2):
    """Divide n1 by n2. Fixed version - now correctly divides instead of adding."""
    # FIXED: Now correctly divides instead of adding
    if n2 == 0:
        raise ValueError("Cannot divide by zero")
    result = n1 / n2  # FIXED: Changed from n1 + n2 to n1 / n2
    print(f"Result of {n1} / {n2} = {result}")
    return result

# Test the fixed function
if __name__ == "__main__":
    try:
        result = divide(10, 2)
        print(f"Final result: {result}")
        print(f"Should be 5.0, got: {result}")
    except Exception as e:
        print(f"Error: {e}")
