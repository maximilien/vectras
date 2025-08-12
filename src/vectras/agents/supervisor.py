"""
Supervisor Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import yaml

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.tool import function_tool as tool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .base_agent import determine_response_type_with_llm


class SupervisorManager:
    """Manages supervisor operations and project coordination."""

    def __init__(self):
        self.project_root = Path(".")
        self.user_settings_path = self.project_root / "config" / "user_settings.yaml"
        self.user_settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.agent_endpoints = {
            "github": "http://127.0.0.1:8129",
            "testing": "http://127.0.0.1:8126",
            "linting": "http://127.0.0.1:8127",
            "coding": "http://127.0.0.1:8125",
            "logging-monitor": "http://127.0.0.1:8124",
        }

    async def get_project_files(self, pattern: str = "*", limit: int = 100) -> str:
        """Get list of project files matching pattern."""
        try:
            if pattern == "*":
                # Get common project files
                files = []
                for ext in [".py", ".yaml", ".yml", ".json", ".md", ".txt", ".sh"]:
                    files.extend(
                        [
                            str(p.relative_to(self.project_root))
                            for p in self.project_root.rglob(f"*{ext}")
                            if not any(part.startswith(".") for part in p.parts)
                            and "logs" not in p.parts
                            and "__pycache__" not in str(p)
                        ]
                    )
                files = sorted(set(files))[:limit]
            else:
                files = [
                    str(p.relative_to(self.project_root)) for p in self.project_root.glob(pattern)
                ][:limit]

            status = f"""## Project Files

**Pattern:** {pattern}
**Files Found:** {len(files)}
**Limit:** {limit}

**Files:**"""

            for file in files:
                status += f"\n- {file}"

            return status

        except Exception as e:
            return f"❌ Error getting project files: {str(e)}"

    async def read_file(self, file_path: str) -> str:
        """Read contents of a project file."""
        try:
            full_path = self.project_root / file_path
            if not full_path.exists() or not full_path.is_file():
                return f"❌ File '{file_path}' not found."

            # Security check: ensure file is within project
            if not str(full_path.resolve()).startswith(str(self.project_root.resolve())):
                return f"❌ Access denied: File '{file_path}' is outside project directory."

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return f"""## File Contents: {file_path}

**Size:** {len(content)} characters

```{self._get_file_extension(file_path)}
{content}
```"""

        except Exception as e:
            return f"❌ Error reading file '{file_path}': {str(e)}"

    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension for syntax highlighting."""
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            return "python"
        elif ext in [".yaml", ".yml"]:
            return "yaml"
        elif ext == ".json":
            return "json"
        elif ext == ".md":
            return "markdown"
        elif ext == ".sh":
            return "bash"
        else:
            return "text"

    async def get_user_settings(self) -> str:
        """Get user settings from config file."""
        try:
            if self.user_settings_path.exists():
                with open(self.user_settings_path, "r") as f:
                    settings = yaml.safe_load(f) or {}
            else:
                settings = {}

            # Add some defaults
            defaults = {
                "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "project_name": self.project_root.name,
                "last_activity": None,
            }

            for key, value in defaults.items():
                if key not in settings:
                    settings[key] = value

            status = f"""## User Settings

**Settings File:** {self.user_settings_path}

**Current Settings:**"""

            for key, value in settings.items():
                status += f"\n- **{key}:** {value}"

            return status

        except Exception as e:
            return f"❌ Error getting user settings: {str(e)}"

    async def update_user_settings(self, updates: Dict[str, Any]) -> str:
        """Update user settings."""
        try:
            # Load current settings
            if self.user_settings_path.exists():
                with open(self.user_settings_path, "r") as f:
                    settings = yaml.safe_load(f) or {}
            else:
                settings = {}

            # Apply updates
            settings.update(updates)

            # Save settings
            with open(self.user_settings_path, "w") as f:
                yaml.dump(settings, f, default_flow_style=False)

            status = """## Settings Updated

**Updated Settings:**"""

            for key, value in updates.items():
                status += f"\n- **{key}:** {value}"

            return status

        except Exception as e:
            return f"❌ Error updating user settings: {str(e)}"

    async def check_agent_health(self) -> str:
        """Check health of all agents."""
        try:
            health_status = {}

            for agent_name, endpoint in self.agent_endpoints.items():
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        response = await client.get(f"{endpoint}/health")
                        if response.status_code == 200:
                            health_status[agent_name] = "✅ Healthy"
                        else:
                            health_status[agent_name] = f"❌ HTTP {response.status_code}"
                except Exception as e:
                    # In CI environment, agents might not be running, so be more graceful
                    if "Connection refused" in str(e) or "timeout" in str(e).lower():
                        health_status[agent_name] = "⚠️ Not running (expected in CI)"
                    else:
                        health_status[agent_name] = f"❌ Error: {str(e)}"

            status = f"""## Agent Health Check

**Checked at:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Agent Status:**"""

            for agent_name, health in health_status.items():
                status += f"\n- **{agent_name}:** {health}"

            return status

        except Exception as e:
            return f"❌ Error checking agent health: {str(e)}"

    async def get_agent_status(self) -> str:
        """Get detailed status from all agents."""
        try:
            status_info = {}

            for agent_name, endpoint in self.agent_endpoints.items():
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        response = await client.get(f"{endpoint}/status")
                        if response.status_code == 200:
                            status_info[agent_name] = response.json()
                        else:
                            status_info[agent_name] = {"error": f"HTTP {response.status_code}"}
                except Exception as e:
                    # In CI environment, agents might not be running, so be more graceful
                    if "Connection refused" in str(e) or "timeout" in str(e).lower():
                        status_info[agent_name] = {"status": "Not running (expected in CI)"}
                    else:
                        status_info[agent_name] = {"error": str(e)}

            status = f"""## Agent Status Report

**Generated at:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**Agent Details:**"""

            for agent_name, info in status_info.items():
                status += f"\n\n### {agent_name.title()} Agent"

                if "error" in info:
                    status += f"\n❌ **Error:** {info['error']}"
                else:
                    for key, value in info.items():
                        if key != "agent":  # Skip redundant agent name
                            status += f"\n- **{key}:** {value}"

            return status

        except Exception as e:
            return f"❌ Error getting agent status: {str(e)}"

    async def get_project_summary(self) -> str:
        """Get a comprehensive project summary."""
        try:
            # Get project files
            files = []
            for ext in [".py", ".yaml", ".yml", ".json", ".md", ".txt", ".sh"]:
                files.extend(
                    [
                        str(p.relative_to(self.project_root))
                        for p in self.project_root.rglob(f"*{ext}")
                        if not any(part.startswith(".") for part in p.parts)
                        and "logs" not in p.parts
                        and "__pycache__" not in str(p)
                    ]
                )

            # Count files by type
            file_counts = {}
            for file in files:
                ext = Path(file).suffix.lower()
                file_counts[ext] = file_counts.get(ext, 0) + 1

            # Get settings
            settings = {}
            if self.user_settings_path.exists():
                with open(self.user_settings_path, "r") as f:
                    settings = yaml.safe_load(f) or {}

            status = f"""## Project Summary

**Project Name:** {self.project_root.name}
**Project Root:** {self.project_root.absolute()}
**Generated at:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

**File Statistics:**
- **Total Files:** {len(files)}"""

            for ext, count in sorted(file_counts.items()):
                status += f"\n- **{ext} files:** {count}"

            status += f"""

**Configuration:**
- **OpenAI Model:** {settings.get("openai_model", "Not set")}
- **Settings File:** {self.user_settings_path}"""

            return status

        except Exception as e:
            return f"❌ Error getting project summary: {str(e)}"

    def get_status(self) -> str:
        """Get the status of the supervisor agent."""
        status = f"""## Supervisor Agent Status

**Project Root:** {self.project_root.absolute()}
**Settings File:** {self.user_settings_path}
**Agent Endpoints:** {len(self.agent_endpoints)}

**Available Operations:**
- Get project files and file contents
- Manage user settings
- Check agent health and status
- Generate project summaries

**Agent Endpoints:**"""

        for agent_name, endpoint in self.agent_endpoints.items():
            status += f"\n- **{agent_name}:** {endpoint}"

        return status


# Global supervisor manager
supervisor_manager = SupervisorManager()


@tool
async def get_project_files(pattern: str = "*", limit: int = 100) -> str:
    """Get list of project files matching pattern."""
    return await supervisor_manager.get_project_files(pattern, limit)


@tool
async def read_file(file_path: str) -> str:
    """Read contents of a project file."""
    return await supervisor_manager.read_file(file_path)


@tool
async def get_user_settings() -> str:
    """Get user settings from config file."""
    return await supervisor_manager.get_user_settings()


@tool
async def update_user_settings(updates: str) -> str:
    """Update user settings. Provide updates as a JSON string."""
    import json

    try:
        updates_dict = json.loads(updates)
        return await supervisor_manager.update_user_settings(updates_dict)
    except json.JSONDecodeError:
        return "❌ Invalid JSON format. Please provide updates as a valid JSON string."


@tool
async def check_agent_health() -> str:
    """Check health of all agents."""
    return await supervisor_manager.check_agent_health()


@tool
async def get_agent_status() -> str:
    """Get detailed status from all agents."""
    return await supervisor_manager.get_agent_status()


@tool
async def get_project_summary() -> str:
    """Get a comprehensive project summary."""
    return await supervisor_manager.get_project_summary()


@tool
async def get_supervisor_status() -> str:
    """Get the current status of the supervisor agent."""
    return supervisor_manager.get_status()


# Create the Supervisor agent using OpenAI Agents SDK
supervisor_agent = Agent(
    name="Supervisor Agent",
    instructions="""You are the Vectras Supervisor Agent. You coordinate with other agents and manage project state.

Your capabilities include:
- Managing project files and file contents
- Managing user settings and configuration
- Checking health and status of other agents
- Generating project summaries
- Coordinating multi-agent workflows

When users ask for status, provide a comprehensive overview of the project and agent status.
When users want to see files, list them clearly with appropriate filtering.
When users want to check agent health, verify all agents are running properly.

You can use the following tools to perform project coordination operations:
- get_project_files: Get list of project files matching a pattern
- read_file: Read contents of a project file
- get_user_settings: Get user settings from config file
- update_user_settings: Update user settings
- check_agent_health: Check health of all agents
- get_agent_status: Get detailed status from all agents
- get_project_summary: Get comprehensive project summary
- get_supervisor_status: Get supervisor agent status

As the supervisor, you can help users understand which agent is best suited for their needs:
- For GitHub operations: The GitHub Agent handles branches, commits, and PRs
- For testing: The Testing Agent creates and runs test tools
- For code analysis and fixes: The Coding Agent analyzes errors and applies fixes
- For code quality and formatting: The Linting Agent handles code quality checks
- For log monitoring: The Logging Monitor Agent checks logs for errors

Format your responses in markdown for better readability.""",
    tools=[
        get_project_files,
        read_file,
        get_user_settings,
        update_user_settings,
        check_agent_health,
        get_agent_status,
        get_project_summary,
        get_supervisor_status,
    ],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras Supervisor Agent",
    description="Project coordination and management agent",
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
    agent_id: str = "supervisor"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        # Check if we're in fake OpenAI mode
        if os.getenv("VECTRAS_FAKE_OPENAI", "0") == "1":
            # Provide a mock response for testing
            fake_response = """## Backend Status Report

### Project Overview
The Vectras project is running successfully with all components operational.

### Agent Status
- **Supervisor Agent**: Active and coordinating project operations
- **GitHub Agent**: Available for repository management
- **Testing Agent**: Ready for test creation and execution
- **Coding Agent**: Available for code analysis and fixes
- **Linting Agent**: Ready for code quality checks
- **Logging Monitor Agent**: Monitoring system logs

### System Health
All backend services are running properly:
- API Service: Operational
- MCP Service: Operational
- Agent Services: All operational

### Project Status
The project is in a healthy state with all agents ready to handle user requests."""

            return QueryResponse(
                status="success",
                response=fake_response,
                timestamp=datetime.now(),
                metadata={
                    "model": "fake-openai",
                    "capabilities": ["Project Management", "Agent Coordination", "File Operations"],
                    "response_type": "markdown",
                    "sdk_version": "fake-mode",
                },
            )

        # Run the agent using the SDK
        result = await Runner.run(supervisor_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "supervisor", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Project Management", "Agent Coordination", "File Operations"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "supervisor-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "Supervisor Agent",
        "status": "active",
        "project_root": str(supervisor_manager.project_root),
        "sdk_version": "openai-agents",
        "tools": [
            "get_project_files",
            "read_file",
            "get_user_settings",
            "update_user_settings",
            "check_agent_health",
            "get_agent_status",
            "get_project_summary",
            "get_supervisor_status",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8123)
