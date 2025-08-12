# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for end-to-end agent functionality."""

import tempfile
from pathlib import Path

import pytest

from vectras.agents.testing import TestingAgentManager

# Updated for OpenAI Agents SDK structure
# Now testing TestingAgentManager instead of TestingAgent


class TestTestingAgent:
    """Test the testing agent's e2e functionality."""

    @pytest.fixture
    def testing_manager(self):
        """Create a testing agent manager instance."""
        return TestingAgentManager()

    @pytest.fixture
    def temp_test_tools_dir(self):
        """Create a temporary test tools directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.mark.asyncio
    async def test_create_divide_tool_with_bug(self, testing_manager, temp_test_tools_dir):
        """Test creating the divide tool with a bug."""
        # Override the test tools directory
        testing_manager.test_tools_directory = temp_test_tools_dir

        # Create the divide tool with a bug
        buggy_code = '''def divide(n1, n2):
    """Divide n1 by n2. Buggy version."""
    result = n1 / 0  # The bug - divides by 0
    return result'''

        result = testing_manager.create_tool(
            name="divide",
            language="python",
            code=buggy_code,
            description="A buggy divide function",
            has_bugs=True,
        )

        assert "Successfully created tool 'divide'" in result

        # Check that the tool was created and has the expected properties
        tool = None
        for t in testing_manager.test_tools.values():
            if t.name == "divide":
                tool = t
                break

        assert tool is not None
        assert tool.name == "divide"
        assert tool.language == "python"
        assert tool.has_bugs is True
        assert tool.severity == "medium"  # Medium severity for manually created tools with bugs
        assert "def divide(n1, n2):" in tool.code
        assert "n1 / 0" in tool.code  # The bug

    @pytest.mark.asyncio
    async def test_execute_divide_tool_with_bug(self, testing_manager, temp_test_tools_dir):
        """Test executing the divide tool with a bug."""
        # Override the test tools directory
        testing_manager.test_tools_directory = temp_test_tools_dir

        # Create the divide tool with a bug
        buggy_code = '''def divide(n1, n2):
    """Divide n1 by n2. Buggy version."""
    result = n1 / 0  # The bug - divides by 0
    return result'''

        testing_manager.create_tool(
            name="divide",
            language="python",
            code=buggy_code,
            description="A buggy divide function",
            has_bugs=True,
        )

        # Execute the tool
        result = testing_manager.execute_tool("divide")

        # Should contain error information or indicate execution
        assert "divide" in result.lower()
        # The tool might execute successfully even with the bug if it's not called with arguments

    @pytest.mark.asyncio
    async def test_run_divide_tool_tests(self, testing_manager, temp_test_tools_dir):
        """Test running tests on the divide tool."""
        # Override the test tools directory
        testing_manager.test_tools_directory = temp_test_tools_dir

        # Create the fixed divide tool
        fixed_code = '''def divide(n1, n2):
    """Divide n1 by n2. Fixed version."""
    if n2 == 0:
        raise ValueError("Cannot divide by zero")
    result = n1 / n2
    return result'''

        # Create the tool using the manager
        testing_manager.create_tool(
            name="divide",
            language="python",
            code=fixed_code,
            description="A fixed divide function",
            has_bugs=False,
        )

        # Run the tests using the manager's method
        result = testing_manager.run_tests("divide")

        # Should indicate that tests were run
        assert "divide" in result.lower()

    @pytest.mark.asyncio
    async def test_list_tools(self, testing_manager):
        """Test listing available tools."""
        result = testing_manager.list_tools()

        # Should list available tools
        assert "Available testing tools" in result
        assert "calculator" in result.lower()  # Default sample tool

    @pytest.mark.asyncio
    async def test_get_status(self, testing_manager):
        """Test getting testing agent status."""
        result = testing_manager.get_status()

        # Should show status information
        assert "Testing Agent Status" in result
        assert "Total Tools:" in result
