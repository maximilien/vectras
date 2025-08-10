# Generated test tool
# Created: 2025-08-09 18:35:54.304689
# Has bugs: True
# Bug description:
# Severity: medium


def multiply(a, b):
    # Bug: Incorrectly returns 1 when either a or b is zero
    if a == 0 or b == 0:
        return 1
    return a * b


# Example usage
if __name__ == "__main__":
    print(multiply(5, 3))  # Should return 15
    print(multiply(0, 5))  # Should return 0, but returns 1 due to the bug
    print(multiply(5, 0))  # Should return 0, but returns 1 due to the bug
    print(multiply(0, 0))  # Should return 0, but returns 1 due to the bug
