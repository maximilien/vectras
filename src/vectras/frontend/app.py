# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
from pathlib import Path

import httpx
import yaml
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _is_sensitive_field(key: str, value: any) -> bool:
    """Check if a field contains sensitive information that should not be exposed."""
    key_lower = key.lower()
    sensitive_keywords = [
        'token', 'key', 'password', 'secret', 'credential', 
        'api_key', 'auth', 'github_token', 'openai_key'
    ]
    
    # Check if key contains sensitive keywords
    if any(keyword in key_lower for keyword in sensitive_keywords):
        return True
    
    # Check if value looks like a token/key (long alphanumeric strings)
    if isinstance(value, str) and len(value) > 20 and value.replace('-', '').replace('_', '').isalnum():
        return True
    
    return False


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras UI", description="Static UI for Vectras", version="0.1.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve the frontend directory
    root_dir = Path(__file__).resolve().parents[3]
    frontend_dir = root_dir / "frontend"
    static_dir = frontend_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    async def health():
        """Health check endpoint for the UI service."""
        return {"status": "ok", "service": "ui"}

    index_path = frontend_dir / "index.html"

    @app.get("/")
    async def index() -> Response:
        if index_path.exists():
            # Read the HTML file and inject the application title
            with open(index_path, "r") as f:
                html_content = f.read()
            
            # Get application title from environment or use default
            app_title = os.getenv("APPLICATION_TITLE", "Vectras AI Assistant")
            
            # Inject the title as a global variable
            html_content = html_content.replace(
                '</head>',
                f'<script>window.APP_TITLE = "{app_title}";</script></head>'
            )
            
            return Response(html_content, media_type="text/html")
        return Response("<h1>Vectras UI</h1><p>index.html missing.</p>", media_type="text/html")

    @app.get("/api/agents")
    async def get_agents():
        """Get agent configurations from config.yaml."""
        try:
            config_path = root_dir / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                
                # Filter out disabled agents and add only safe, public info
                agents = []
                for agent in config.get("agents", []):
                    if agent.get("enabled", True):
                        # Start with safe, whitelisted fields only
                        safe_fields = {
                            "id": agent.get("id"),
                            "name": agent.get("name"), 
                            "description": agent.get("description"),
                            "capabilities": agent.get("capabilities", []),
                            "tags": agent.get("tags", []),
                            "endpoint": agent.get("endpoint", "/query")
                        }
                        
                        # Double-check: filter out any potentially sensitive data
                        agent_info = {}
                        for key, value in safe_fields.items():
                            if not _is_sensitive_field(key, value):
                                agent_info[key] = value
                        
                        # Add port mapping for different agents
                        port_mapping = {
                            "supervisor": 8123,
                            "logging-monitor": 8124,
                            "coding": 8125,
                            "linting": 8127,
                            "testing": 8126,
                            "github": 8128
                        }
                        agent_info["port"] = port_mapping.get(agent.get("id"), 8123)
                        agents.append(agent_info)
                
                return {"agents": agents}
            else:
                return {"agents": []}
        except Exception as e:
            return {"agents": [], "error": str(e)}

    @app.get("/api/agents-statuses")
    async def get_agents_statuses():
        """Get status information for all agents."""
        import httpx
        from datetime import datetime, timedelta
        
        agent_ports = {
            "supervisor": 8123,
            "logging-monitor": 8124,
            "coding": 8125,
            "linting": 8127,
            "testing": 8126,
            "github": 8128
        }
        
        status_data = {}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for agent_id, port in agent_ports.items():
                try:
                    # Get basic status
                    status_response = await client.get(f"http://localhost:{port}/status")
                    if status_response.status_code == 200:
                        status_info = status_response.json()
                        
                        # Get agent-specific status summary
                        status_summary = await get_agent_status_summary(agent_id, status_info, client)
                        status_data[agent_id] = status_summary
                    else:
                        status_data[agent_id] = {
                            "status": "offline",
                            "summary": "Offline ❌",
                            "details": f"HTTP {status_response.status_code}"
                        }
                except Exception as e:
                    status_data[agent_id] = {
                        "status": "offline",
                        "summary": "Offline ❌",
                        "details": str(e)
                    }
        
        return {"agents_statuses": status_data}

    async def get_agent_status_summary(agent_id: str, status_info: dict, client: httpx.AsyncClient) -> dict:
        """Get a summary status for a specific agent."""
        from datetime import datetime, timedelta
        
        try:
            if agent_id == "supervisor":
                # For supervisor, check other agents' health
                agent_ports = {
                    "supervisor": 8123,
                    "logging-monitor": 8124,
                    "coding": 8125,
                    "linting": 8127,
                    "testing": 8126,
                    "github": 8128
                }
                
                online_count = 0
                offline_count = 0
                
                for other_agent_id, port in agent_ports.items():
                    try:
                        health_response = await client.get(f"http://localhost:{port}/health", timeout=2.0)
                        if health_response.status_code == 200:
                            online_count += 1
                        else:
                            offline_count += 1
                    except:
                        offline_count += 1
                
                if offline_count == 0:
                    summary = f"{online_count} agents ✅"
                else:
                    summary = f"{online_count} agents ✅ {offline_count} agents ❌"
                    
            elif agent_id == "logging-monitor":
                # Get error count from recent logs
                error_count = status_info.get("error_count", 0)
                summary = f"{error_count} errors (last hour)"
                
            elif agent_id == "coding":
                # Get recent analysis count
                recent_activities = status_info.get("recent_activities", [])
                analysis_count = sum(1 for activity in recent_activities 
                                   if "analysis" in activity.get("activity", "").lower())
                fixes_count = sum(1 for activity in recent_activities 
                                if "fix" in activity.get("activity", "").lower())
                
                if analysis_count > 0 or fixes_count > 0:
                    summary = f"{analysis_count} analysis, {fixes_count} fixes (last day)"
                else:
                    summary = "No recent activity"
                    
            elif agent_id == "linting":
                # Get files linted count
                recent_activities = status_info.get("recent_activities", [])
                files_linted = sum(1 for activity in recent_activities 
                                 if "lint" in activity.get("activity", "").lower())
                
                if files_linted > 0:
                    summary = f"{files_linted} files fixed (today)"
                else:
                    summary = "No files linted today"
                    
            elif agent_id == "testing":
                # Get test results
                recent_activities = status_info.get("recent_activities", [])
                tests_passed = sum(1 for activity in recent_activities 
                                 if "test" in activity.get("activity", "").lower() 
                                 and "pass" in activity.get("activity", "").lower())
                tests_failed = sum(1 for activity in recent_activities 
                                 if "test" in activity.get("activity", "").lower() 
                                 and "fail" in activity.get("activity", "").lower())
                
                if tests_passed > 0 or tests_failed > 0:
                    summary = f"{tests_passed + tests_failed} tests ✅ (today)"
                else:
                    summary = "No tests run today"
                    
            elif agent_id == "github":
                # Get PR count
                recent_activities = status_info.get("recent_activities", [])
                pr_count = sum(1 for activity in recent_activities 
                              if "pr" in activity.get("activity", "").lower() 
                              or "pull request" in activity.get("activity", "").lower())
                
                if pr_count > 0:
                    summary = f"{pr_count} PRs 📤 (today)"
                else:
                    summary = "No PRs today"
                    
            else:
                summary = "Active"
                
            return {
                "status": "active",
                "summary": summary,
                "details": status_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "summary": "Error getting status",
                "details": str(e)
            }

    @app.get("/api/config")
    async def get_config():
        """Get full configuration from config.yaml."""
        try:
            config_path = root_dir / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                
                # Return safe configuration data
                safe_config = {
                    "default_queries": config.get("default_queries", []),
                    "settings": config.get("settings", {}),
                    "agents": []
                }
                
                # Add agents with full configuration (excluding sensitive data)
                for agent in config.get("agents", []):
                    # Create a copy of the agent config
                    agent_config = agent.copy()
                    
                    # Remove or mask sensitive fields
                    sensitive_fields = ['system_prompt']  # Add more if needed
                    for field in sensitive_fields:
                        if field in agent_config:
                            agent_config[field] = "[REDACTED]"
                    
                    # Check for sensitive values in all fields
                    for key, value in list(agent_config.items()):
                        if _is_sensitive_field(key, value):
                            agent_config[key] = "[REDACTED]"
                    
                    safe_config["agents"].append(agent_config)
                
                return safe_config
            else:
                return {
                    "default_queries": ["status", "latest actions", "up time"],
                    "settings": {},
                    "agents": []
                }
        except Exception as e:
            return {
                "default_queries": ["status", "latest actions", "up time"],
                "settings": {},
                "agents": [],
                "error": str(e)
            }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_UI_HOST", "localhost")
    port = int(os.getenv("VECTRAS_UI_PORT", "8120"))
    uvicorn.run(app, host=host, port=port)


