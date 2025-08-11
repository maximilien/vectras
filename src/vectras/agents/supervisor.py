# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Supervisor Agent - Main coordinator agent."""

import os
from typing import Any, Dict, List, Optional

import httpx
import yaml

from .base_agent import BaseAgent
from .config import ensure_directory, get_project_root


class SupervisorAgent(BaseAgent):
    """Main supervisor agent that coordinates with other agents and manages project state."""

    def __init__(self):
        super().__init__("supervisor")
        self.project_root = get_project_root()
        self.user_settings_path = self.project_root / "config" / "user_settings.yaml"
        ensure_directory(self.user_settings_path.parent)

    async def get_project_files(self, pattern: str = "*", limit: int = 100) -> List[str]:
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

            self.log_activity("file_list", {"pattern": pattern, "count": len(files)})
            return files
        except Exception as e:
            self.log_activity("file_list_error", {"pattern": pattern, "error": str(e)})
            return []

    async def read_file(self, file_path: str) -> Optional[str]:
        """Read contents of a project file."""
        try:
            full_path = self.project_root / file_path
            if not full_path.exists() or not full_path.is_file():
                return None

            # Security check: ensure file is within project
            if not str(full_path.resolve()).startswith(str(self.project_root.resolve())):
                return None

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.log_activity("file_read", {"file": file_path, "size": len(content)})
            return content
        except Exception as e:
            self.log_activity("file_read_error", {"file": file_path, "error": str(e)})
            return None

    async def get_user_settings(self) -> Dict[str, Any]:
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

            return settings
        except Exception as e:
            self.log_activity("settings_error", {"error": str(e)})
            return {}

    async def update_user_settings(self, updates: Dict[str, Any]) -> bool:
        """Update user settings."""
        try:
            current_settings = await self.get_user_settings()
            current_settings.update(updates)

            with open(self.user_settings_path, "w") as f:
                yaml.dump(current_settings, f, default_flow_style=False)

            self.log_activity("settings_updated", {"keys": list(updates.keys())})
            return True
        except Exception as e:
            self.log_activity("settings_update_error", {"error": str(e)})
            return False

    async def check_services_health(self) -> Dict[str, Any]:
        """Check health of all Vectras services."""
        services = {
            "api": {"url": "http://localhost:8121/health", "status": "unknown"},
            "mcp": {"url": "http://localhost:8122/health", "status": "unknown"},
            "log_monitor": {"url": "http://localhost:8124/health", "status": "unknown"},
            "code_fixer": {"url": "http://localhost:8125/health", "status": "unknown"},
        }

        async with httpx.AsyncClient() as client:
            for service_name, service_info in services.items():
                try:
                    response = await client.get(service_info["url"], timeout=5.0)
                    if response.status_code == 200:
                        services[service_name]["status"] = "healthy"
                        services[service_name]["response"] = response.json()
                    else:
                        services[service_name]["status"] = "unhealthy"
                        services[service_name]["error"] = f"HTTP {response.status_code}"
                except Exception as e:
                    services[service_name]["status"] = "error"
                    services[service_name]["error"] = str(e)

        self.log_activity(
            "health_check", {"services": {k: v["status"] for k, v in services.items()}}
        )
        return services

    async def check_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check status of a specific agent."""
        agent_ports = {"log-monitor": 8124, "coding": 8125}

        port = agent_ports.get(agent_id)
        if not port:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/status", timeout=5.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process queries for the supervisor agent."""
        query_lower = query.lower()

        # Status and health checks
        if "status" in query_lower and "backend" in query_lower:
            return await self.check_services_health()

        if "status" in query_lower and "agent" in query_lower:
            if context and "agent_id" in context:
                return await self.check_agent_status(context["agent_id"])
            else:
                # Return status of all agents
                statuses = {}
                for agent_id in ["log-monitor", "coding"]:
                    statuses[agent_id] = await self.check_agent_status(agent_id)
                return statuses

        # File operations
        if "list files" in query_lower or "show files" in query_lower:
            pattern = context.get("pattern", "*") if context else "*"
            return await self.get_project_files(pattern)

        if "read file" in query_lower and context and "file_path" in context:
            return await self.read_file(context["file_path"])

        # Settings operations
        if "settings" in query_lower:
            if "update" in query_lower and context and "updates" in context:
                success = await self.update_user_settings(context["updates"])
                return {"success": success, "settings": await self.get_user_settings()}
            else:
                return await self.get_user_settings()

        # Handoff to other agents
        if "monitor logs" in query_lower or "check logs" in query_lower:
            return await self.handoff_to_agent("log-monitor", query, context)

        if "fix code" in query_lower or "analyze error" in query_lower:
            return await self.handoff_to_agent("coding", query, context)

        # Default LLM response with system context
        messages = [
            {
                "role": "system",
                "content": self.config.system_prompt
                + f"""
                
Current project: {self.project_root.name}
Available capabilities: {", ".join(self.config.capabilities)}
Other agents available: log-monitor, coding

I can help with:
- Checking system and agent status
- Managing user settings  
- Accessing project files
- Coordinating with other agents
- General assistance
""",
            },
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(messages)


# Create the agent instance
supervisor = SupervisorAgent()


def create_app():
    """Create FastAPI app for the supervisor agent."""
    return supervisor.create_app()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = supervisor.config.port or 8123
    uvicorn.run(app, host="0.0.0.0", port=port)
