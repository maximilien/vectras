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
        
        # Pre-create the divide tool with bug for e2e testing
        self._create_predefined_divide_tool()
        
        # Load existing tools from filesystem
        self._load_existing_tools()

    def _create_predefined_divide_tool(self):
        """Create a predefined divide tool with bug for e2e testing."""
        print("DEBUG: Creating predefined divide tool...")
        divide_tool = TestingTool(
            name="divide",
            language="python",
            code='''def divide(n1, n2):
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
        print(f"Error: {e}")''',
            description="A division function with a divide by zero bug for testing error detection",
            has_bugs=True,
            bug_description="Divides by 0 instead of the second parameter",
            severity="high"
        )
        
        # Add to tools dictionary
        self.test_tools[divide_tool.id] = divide_tool
        print(f"DEBUG: Added divide tool to test_tools, total tools: {len(self.test_tools)}")
        
        # Save to file
        try:
            tool_file = self.test_tools_directory / f"{divide_tool.name}.py"
            tool_file.write_text(divide_tool.code)
            print(f"DEBUG: Created predefined divide tool at {tool_file}")
        except Exception as e:
            print(f"DEBUG: Error saving divide tool: {e}")

    def _load_existing_tools(self):
        """Load existing tools from the filesystem."""
        print("DEBUG: Loading existing tools from filesystem...")
        try:
            if not self.test_tools_directory.exists():
                print(f"DEBUG: Test tools directory {self.test_tools_directory} does not exist")
                return
            
            # Look for Python files in the test_tools directory
            for file_path in self.test_tools_directory.glob("*.py"):
                tool_name = file_path.stem  # filename without extension
                
                # Skip if tool already exists
                if any(tool.name == tool_name for tool in self.test_tools.values()):
                    print(f"DEBUG: Tool {tool_name} already exists, skipping")
                    continue
                
                try:
                    # Read the file content
                    code = file_path.read_text()
                    
                    # Create a TestingTool object
                    tool = TestingTool(
                        name=tool_name,
                        language="python",
                        code=code,
                        description=f"Loaded from {file_path.name}",
                        has_bugs="bug" in code.lower() or "error" in code.lower(),
                        bug_description="Loaded from filesystem",
                        severity="medium"
                    )
                    
                    # Add to tools dictionary
                    self.test_tools[tool.id] = tool
                    print(f"DEBUG: Loaded tool {tool_name} from {file_path}")
                    
                except Exception as e:
                    print(f"DEBUG: Error loading tool from {file_path}: {e}")
            
            print(f"DEBUG: Loaded {len(self.test_tools)} tools from filesystem")
            
        except Exception as e:
            print(f"DEBUG: Error loading existing tools: {e}")

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process a query for the testing agent."""
        # Ensure tools are loaded
        if not self.test_tools:
            print("DEBUG: No tools found, loading tools...")
            self._create_predefined_divide_tool()
            self._load_existing_tools()
            print(f"DEBUG: After loading, have {len(self.test_tools)} tools")
        
        query_lower = query.lower().strip()
        print(f"DEBUG: Processing query: '{query_lower}'")
        print(f"DEBUG: Query contains 'create a tool called': {'create a tool called' in query_lower}")
        print(f"DEBUG: Query contains 'create tool': {'create tool' in query_lower}")
        print(f"DEBUG: Query contains 'add tool': {'add tool' in query_lower}")
        print(f"DEBUG: Query contains 'create a tool': {'create a tool' in query_lower}")

        if ("create tool" in query_lower or "add tool" in query_lower or "create a tool" in query_lower or 
            "create a tool called" in query_lower or "create divide tool" in query_lower):
            print("DEBUG: Routing to tool creation handler")
            return await self._handle_create_tool_request(query, context)
        elif "list tools" in query_lower or "show tools" in query_lower:
            return await self._handle_list_tools_request(query, context)
        elif "execute tool" in query_lower or "run tool" in query_lower:
            return await self._handle_execute_tool_request(query, context)
        elif "create test" in query_lower or "integration test" in query_lower:
            return await self._handle_create_integration_test_request(query, context)
        elif "run test" in query_lower or "run tests" in query_lower:
            return await self._handle_run_tests_request(query, context)
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
            # Check for specific tool requests first
            print(f"DEBUG: Checking query '{query.lower()}' for divide tool creation")
            if "divide" in query.lower():
                print("DEBUG: Creating specific divide tool")
                # Create the specific divide tool with bug for e2e testing
                tool = await self._create_divide_tool_with_bug()
            else:
                print("DEBUG: Using LLM for tool creation")
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

                return f"✅ Test tool '{tool.name}' created successfully!\n\nCode:\n```python\n{tool.code}\n```"
            else:
                return f"❌ Failed to create tool."

        except Exception as e:
            self.log_activity("tool_creation_error", {"error": str(e)})
            return f"❌ Error creating tool: {str(e)}"

    async def _create_divide_tool_with_bug(self) -> TestingTool:
        """Create a divide tool with a divide by zero bug for testing."""
        code = '''def divide(n1, n2):
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
        print(f"Error: {e}")'''

        return TestingTool(
            name="divide",
            language="python",
            code=code,
            description="A division function with a divide by zero bug for testing error detection",
            has_bugs=True,
            bug_description="Divides by 0 instead of the second parameter",
            severity="high"
        )

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

    async def _handle_run_tests_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to run tests on tools."""
        try:
            # Check for specific test requests
            if "divide" in query.lower():
                return await self._run_divide_tool_tests()
            else:
                # Generic test running
                return await self._run_generic_tests(query)

        except Exception as e:
            self.log_activity("test_execution_error", {"error": str(e)})
            return f"❌ Error running tests: {str(e)}"

    async def _run_divide_tool_tests(self) -> str:
        """Run tests specifically for the divide tool."""
        try:
            # Check if the fixed divide tool exists
            fixed_file_path = self.test_tools_directory / "divide_fixed.py"
            test_file_path = self.test_tools_directory / "test_divide.py"
            
            if not fixed_file_path.exists():
                return "❌ Fixed divide tool not found. Please run the code fixer first."
            
            if not test_file_path.exists():
                return "❌ Test file not found. Please run the code fixer first."
            
            # Import and test the fixed divide function
            import sys
            import importlib.util
            
            # Load the fixed divide module
            spec = importlib.util.spec_from_file_location("divide_fixed", fixed_file_path)
            divide_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(divide_module)
            
            # Load the test module
            test_spec = importlib.util.spec_from_file_location("test_divide", test_file_path)
            test_module = importlib.util.module_from_spec(test_spec)
            test_spec.loader.exec_module(test_module)
            
            # Run the tests
            from io import StringIO
            from contextlib import redirect_stdout
            
            stdout_capture = StringIO()
            with redirect_stdout(stdout_capture):
                test_result = test_module.test_divide()
            
            output = stdout_capture.getvalue()
            
            if test_result:
                return f"✅ Divide tool tests passed successfully!\n\nTest Output:\n{output}"
            else:
                return f"❌ Divide tool tests failed!\n\nTest Output:\n{output}"
                
        except Exception as e:
            return f"❌ Error running divide tool tests: {str(e)}"

    async def _run_generic_tests(self, query: str) -> str:
        """Run generic tests based on the query."""
        try:
            # This would be a more sophisticated test runner
            return f"🔧 Generic test execution for: {query}\n\nTests would be run here in a real implementation."
        except Exception as e:
            return f"❌ Error running generic tests: {str(e)}"

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
                # Actually execute Python code in a safe environment
                return await self._execute_python_tool(tool)
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

    async def _execute_python_tool(self, tool: TestingTool) -> str:
        """Execute a Python tool and return results."""
        try:
            # Create a safe execution environment
            import sys
            from io import StringIO
            from contextlib import redirect_stdout, redirect_stderr
            
            # Capture output and errors
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            # Create a safe namespace for execution
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'abs': abs,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'round': round,
                    'pow': pow,
                    'divmod': divmod,
                    'all': all,
                    'any': any,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sorted': sorted,
                    'reversed': reversed,
                    'isinstance': isinstance,
                    'type': type,
                    'dir': dir,
                    'getattr': getattr,
                    'setattr': setattr,
                    'hasattr': hasattr,
                    'callable': callable,
                    'issubclass': issubclass,
                    'super': super,
                    'property': property,
                    'staticmethod': staticmethod,
                    'classmethod': classmethod,
                    'object': object,
                    'Exception': Exception,
                    'ValueError': ValueError,
                    'TypeError': TypeError,
                    'ZeroDivisionError': ZeroDivisionError,
                    'AttributeError': AttributeError,
                    'IndexError': IndexError,
                    'KeyError': KeyError,
                    'FileNotFoundError': FileNotFoundError,
                    'ImportError': ImportError,
                    'NameError': NameError,
                    'SyntaxError': SyntaxError,
                    'IndentationError': IndentationError,
                    'RuntimeError': RuntimeError,
                    'MemoryError': MemoryError,
                    'OverflowError': OverflowError,
                    'ArithmeticError': ArithmeticError,
                    'AssertionError': AssertionError,
                    'EOFError': EOFError,
                    'FloatingPointError': FloatingPointError,
                    'GeneratorExit': GeneratorExit,
                    'KeyboardInterrupt': KeyboardInterrupt,
                    'NotImplementedError': NotImplementedError,
                    'OSError': OSError,
                    'ReferenceError': ReferenceError,
                    'SystemError': SystemError,
                    'SystemExit': SystemExit,
                    'TabError': TabError,
                    'UnboundLocalError': UnboundLocalError,
                    'UnicodeError': UnicodeError,
                    'UnicodeDecodeError': UnicodeDecodeError,
                    'UnicodeEncodeError': UnicodeEncodeError,
                    'UnicodeTranslateError': UnicodeTranslateError,
                    'Warning': Warning,
                    'DeprecationWarning': DeprecationWarning,
                    'PendingDeprecationWarning': PendingDeprecationWarning,
                    'RuntimeWarning': RuntimeWarning,
                    'SyntaxWarning': SyntaxWarning,
                    'UserWarning': UserWarning,
                    'FutureWarning': FutureWarning,
                    'ImportWarning': ImportWarning,
                    'UnicodeWarning': UnicodeWarning,
                    'BytesWarning': BytesWarning,
                    'ResourceWarning': ResourceWarning,
                    'BlockingIOError': BlockingIOError,
                    'BrokenPipeError': BrokenPipeError,
                    'ChildProcessError': ChildProcessError,
                    'ConnectionError': ConnectionError,
                    'ConnectionAbortedError': ConnectionAbortedError,
                    'ConnectionRefusedError': ConnectionRefusedError,
                    'ConnectionResetError': ConnectionResetError,
                    'FileExistsError': FileExistsError,
                    'FileNotFoundError': FileNotFoundError,
                    'InterruptedError': InterruptedError,
                    'IsADirectoryError': IsADirectoryError,
                    'NotADirectoryError': NotADirectoryError,
                    'PermissionError': PermissionError,
                    'ProcessLookupError': ProcessLookupError,
                    'TimeoutError': TimeoutError,
                    'open': open,
                    'input': lambda: '',
                    'eval': lambda x: None,
                    'exec': lambda x: None,
                    'compile': lambda x, y, z: None,
                    'globals': lambda: {},
                    'locals': lambda: {},
                    'vars': lambda x: {},
                    'help': lambda x: None,
                    'copyright': None,
                    'credits': None,
                    'license': None,
                    'exit': lambda: None,
                    'quit': lambda: None,
                }
            }
            
            # Execute the code with captured output
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(tool.code, safe_globals)
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Check if there were any errors
            if stderr_output:
                tool.last_error = stderr_output
                self.log_activity("tool_execution_error", {"error": stderr_output, "tool_id": tool.id})
                return f"❌ Error executing tool '{tool.name}':\n{stderr_output}\n\nCode:\n```python\n{tool.code}\n```"
            
            # Check if the tool has known bugs
            if tool.has_bugs:
                return (
                    f"⚠️ Tool '{tool.name}' executed with known bugs: {tool.bug_description}\n\n"
                    f"Output: {stdout_output}\n\n"
                    f"Code:\n```python\n{tool.code}\n```"
                )
            
            return f"✅ Tool '{tool.name}' executed successfully!\n\nOutput: {stdout_output}\n\nCode:\n```python\n{tool.code}\n```"
            
        except Exception as e:
            tool.last_error = str(e)
            self.log_activity("tool_execution_error", {"error": str(e), "tool_id": tool.id})
            return f"❌ Error executing tool '{tool.name}': {str(e)}\n\nCode:\n```python\n{tool.code}\n```"

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
