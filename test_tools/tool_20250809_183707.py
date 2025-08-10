# Generated test tool
# Created: 2025-08-09 18:37:07.297591
# Has bugs: True
# Bug description:
# Severity: high


def crash():
    # Intentional bug: Incorrectly formatted error message
    raise ValueError("This is a crash, but the message is missing important details")


# Uncomment the line below to execute the crash
# crash()
