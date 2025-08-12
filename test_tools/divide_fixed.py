def divide(n1, n2):
    """Divide n1 by n2. Fixed version - now correctly divides by n2."""
    # FIXED: Now correctly uses n2 instead of 0
    if n2 == 0:
        raise ValueError("Cannot divide by zero")
    result = n1 / n2
    print(f"Result of {n1} / {n2} = {result}")
    return result

# Test the fixed function
if __name__ == "__main__":
    try:
        result = divide(355, 113)
        print(f"Final result: {result}")
        print(f"Approximation of pi: {result}")
    except Exception as e:
        print(f"Error: {e}")