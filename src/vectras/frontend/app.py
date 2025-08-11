# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
from pathlib import Path

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
                            "log-monitor": 8124,
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


