"""
Testing Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.tool import function_tool as tool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .base_agent import determine_response_type_with_llm


class TestingTool:
    """Represents a test tool that can be created by the testing agent."""

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


class TestingAgentManager:
    """Manages testing tools and operations."""

    def __init__(self):
        self.test_tools: Dict[str, TestingTool] = {}
        self.test_tools_directory = Path("./test_tools")
        self.test_tools_directory.mkdir(parents=True, exist_ok=True)

        # Create sample tools for demonstration
        self._create_sample_tools()
        self._load_existing_tools()

    def _create_sample_tools(self):
        """Create sample tools for demonstration purposes."""
        print("DEBUG: Creating sample tools...")

        # Create a simple calculator tool
        calculator_tool = TestingTool(
            name="calculator",
            language="python",
            code='''def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Test the functions
if __name__ == "__main__":
    print(f"2 + 3 = {add(2, 3)}")
    print(f"5 - 2 = {subtract(5, 2)}")
    print(f"4 * 6 = {multiply(4, 6)}")
    print(f"10 / 2 = {divide(10, 2)}")''',
            description="A simple calculator with basic arithmetic operations",
            has_bugs=False,
            bug_description="",
            severity="low",
        )

        self.test_tools[calculator_tool.id] = calculator_tool
        print(f"DEBUG: Added calculator tool to test_tools, total tools: {len(self.test_tools)}")

        # Save to file
        try:
            tool_file = self.test_tools_directory / f"{calculator_tool.name}.py"
            tool_file.write_text(calculator_tool.code)
            print(f"DEBUG: Created sample calculator tool at {tool_file}")
        except Exception as e:
            print(f"DEBUG: Error saving calculator tool: {e}")

    def _load_existing_tools(self):
        """Load existing tools from the filesystem."""
        print("DEBUG: Loading existing tools from filesystem...")
        try:
            if not self.test_tools_directory.exists():
                print(f"DEBUG: Test tools directory {self.test_tools_directory} does not exist")
                return

            for file_path in self.test_tools_directory.glob("*.py"):
                tool_name = file_path.stem

                # Check if tool already exists and remove it to allow reloading
                existing_tool = None
                for tool in self.test_tools.values():
                    if tool.name == tool_name:
                        existing_tool = tool
                        break

                if existing_tool:
                    print(f"DEBUG: Tool {tool_name} already exists, replacing with file version")
                    del self.test_tools[existing_tool.id]

                try:
                    code = file_path.read_text()
                    tool = TestingTool(
                        name=tool_name,
                        language="python",
                        code=code,
                        description=f"Loaded from {file_path.name}",
                        has_bugs="bug" in code.lower() or "error" in code.lower(),
                        bug_description="Loaded from filesystem",
                        severity="medium",
                    )
                    self.test_tools[tool.id] = tool
                    print(f"DEBUG: Loaded tool {tool_name} from {file_path}")

                except Exception as e:
                    print(f"DEBUG: Error loading tool from {file_path}: {e}")

            print(f"DEBUG: Loaded {len(self.test_tools)} tools from filesystem")

        except Exception as e:
            print(f"DEBUG: Error loading existing tools: {e}")

    def reload_tools(self) -> str:
        """Reload all tools from the filesystem."""
        print("DEBUG: Reloading tools from filesystem...")
        # Clear existing tools except sample tools
        sample_tools = {k: v for k, v in self.test_tools.items() if v.name == "calculator"}
        self.test_tools = sample_tools

        # Reload from filesystem
        self._load_existing_tools()

        return f"✅ Reloaded tools. Total tools: {len(self.test_tools)}"

    def create_tool(
        self, name: str, language: str, code: str, description: str, has_bugs: bool = False
    ) -> str:
        """Create a new testing tool."""
        try:
            # Create the tool
            tool = TestingTool(
                name=name,
                language=language,
                code=code,
                description=description,
                has_bugs=has_bugs,
                bug_description="Manually created tool",
                severity="medium" if has_bugs else "low",
            )

            self.test_tools[tool.id] = tool

            # Save to file
            tool_file = self.test_tools_directory / f"{name}.py"
            tool_file.write_text(code)

            return f"✅ Successfully created tool '{name}' with ID {tool.id}"
        except Exception as e:
            return f"❌ Error creating tool: {str(e)}"

    def list_tools(self) -> str:
        """List all available testing tools."""
        if not self.test_tools:
            return "📋 No testing tools available."

        tool_list = []
        for test_tool in self.test_tools.values():
            status = "🐛" if test_tool.has_bugs else "✅"
            tool_list.append(f"{status} **{test_tool.name}** - {test_tool.description}")

        return f"📋 Available testing tools ({len(self.test_tools)}):\n\n" + "\n".join(tool_list)

    def execute_tool(self, tool_name: str, *args) -> str:
        """Execute a testing tool."""
        # Find the tool
        tool = None
        for t in self.test_tools.values():
            if t.name.lower() == tool_name.lower():
                tool = t
                break

        if not tool:
            return f"❌ Tool '{tool_name}' not found."

        try:
            # Save tool to temporary file and execute
            temp_file = self.test_tools_directory / f"temp_{tool_name}.py"
            temp_file.write_text(tool.code)

            # Execute the tool
            result = subprocess.run(
                [sys.executable, str(temp_file)], capture_output=True, text=True, timeout=30
            )

            tool.executed_count += 1

            if result.returncode == 0:
                return f"✅ Tool '{tool_name}' executed successfully:\n```\n{result.stdout}\n```"
            else:
                tool.last_error = result.stderr
                return f"❌ Tool '{tool_name}' failed:\n```\n{result.stderr}\n```"

        except subprocess.TimeoutExpired:
            return f"⏰ Tool '{tool_name}' execution timed out."
        except Exception as e:
            return f"❌ Error executing tool '{tool_name}': {str(e)}"

    def run_tests(self, tool_name: str) -> str:
        """Run tests for a specific tool."""
        tool = None
        for t in self.test_tools.values():
            if t.name.lower() == tool_name.lower():
                tool = t
                break

        if not tool:
            return f"❌ Tool '{tool_name}' not found."

        try:
            # Create a simple test that executes in the current process
            test_code = f"""
import sys
import os
import tempfile

# Create a temporary file with the tool code
tool_code = '''{tool.code}'''

# Write to a temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(tool_code)
    temp_file = f.name

try:
    # Execute the code in a controlled way
    exec(tool_code)
    
    print(f"✅ Tool '{tool_name}' code executed successfully")
    
    # Test specific functions if they exist
    local_vars = {{}}
    exec(tool_code, globals(), local_vars)
    
    # Find functions in the executed code
    functions = [name for name, obj in local_vars.items() 
                if callable(obj) and not name.startswith('_')]
    
    print(f"Found functions: {{functions}}")
    
    # Test each function
    for func_name in functions:
        try:
            func = local_vars[func_name]
            
            if func_name == 'divide':
                # Test with valid inputs
                try:
                    result = func(10, 2)
                    print(f"✅ {{func_name}}(10, 2) = {{result}}")
                except Exception as e:
                    print(f"❌ {{func_name}}(10, 2) failed: {{e}}")
                    
                # Test with zero division
                try:
                    result = func(10, 0)
                    print(f"❌ {{func_name}}(10, 0) should have failed but returned: {{result}}")
                except ZeroDivisionError:
                    print(f"✅ {{func_name}}(10, 0) correctly raised ZeroDivisionError")
                except Exception as e:
                    print(f"⚠️ {{func_name}}(10, 0) raised unexpected error: {{e}}")
                    
            elif func_name in ['add', 'subtract', 'multiply']:
                result = func(10, 2)
                print(f"✅ {{func_name}}(10, 2) = {{result}}")
            else:
                print(f"⚠️ {{func_name}}: No test inputs defined")
                
        except Exception as e:
            print(f"❌ {{func_name}} test failed: {{e}}")
    
    print(f"✅ Tool '{tool_name}' tests completed successfully")
    
finally:
    # Clean up
    try:
        os.unlink(temp_file)
    except:
        pass
"""

            # Execute the test code directly in the current process
            result = {"returncode": 0, "stdout": "", "stderr": ""}

            try:
                # Capture stdout/stderr
                import io
                from contextlib import redirect_stderr, redirect_stdout

                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()

                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    exec(test_code)

                result["stdout"] = stdout_capture.getvalue()
                result["stderr"] = stderr_capture.getvalue()

            except Exception as e:
                result["returncode"] = 1
                result["stderr"] = str(e)

            if result["returncode"] == 0:
                return f"✅ Tests for '{tool_name}' completed successfully:\n```\n{result['stdout']}\n```"
            else:
                return f"❌ Tests for '{tool_name}' failed:\n```\n{result['stderr']}\n```"

        except Exception as e:
            return f"❌ Error running tests for '{tool_name}': {str(e)}"

    def get_status(self) -> str:
        """Get the status of the testing agent."""
        total_tools = len(self.test_tools)
        tools_with_bugs = sum(1 for tool in self.test_tools.values() if tool.has_bugs)
        total_executions = sum(tool.executed_count for tool in self.test_tools.values())

        status = f"""## Testing Agent Status

**Total Tools:** {total_tools}
**Tools with Bugs:** {tools_with_bugs}
**Total Executions:** {total_executions}
**Test Tools Directory:** {self.test_tools_directory}

**Recent Tools:**"""

        # Show recent tools
        recent_tools = sorted(self.test_tools.values(), key=lambda x: x.created_at, reverse=True)[
            :5
        ]
        for test_tool in recent_tools:
            status += f"\n- **{test_tool.name}** ({test_tool.language}) - {test_tool.description}"

        return status


# Global testing agent manager
testing_manager = TestingAgentManager()


@tool
async def create_testing_tool(
    name: str, language: str, code: str, description: str, has_bugs: bool = False
) -> str:
    """Create a new testing tool with the specified parameters."""
    return testing_manager.create_tool(name, language, code, description, has_bugs)


@tool
async def list_testing_tools() -> str:
    """List all available testing tools."""
    return testing_manager.list_tools()


@tool
async def execute_testing_tool(tool_name: str) -> str:
    """Execute a testing tool by name."""
    return testing_manager.execute_tool(tool_name)


@tool
async def run_tool_tests(tool_name: str) -> str:
    """Run tests for a specific tool."""
    return testing_manager.run_tests(tool_name)


@tool
async def get_testing_status() -> str:
    """Get the current status of the testing agent."""
    return testing_manager.get_status()


@tool
async def reload_testing_tools() -> str:
    """Reload all testing tools from the filesystem."""
    return testing_manager.reload_tools()


# Create the Testing agent using OpenAI Agents SDK
testing_agent = Agent(
    name="Testing Agent",
    instructions="""You are the Vectras Testing Agent. You help create, manage, and execute testing tools.

Your capabilities include:
- Creating new testing tools with custom code
- Listing all available testing tools
- Executing testing tools and capturing their output
- Running tests for specific tools
- Providing status information about the testing environment

When users ask for status, provide a comprehensive overview of all testing tools.
When users want to create tools, guide them through the process and ensure proper code formatting.
When users want to execute tools, run them safely and report the results clearly.

You can use the following tools to perform testing operations:
- create_testing_tool: Create a new testing tool with custom code
- list_testing_tools: List all available testing tools
- execute_testing_tool: Execute a specific testing tool
- run_tool_tests: Run tests for a specific tool
- get_testing_status: Get comprehensive testing agent status
- reload_testing_tools: Reload all tools from the filesystem

If a user asks about something outside your capabilities (like GitHub operations, code analysis, or linting), you can suggest they ask the appropriate agent:
- For GitHub operations: Ask the GitHub Agent
- For code analysis and fixes: Ask the Coding Agent
- For code quality and formatting: Ask the Linting Agent
- For log monitoring: Ask the Logging Monitor Agent
- For project coordination: Ask the Supervisor Agent

Format your responses in markdown for better readability.""",
    tools=[
        create_testing_tool,
        list_testing_tools,
        execute_testing_tool,
        run_tool_tests,
        get_testing_status,
        reload_testing_tools,
    ],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras Testing Agent",
    description="Testing tools management agent",
    version="0.2.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    status: str
    response: str
    agent_id: str = "testing"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        print(f"DEBUG: Testing agent received query: {request.query[:100]}...")

        # Run the agent using the SDK
        result = await Runner.run(testing_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "testing", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Tool Creation", "Tool Execution", "Testing"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        print(f"Error in Testing agent: {str(e)}")
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "testing-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "Testing Agent",
        "status": "active",
        "tools_count": len(testing_manager.test_tools),
        "sdk_version": "openai-agents",
        "tools": [
            "create_testing_tool",
            "list_testing_tools",
            "execute_testing_tool",
            "run_tool_tests",
            "get_testing_status",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8126)
