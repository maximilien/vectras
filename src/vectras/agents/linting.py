"""
Linting Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.tool import function_tool as tool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .base_agent import determine_response_type_with_llm


class LintingManager:
    """Manages linting operations and code quality checks."""

    def __init__(self):
        self.linters = {
            "python": ["ruff", "black"],
            "javascript": ["eslint", "prettier"],
            "bash": ["shellcheck"],
        }
        self.auto_fix = True
        self.format_on_save = True
        self.lint_directories = [Path("./src"), Path("./tests"), Path("./frontend")]
        self.exclude_patterns = [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.venv/**",
        ]
        self.lint_history = []

    def _extract_target_from_query(self, query: str) -> Optional[str]:
        """Extract target from query."""
        query_lower = query.lower()

        # Look for specific file or directory mentions
        if "divide" in query_lower and "tool" in query_lower:
            return "divide"
        elif "test_tools" in query_lower:
            return "test_tools"
        elif "src" in query_lower:
            return "src"
        elif "tests" in query_lower:
            return "tests"
        elif "frontend" in query_lower:
            return "frontend"
        elif "all" in query_lower or "everything" in query_lower:
            return "all"
        else:
            return None

    def _get_file_extension(self, file_path: Path) -> str:
        """Get file extension for determining linter."""
        return file_path.suffix.lower()

    def _get_linters_for_file(self, file_path: Path) -> List[str]:
        """Get appropriate linters for a file."""
        ext = self._get_file_extension(file_path)

        if ext == ".py":
            return self.linters["python"]
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            return self.linters["javascript"]
        elif ext in [".sh", ".bash"]:
            return self.linters["bash"]
        else:
            return []

    async def lint_file(self, file_path: str) -> str:
        """Lint a specific file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"❌ File '{file_path}' not found."

            linters = self._get_linters_for_file(path)
            if not linters:
                return f"⚠️ No linters configured for file type: {path.suffix}"

            results = []
            for linter in linters:
                try:
                    if linter == "ruff":
                        result = subprocess.run(
                            [linter, "check", str(path)], capture_output=True, text=True, timeout=30
                        )
                        if result.returncode == 0:
                            results.append(f"✅ {linter}: No issues found")
                        else:
                            results.append(f"❌ {linter}:\n{result.stdout}\n{result.stderr}")

                    elif linter == "black":
                        result = subprocess.run(
                            [linter, "--check", str(path)],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if result.returncode == 0:
                            results.append(f"✅ {linter}: Code is properly formatted")
                        else:
                            results.append(f"⚠️ {linter}: Code needs formatting\n{result.stdout}")

                    else:
                        results.append(f"⚠️ Linter '{linter}' not implemented yet")

                except subprocess.TimeoutExpired:
                    results.append(f"⏰ {linter}: Timeout")
                except FileNotFoundError:
                    results.append(f"❌ {linter}: Not installed")
                except Exception as e:
                    results.append(f"❌ {linter}: Error - {str(e)}")

            return f"## Linting Results for {file_path}\n\n" + "\n\n".join(results)

        except Exception as e:
            return f"❌ Error linting file '{file_path}': {str(e)}"

    async def fix_file(self, file_path: str) -> str:
        """Auto-fix a specific file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"❌ File '{file_path}' not found."

            linters = self._get_linters_for_file(path)
            if not linters:
                return f"⚠️ No linters configured for file type: {path.suffix}"

            results = []
            for linter in linters:
                try:
                    if linter == "black":
                        result = subprocess.run(
                            [linter, str(path)], capture_output=True, text=True, timeout=30
                        )
                        if result.returncode == 0:
                            results.append(f"✅ {linter}: Code formatted successfully")
                        else:
                            results.append(f"❌ {linter}: {result.stderr}")

                    elif linter == "ruff":
                        result = subprocess.run(
                            [linter, "--fix", str(path)], capture_output=True, text=True, timeout=30
                        )
                        if result.returncode == 0:
                            results.append(f"✅ {linter}: Auto-fixes applied")
                        else:
                            results.append(f"❌ {linter}: {result.stderr}")

                    else:
                        results.append(f"⚠️ Auto-fix for '{linter}' not implemented yet")

                except subprocess.TimeoutExpired:
                    results.append(f"⏰ {linter}: Timeout")
                except FileNotFoundError:
                    results.append(f"❌ {linter}: Not installed")
                except Exception as e:
                    results.append(f"❌ {linter}: Error - {str(e)}")

            return f"## Auto-fix Results for {file_path}\n\n" + "\n\n".join(results)

        except Exception as e:
            return f"❌ Error fixing file '{file_path}': {str(e)}"

    async def lint_directory(self, directory: str) -> str:
        """Lint all files in a directory."""
        try:
            path = Path(directory)
            if not path.exists():
                return f"❌ Directory '{directory}' not found."

            if not path.is_dir():
                return f"❌ '{directory}' is not a directory."

            # Find all files to lint
            files_to_lint = []
            for file_path in path.rglob("*"):
                if file_path.is_file() and self._get_linters_for_file(file_path):
                    # Check if file should be excluded
                    should_exclude = False
                    for pattern in self.exclude_patterns:
                        if file_path.match(pattern):
                            should_exclude = True
                            break

                    if not should_exclude:
                        files_to_lint.append(file_path)

            if not files_to_lint:
                return f"📁 No lintable files found in '{directory}'"

            results = []
            for file_path in files_to_lint[:10]:  # Limit to first 10 files
                file_result = await self.lint_file(str(file_path))
                results.append(f"### {file_path.name}\n{file_result}")

            if len(files_to_lint) > 10:
                results.append(f"\n... and {len(files_to_lint) - 10} more files")

            return f"## Directory Linting Results for {directory}\n\n" + "\n\n".join(results)

        except Exception as e:
            return f"❌ Error linting directory '{directory}': {str(e)}"

    async def lint_sample_tool(self) -> str:
        """Lint a sample tool for demonstration."""
        sample_path = Path("./test_tools/calculator.py")
        if not sample_path.exists():
            return "❌ Sample tool not found at ./test_tools/calculator.py"

        return await self.lint_file(str(sample_path))

    async def fix_sample_tool(self) -> str:
        """Fix a sample tool for demonstration."""
        sample_path = Path("./test_tools/calculator.py")
        if not sample_path.exists():
            return "❌ Sample tool not found at ./test_tools/calculator.py"

        return await self.fix_file(str(sample_path))

    def get_status(self) -> str:
        """Get the status of the linting agent."""
        status = f"""## Linting Agent Status

**Auto-fix Enabled:** {self.auto_fix}
**Format on Save:** {self.format_on_save}
**Lint Directories:** {", ".join(str(d) for d in self.lint_directories)}
**Exclude Patterns:** {", ".join(self.exclude_patterns)}

**Available Linters:**
- **Python:** {", ".join(self.linters["python"])}
- **JavaScript:** {", ".join(self.linters["javascript"])}
- **Bash:** {", ".join(self.linters["bash"])}

**Recent Linting Activity:** {len(self.lint_history)} operations performed"""

        return status

    def check_linter_availability(self) -> str:
        """Check which linters are available on the system."""
        available = {}
        not_available = {}

        for language, linters in self.linters.items():
            available[language] = []
            not_available[language] = []

            for linter in linters:
                try:
                    result = subprocess.run(
                        [linter, "--version"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        available[language].append(linter)
                    else:
                        not_available[language].append(linter)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    not_available[language].append(linter)

        status = "## Linter Availability Check\n\n"

        for language, linters in available.items():
            if linters:
                status += f"**{language.title()}:** ✅ {', '.join(linters)}\n"

        status += "\n**Not Available:**\n"
        for language, linters in not_available.items():
            if linters:
                status += f"- {language.title()}: {', '.join(linters)}\n"

        return status


# Global linting manager
linting_manager = LintingManager()


@tool
async def lint_file(file_path: str) -> str:
    """Lint a specific file for code quality issues."""
    return await linting_manager.lint_file(file_path)


@tool
async def fix_file(file_path: str) -> str:
    """Auto-fix code quality issues in a specific file."""
    return await linting_manager.fix_file(file_path)


@tool
async def lint_directory(directory: str) -> str:
    """Lint all files in a directory."""
    return await linting_manager.lint_directory(directory)


@tool
async def lint_sample_tool() -> str:
    """Lint a sample tool for demonstration."""
    return await linting_manager.lint_sample_tool()


@tool
async def fix_sample_tool() -> str:
    """Fix a sample tool for demonstration."""
    return await linting_manager.fix_sample_tool()


@tool
async def get_linting_status() -> str:
    """Get the current status of the linting agent."""
    return linting_manager.get_status()


@tool
async def check_linter_availability() -> str:
    """Check which linters are available on the system."""
    return linting_manager.check_linter_availability()


# Create the Linting agent using OpenAI Agents SDK
linting_agent = Agent(
    name="Linting Agent",
    instructions="""You are the Vectras Linting Agent. You help with code quality checks and formatting.

Your capabilities include:
- Linting specific files for code quality issues
- Auto-fixing code formatting and style issues
- Linting entire directories
- Checking linter availability
- Providing status information about the linting environment

When users ask for status, provide a comprehensive overview of the linting setup.
When users want to lint files, run the appropriate linters and report issues clearly.
When users want to fix files, apply auto-fixes and report the results.

You can use the following tools to perform linting operations:
- lint_file: Lint a specific file for code quality issues
- fix_file: Auto-fix code quality issues in a specific file
- lint_directory: Lint all files in a directory
- lint_sample_tool: Lint a sample tool for demonstration
- fix_sample_tool: Fix a sample tool for demonstration
- get_linting_status: Get comprehensive linting agent status
- check_linter_availability: Check which linters are available on the system

If a user asks about something outside your capabilities (like GitHub operations, testing, or code analysis), you can suggest they ask the appropriate agent:
- For GitHub operations: Ask the GitHub Agent
- For testing: Ask the Testing Agent
- For code analysis and fixes: Ask the Coding Agent
- For log monitoring: Ask the Logging Monitor Agent
- For project coordination: Ask the Supervisor Agent

Format your responses in markdown for better readability.""",
    tools=[
        lint_file,
        fix_file,
        lint_directory,
        lint_sample_tool,
        fix_sample_tool,
        get_linting_status,
        check_linter_availability,
    ],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras Linting Agent",
    description="Code quality and formatting agent",
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
    agent_id: str = "linting"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        print(f"DEBUG: Linting agent received query: {request.query[:100]}...")

        # Run the agent using the SDK
        result = await Runner.run(linting_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "linting", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Code Linting", "Auto-fixing", "Quality Checks"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        print(f"Error in Linting agent: {str(e)}")
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "linting-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "Linting Agent",
        "status": "active",
        "auto_fix": linting_manager.auto_fix,
        "sdk_version": "openai-agents",
        "tools": [
            "lint_file",
            "fix_file",
            "lint_directory",
            "lint_sample_tool",
            "fix_sample_tool",
            "get_linting_status",
            "check_linter_availability",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8127)
