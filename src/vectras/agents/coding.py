"""
Coding Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import ast
import re
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


class CodeAnalysis:
    """Represents code analysis results."""

    def __init__(self, file_path: str, error_content: str, analysis: str, suggested_fix: str):
        self.file_path = file_path
        self.error_content = error_content
        self.analysis = analysis
        self.suggested_fix = suggested_fix
        self.timestamp = datetime.now()
        self.severity = self._assess_severity(error_content)
        self.confidence = self._assess_confidence(analysis)

    def _assess_severity(self, error_content: str) -> str:
        """Assess the severity of the error."""
        high_severity_patterns = [
            "fatal",
            "critical",
            "syntaxerror",
            "importerror",
            "modulenotfound",
        ]
        medium_severity_patterns = ["attributeerror", "typeerror", "valueerror", "keyerror"]

        content_lower = error_content.lower()

        if any(pattern in content_lower for pattern in high_severity_patterns):
            return "high"
        elif any(pattern in content_lower for pattern in medium_severity_patterns):
            return "medium"
        else:
            return "low"

    def _assess_confidence(self, analysis: str) -> str:
        """Assess confidence in the analysis."""
        if len(analysis) > 200 and ("specific" in analysis.lower() or "line" in analysis.lower()):
            return "high"
        elif len(analysis) > 100:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "error_content": self.error_content,
            "analysis": self.analysis,
            "suggested_fix": self.suggested_fix,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "confidence": self.confidence,
        }


class CodeFixerManager:
    """Manages code analysis and fixing operations."""

    def __init__(self):
        self.project_root = Path(".")
        self.analyses: List[CodeAnalysis] = []
        self.fix_history = []

    def _extract_file_path(self, error_content: str) -> Optional[str]:
        """Extract file path from error content."""
        # Common patterns for file paths in error messages
        patterns = [
            r'File "([^"]+)"',
            r"File \'([^\']+)\'",
            r"at ([^\s]+\.py)",
            r"in ([^\s]+\.py)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_content)
            if match:
                return match.group(1)
        return None

    def _extract_line_number(self, error_content: str) -> Optional[int]:
        """Extract line number from error content."""
        patterns = [
            r"line (\d+)",
            r"line (\d+),",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_content)
            if match:
                return int(match.group(1))
        return None

    def _read_file_content(self, file_path: str) -> str:
        """Read file content safely."""
        try:
            full_path = self.project_root / file_path
            if full_path.exists() and full_path.is_file():
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        return ""

    def _validate_python_syntax(self, code: str) -> Dict[str, Any]:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return {"valid": True, "errors": []}
        except SyntaxError as e:
            return {
                "valid": False,
                "errors": [
                    {"type": "SyntaxError", "message": str(e), "line": e.lineno, "column": e.offset}
                ],
            }
        except Exception as e:
            return {"valid": False, "errors": [{"type": "Error", "message": str(e)}]}

    async def analyze_code(self, file_path: str) -> str:
        """Analyze code in a file for potential issues."""
        try:
            content = self._read_file_content(file_path)
            if not content:
                return f"❌ Could not read file '{file_path}'"

            # Basic syntax validation
            syntax_result = self._validate_python_syntax(content)

            # Look for common issues
            issues = []

            # Check for common patterns
            if "import *" in content:
                issues.append("⚠️ Wildcard imports detected - consider specific imports")

            if "print(" in content and "logging" not in content:
                issues.append("⚠️ Print statements detected - consider using logging")

            if "except:" in content:
                issues.append("⚠️ Bare except clauses detected - specify exception types")

            if "def " in content and "->" not in content:
                issues.append("⚠️ Functions without type hints detected")

            # Check for potential bugs
            if "n1 / 0" in content:
                issues.append("🐛 **CRITICAL**: Division by zero detected!")

            if "result = n1 / 0" in content:
                issues.append("🐛 **CRITICAL**: Division by zero bug found!")

            analysis = f"""## Code Analysis for {file_path}

**Syntax Validation:** {"✅ Valid" if syntax_result["valid"] else "❌ Invalid"}

**Issues Found:** {len(issues)}
"""

            if syntax_result["errors"]:
                analysis += "\n**Syntax Errors:**\n"
                for error in syntax_result["errors"]:
                    analysis += f"- Line {error.get('line', '?')}: {error['message']}\n"

            if issues:
                analysis += "\n**Code Quality Issues:**\n"
                for issue in issues:
                    analysis += f"- {issue}\n"
            else:
                analysis += "\n✅ No major issues detected"

            return analysis

        except Exception as e:
            return f"❌ Error analyzing code: {str(e)}"

    async def analyze_error(self, error_content: str, file_path: Optional[str] = None) -> str:
        """Analyze an error and suggest a fix."""
        try:
            # Extract file path from error content if not provided
            if not file_path:
                file_path = self._extract_file_path(error_content)

            # Extract line number
            line_number = self._extract_line_number(error_content)

            # Read file content if available
            file_content = ""
            if file_path:
                file_content = self._read_file_content(file_path)

            # Analyze the error
            analysis = f"""## Error Analysis

**Error:** {error_content}
**File:** {file_path or "Unknown"}
**Line:** {line_number or "Unknown"}

**Analysis:**"""

            # Provide specific analysis based on error type
            error_lower = error_content.lower()

            if "division by zero" in error_lower or "zerodivisionerror" in error_lower:
                analysis += """
This is a division by zero error. The code is trying to divide by 0, which is mathematically undefined.

**Root Cause:** The divisor is 0 instead of the intended value.

**Suggested Fix:** Change the divisor from 0 to the correct variable."""

                if file_content and "n1 / 0" in file_content:
                    analysis += """

**Specific Fix:**
```python
# Change this line:
result = n1 / 0

# To this:
result = n1 / n2
```"""

            elif "syntaxerror" in error_lower:
                analysis += """
This is a syntax error indicating invalid Python code structure.

**Common Causes:**
- Missing colons after function/class definitions
- Unmatched parentheses or brackets
- Invalid indentation
- Missing quotes in strings

**Suggested Fix:** Review the code around the error line for syntax issues."""

            elif "importerror" in error_lower or "modulenotfound" in error_lower:
                analysis += """
This is an import error indicating a missing or incorrectly named module.

**Common Causes:**
- Module not installed
- Incorrect module name
- Wrong import path
- Missing __init__.py file

**Suggested Fix:** Install the missing module or correct the import statement."""

            else:
                analysis += """
This appears to be a runtime error. The code is syntactically correct but fails during execution.

**Suggested Fix:** Review the error message and check the logic around the error location."""

            # Create analysis object
            code_analysis = CodeAnalysis(
                file_path=file_path or "Unknown",
                error_content=error_content,
                analysis=analysis,
                suggested_fix="See analysis above",
            )

            self.analyses.append(code_analysis)

            return analysis

        except Exception as e:
            return f"❌ Error analyzing error: {str(e)}"

    async def fix_code(self, file_path: str, fix_description: str) -> str:
        """Apply a fix to a file."""
        try:
            content = self._read_file_content(file_path)
            if not content:
                return f"❌ Could not read file '{file_path}'"

            # Apply specific fixes based on description

            if "division by zero" in fix_description.lower():
                # Fix the divide by zero bug
                content = content.replace("n1 / 0", "n1 / n2")
                content = content.replace("result = n1 / 0", "result = n1 / n2")

            if "import" in fix_description.lower() and "wildcard" in fix_description.lower():
                # Replace wildcard imports with specific imports
                content = re.sub(
                    r"from \w+ import \*", "# TODO: Replace with specific imports", content
                )

            if "print" in fix_description.lower() and "logging" in fix_description.lower():
                # Replace print statements with logging
                content = re.sub(r"print\(", "logging.info(", content)

            # Validate the fixed code
            syntax_result = self._validate_python_syntax(content)

            if not syntax_result["valid"]:
                return f"❌ Fix would create syntax errors:\n{syntax_result['errors']}"

            # Save the fixed code
            full_path = self.project_root / file_path
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)

                self.fix_history.append(
                    {
                        "file_path": file_path,
                        "timestamp": datetime.now(),
                        "description": fix_description,
                    }
                )

                return f"✅ Successfully applied fix to '{file_path}'\n\n**Changes:**\n{fix_description}"

            except Exception as e:
                return f"❌ Error saving fixed file: {str(e)}"

        except Exception as e:
            return f"❌ Error fixing code: {str(e)}"

    async def fix_sample_tool(self) -> str:
        """Fix a sample tool for demonstration."""
        sample_path = "test_tools/calculator.py"
        return await self.fix_code(sample_path, "Fix any issues found in the sample tool")

    def get_status(self) -> str:
        """Get the status of the coding agent."""
        total_analyses = len(self.analyses)
        total_fixes = len(self.fix_history)

        # Count issues by severity
        high_severity = sum(1 for a in self.analyses if a.severity == "high")
        medium_severity = sum(1 for a in self.analyses if a.severity == "medium")
        low_severity = sum(1 for a in self.analyses if a.severity == "low")

        status = f"""## Coding Agent Status

**Total Analyses:** {total_analyses}
**Total Fixes Applied:** {total_fixes}

**Issues by Severity:**
- **High:** {high_severity}
- **Medium:** {medium_severity}
- **Low:** {low_severity}

**Recent Fixes:**"""

        # Show recent fixes
        recent_fixes = sorted(self.fix_history, key=lambda x: x["timestamp"], reverse=True)[:5]
        for fix in recent_fixes:
            status += f"\n- **{fix['file_path']}** - {fix['description']}"

        return status

    def get_recent_analyses(self) -> str:
        """Get recent code analyses."""
        if not self.analyses:
            return "📋 No analyses performed yet."

        status = "## Recent Code Analyses\n\n"

        recent_analyses = sorted(self.analyses, key=lambda x: x.timestamp, reverse=True)[:5]
        for analysis in recent_analyses:
            status += f"### {analysis.file_path}\n"
            status += f"**Severity:** {analysis.severity.title()}\n"
            status += f"**Confidence:** {analysis.confidence.title()}\n"
            status += f"**Timestamp:** {analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        return status


# Global coding manager
code_fixer_manager = CodeFixerManager()


@tool
async def analyze_code(file_path: str) -> str:
    """Analyze code in a file for potential issues."""
    return await code_fixer_manager.analyze_code(file_path)


@tool
async def analyze_error(error_content: str, file_path: Optional[str] = None) -> str:
    """Analyze an error and suggest a fix."""
    return await code_fixer_manager.analyze_error(error_content, file_path)


@tool
async def fix_code(file_path: str, fix_description: str) -> str:
    """Apply a fix to a file."""
    return await code_fixer_manager.fix_code(file_path, fix_description)


@tool
async def fix_sample_tool() -> str:
    """Fix a sample tool for demonstration."""
    return await code_fixer_manager.fix_sample_tool()


@tool
async def get_code_fixer_status() -> str:
    """Get the current status of the coding agent."""
    return code_fixer_manager.get_status()


@tool
async def get_recent_analyses() -> str:
    """Get recent code analyses."""
    return code_fixer_manager.get_recent_analyses()


# Create the Coding agent using OpenAI Agents SDK
code_fixer_agent = Agent(
    name="Coding Agent",
    instructions="""You are the Vectras Coding Agent. You help analyze code issues and apply fixes.

Your capabilities include:
- Analyzing code files for potential issues
- Analyzing error messages and suggesting fixes
- Applying automatic fixes to code files
- Providing status information about code analysis activities

When users ask for status, provide a comprehensive overview of analyses and fixes.
When users want to analyze code, examine the file for issues and report findings.
When users want to fix code, apply the appropriate fixes and report the results.

You can use the following tools to perform code analysis and fixing operations:
- analyze_code: Analyze a file for potential issues
- analyze_error: Analyze an error message and suggest fixes
- fix_code: Apply a fix to a file
- fix_sample_tool: Fix a sample tool for demonstration
- get_code_fixer_status: Get comprehensive coding agent status
- get_recent_analyses: Get recent code analyses

If a user asks about something outside your capabilities (like GitHub operations, testing, or linting), you can suggest they ask the appropriate agent:
- For GitHub operations: Ask the GitHub Agent
- For testing: Ask the Testing Agent
- For code quality and formatting: Ask the Linting Agent
- For log monitoring: Ask the Logging Monitor Agent
- For project coordination: Ask the Supervisor Agent

Format your responses in markdown for better readability.""",
    tools=[
        analyze_code,
        analyze_error,
        fix_code,
        fix_sample_tool,
        get_code_fixer_status,
        get_recent_analyses,
    ],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras Coding Agent",
    description="Code analysis and fixing agent",
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
    agent_id: str = "coding"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        print(f"DEBUG: Coding agent received query: {request.query[:100]}...")

        # Run the agent using the SDK
        result = await Runner.run(code_fixer_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "coding", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Code Analysis", "Error Fixing", "Bug Detection"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        print(f"Error in Coding agent: {str(e)}")
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "coding-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "Coding Agent",
        "status": "active",
        "analyses_count": len(code_fixer_manager.analyses),
        "fixes_count": len(code_fixer_manager.fix_history),
        "sdk_version": "openai-agents",
        "tools": [
            "analyze_code",
            "analyze_error",
            "fix_code",
            "fix_sample_tool",
            "get_code_fixer_status",
            "get_recent_analyses",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8125)
