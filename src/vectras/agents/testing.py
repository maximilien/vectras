"""Testing agent for Vectras - creates test tools and integration tests."""

import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .base_agent import BaseAgent


class TestingTool:
    """Represents a test tool that can be created by the testing agent."""

    __test__ = False

    def __init__(
        self,
        name: str,
        language: str,
        code: str,
        description: str,
        has_bugs: bool = False,
        bug_description: str = "",
        severity: str = "low",
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.language = language
        self.code = code
        self.description = description
        self.has_bugs = has_bugs
        self.bug_description = bug_description
        self.severity = severity
        self.created_at = datetime.now()
        self.executed_count = 0
        self.last_error = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "code": self.code,
            "description": self.description,
            "has_bugs": self.has_bugs,
            "bug_description": self.bug_description,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
            "executed_count": self.executed_count,
            "last_error": self.last_error,
        }


class TestingAgent(BaseAgent):
    """Testing agent that creates test tools and integration tests."""

    __test__ = False

    def __init__(self):
        super().__init__("testing")

        # Testing-specific attributes
        self.test_tools: Dict[str, TestingTool] = {}
        self.test_tools_directory = Path(
            self.config.settings.test_tools_directory or "./test_tools"
        )
        self.integration_test_path = Path(
            self.config.settings.integration_test_path or "./tests/integration"
        )
        self.bug_severity_levels = self.config.settings.bug_severity_levels or [
            "low",
            "medium",
            "high",
        ]
        self.supported_languages = self.config.settings.supported_languages or [
            "python",
            "javascript",
            "bash",
        ]
        self.enable_bug_injection = self.config.settings.enable_bug_injection or True

        # Ensure directories exist
        self.test_tools_directory.mkdir(parents=True, exist_ok=True)
        self.integration_test_path.mkdir(parents=True, exist_ok=True)

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process a query for the testing agent."""
        query_lower = query.lower()

        if "create tool" in query_lower or "add tool" in query_lower:
            return await self._handle_create_tool_request(query, context)
        elif "list tools" in query_lower or "show tools" in query_lower:
            return await self._handle_list_tools_request(query, context)
        elif "execute tool" in query_lower or "run tool" in query_lower:
            return await self._handle_execute_tool_request(query, context)
        elif "create test" in query_lower or "integration test" in query_lower:
            return await self._handle_create_integration_test_request(query, context)
        elif "introduce bug" in query_lower or "add bug" in query_lower:
            return await self._handle_introduce_bug_request(query, context)
        elif "status" in query_lower or "info" in query_lower:
            return await self._handle_status_request(query, context)
        else:
            return await self._handle_general_query(query, context)

    async def _handle_create_tool_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to create test tools."""
        try:
            # Use LLM to generate the tool based on the request
            messages = [
                {"role": "system", "content": self._get_tool_creation_prompt()},
                {"role": "user", "content": f"Create a test tool based on this request: {query}"},
            ]

            response = await self.llm_completion(
                messages, session_id=context.get("session_id") if context else None
            )

            # Parse the response to extract tool details
            tool = await self._parse_tool_from_response(response)

            if tool:
                # Save the tool
                self.test_tools[tool.id] = tool
                await self._save_tool_to_file(tool)

                self.log_activity(
                    "tool_created",
                    {
                        "tool_id": tool.id,
                        "name": tool.name,
                        "language": tool.language,
                        "has_bugs": tool.has_bugs,
                    },
                )

                return f"✅ Test tool '{tool.name}' created successfully!\n\n{response}"
            else:
                return f"❌ Failed to create tool. Response: {response}"

        except Exception as e:
            self.log_activity("tool_creation_error", {"error": str(e)})
            return f"❌ Error creating tool: {str(e)}"

    async def _handle_list_tools_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to list test tools."""
        if not self.test_tools:
            return "📝 No test tools have been created yet."

        tools_list = []
        for tool in self.test_tools.values():
            status = "🐛 Has bugs" if tool.has_bugs else "✅ Clean"
            tools_list.append(
                f"- **{tool.name}** ({tool.language}) - {status}\n  📝 {tool.description}"
            )

        return f"🔧 **Test Tools ({len(self.test_tools)} total):**\n\n" + "\n\n".join(tools_list)

    async def _handle_execute_tool_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to execute test tools."""
        # Extract tool name/id from query
        tool_name = self._extract_tool_name_from_query(query)

        if not tool_name:
            return "❌ Please specify which tool to execute."

        # Find the tool
        tool = None
        for t in self.test_tools.values():
            if tool_name.lower() in t.name.lower():
                tool = t
                break

        if not tool:
            return f"❌ Tool '{tool_name}' not found."

        # Execute the tool
        result = await self._execute_tool(tool)
        return result

    async def _handle_create_integration_test_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to create integration tests."""
        try:
            messages = [
                {"role": "system", "content": self._get_integration_test_prompt()},
                {"role": "user", "content": f"Create an integration test based on: {query}"},
            ]

            response = await self.llm_completion(
                messages, session_id=context.get("session_id") if context else None
            )

            # Save the integration test
            test_file = (
                self.integration_test_path
                / f"test_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            )
            with open(test_file, "w") as f:
                f.write(response)

            self.log_activity("integration_test_created", {"file": str(test_file)})

            return f"✅ Integration test created at: {test_file}\n\n```python\n{response}\n```"

        except Exception as e:
            self.log_activity("integration_test_error", {"error": str(e)})
            return f"❌ Error creating integration test: {str(e)}"

    async def _handle_introduce_bug_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to introduce bugs into existing tools."""
        if not self.enable_bug_injection:
            return "❌ Bug injection is disabled in configuration."

        try:
            messages = [
                {"role": "system", "content": self._get_bug_injection_prompt()},
                {"role": "user", "content": f"Introduce a bug based on: {query}"},
            ]

            response = await self.llm_completion(
                messages, session_id=context.get("session_id") if context else None
            )

            # Create a buggy tool or modify existing one
            # This would involve parsing the response and creating/modifying tools

            self.log_activity("bug_introduced", {"query": query})

            return f"🐛 Bug introduction completed:\n\n{response}"

        except Exception as e:
            self.log_activity("bug_injection_error", {"error": str(e)})
            return f"❌ Error introducing bug: {str(e)}"

    async def _handle_status_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle status/info requests."""
        total_tools = len(self.test_tools)
        buggy_tools = sum(1 for tool in self.test_tools.values() if tool.has_bugs)
        clean_tools = total_tools - buggy_tools

        status_info = f"""🧪 **Testing Agent Status**

**Tool Statistics:**
- Total tools: {total_tools}
- Clean tools: {clean_tools} ✅
- Buggy tools: {buggy_tools} 🐛

**Configuration:**
- Test tools directory: {self.test_tools_directory}
- Integration test path: {self.integration_test_path}
- Bug injection enabled: {"Yes" if self.enable_bug_injection else "No"}
- Supported languages: {", ".join(self.supported_languages)}

**Capabilities:**
- Create test tools with controlled bugs
- Generate integration tests
- Execute and monitor test tools
- Coordinate with other agents for bug detection

Recent activity count: {len(self.recent_activities)}
"""
        return status_info

    async def _handle_general_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle general queries about testing."""
        messages = [
            {
                "role": "system",
                "content": f"""You are the Vectras testing agent. You help with:

1. Creating test tools (potentially with bugs for other agents to find)
2. Generating integration tests
3. Testing agent coordination
4. Quality assurance

Current status:
- Tools created: {len(self.test_tools)}
- Test directory: {self.test_tools_directory}
- Bug injection enabled: {self.enable_bug_injection}

Provide helpful information about testing capabilities and guide users on what they can do.""",
            },
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(
            messages, session_id=context.get("session_id") if context else None
        )

    def _get_tool_creation_prompt(self) -> str:
        """Get the system prompt for tool creation."""
        return f"""You are a test tool creator. Create functional code tools that can optionally contain bugs for testing purposes.

Guidelines:
1. Supported languages: {", ".join(self.supported_languages)}
2. Tools should be small, focused utilities
3. If requested, introduce realistic bugs that other agents might detect
4. Always provide clear descriptions of what the tool does
5. If adding bugs, specify what type of bug and its severity level

Format your response as a clear description of the tool, followed by the code block."""

    def _get_integration_test_prompt(self) -> str:
        """Get the system prompt for integration test creation."""
        return """You are creating integration tests for the Vectras agent system.

Create pytest-based integration tests that:
1. Test agent interactions and coordination
2. Verify system functionality end-to-end
3. Can be run automatically
4. Include proper assertions and error handling

Write complete Python test files using pytest conventions."""

    def _get_bug_injection_prompt(self) -> str:
        """Get the system prompt for bug injection."""
        return f"""You are introducing controlled bugs for testing purposes.

Guidelines:
1. Create realistic bugs that might occur in development
2. Use severity levels: {", ".join(self.bug_severity_levels)}
3. Bugs should be detectable by monitoring and analysis
4. Document what the bug is and how it might manifest
5. Make bugs educational and realistic

Describe the bug introduced and provide the buggy code."""

    async def _parse_tool_from_response(self, response: str) -> Optional[TestingTool]:
        """Parse a TestingTool from LLM response."""
        try:
            # Simple parsing - in a real implementation, this would be more sophisticated
            lines = response.split("\n")
            name = f"tool_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            language = "python"  # Default
            description = "Generated test tool"
            has_bugs = "bug" in response.lower() or "error" in response.lower()

            # Extract code block if present
            code_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    if not in_code_block:
                        in_code_block = True
                        # Try to detect language
                        lang = line.strip()[3:].strip()
                        if lang in self.supported_languages:
                            language = lang
                    else:
                        in_code_block = False
                elif in_code_block:
                    code_lines.append(line)

            code = "\n".join(code_lines) if code_lines else response

            return TestingTool(
                name=name,
                language=language,
                code=code,
                description=description,
                has_bugs=has_bugs,
                severity=random.choice(self.bug_severity_levels) if has_bugs else "low",
            )

        except Exception as e:
            self.log_activity("tool_parsing_error", {"error": str(e)})
            return None

    async def _save_tool_to_file(self, tool: TestingTool) -> None:
        """Save a tool to the file system."""
        try:
            extension_map = {"python": ".py", "javascript": ".js", "bash": ".sh"}

            extension = extension_map.get(tool.language, ".txt")
            file_path = self.test_tools_directory / f"{tool.name}{extension}"

            with open(file_path, "w") as f:
                f.write(f"# {tool.description}\n")
                f.write(f"# Created: {tool.created_at}\n")
                f.write(f"# Has bugs: {tool.has_bugs}\n")
                if tool.has_bugs:
                    f.write(f"# Bug description: {tool.bug_description}\n")
                f.write(f"# Severity: {tool.severity}\n\n")
                f.write(tool.code)

        except Exception as e:
            self.log_activity("tool_save_error", {"error": str(e), "tool_id": tool.id})

    async def _execute_tool(self, tool: TestingTool) -> str:
        """Execute a test tool and return results."""
        try:
            tool.executed_count += 1

            if tool.language == "python":
                # In a real implementation, this would run in a sandbox
                return (
                    f"🔧 Simulated execution of Python tool '{tool.name}'\n\nCode:\n```python\n{tool.code}\n```\n\n"
                    + (
                        f"⚠️ This tool has known bugs: {tool.bug_description}"
                        if tool.has_bugs
                        else "✅ Tool executed successfully"
                    )
                )
            else:
                return f"🔧 Simulated execution of {tool.language} tool '{tool.name}'\n\n" + (
                    f"⚠️ This tool has known bugs: {tool.bug_description}"
                    if tool.has_bugs
                    else "✅ Tool executed successfully"
                )

        except Exception as e:
            tool.last_error = str(e)
            self.log_activity("tool_execution_error", {"error": str(e), "tool_id": tool.id})
            return f"❌ Error executing tool '{tool.name}': {str(e)}"

    def _extract_tool_name_from_query(self, query: str) -> Optional[str]:
        """Extract tool name from a query."""
        # Simple extraction - look for quoted names or names after "tool"
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() in ["execute", "run"] and i + 1 < len(words):
                # If next word is "tool", get the word after that
                if words[i + 1].lower() == "tool" and i + 2 < len(words):
                    return words[i + 2]  # Don't strip quotes
                # Otherwise, return the word after execute/run
                return words[i + 1].strip("'\"")
            elif word.lower() == "tool" and i + 1 < len(words):
                return words[i + 1]  # Don't strip quotes

        # Only use fallback if the query seems to be about tools
        if any(word.lower() in ["tool", "execute", "run", "calculator", "test"] for word in words):
            if words:
                return words[-1].strip("'\"")
        return None


# Create the agent instance
testing_agent = TestingAgent()


def create_app():
    """Create FastAPI app for the testing agent."""
    return testing_agent.create_app()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = testing_agent.config.port or 8126
    uvicorn.run(app, host="0.0.0.0", port=port)
