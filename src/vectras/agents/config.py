# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Configuration loading and management for Vectras agents."""

from pathlib import Path
from typing import List, Optional

import os
import re
import yaml
from pydantic import BaseModel, Field

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    pass  # dotenv not available, continue without it


class AgentSettings(BaseModel):
    """Base agent settings from config."""

    project_root: Optional[str] = None
    user_settings_file: Optional[str] = None
    handoff_timeout: Optional[int] = 30
    log_directory: Optional[str] = None
    monitor_interval: Optional[int] = 5
    error_patterns: Optional[List[str]] = None
    max_log_size: Optional[str] = None
    github_enabled: Optional[bool] = False
    github_token_env: Optional[str] = None
    branch_prefix: Optional[str] = None
    pr_labels: Optional[List[str]] = None

    # Testing agent specific settings
    test_tools_directory: Optional[str] = None
    bug_severity_levels: Optional[List[str]] = None
    supported_languages: Optional[List[str]] = None
    integration_test_path: Optional[str] = None
    enable_bug_injection: Optional[bool] = None

    # Code fixer specific settings
    linting_agent_port: Optional[int] = None
    auto_lint_fixes: Optional[bool] = None

    # Linting agent specific settings
    linters: Optional[dict] = None
    auto_fix: Optional[bool] = None
    format_on_save: Optional[bool] = None
    lint_directories: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None

    # GitHub agent specific settings
    github_token: Optional[str] = None
    github_org: Optional[str] = None
    github_repo: Optional[str] = None
    github_branch: Optional[str] = None
    github_branch_prefix: Optional[str] = None
    github_pr_template: Optional[str] = None
    github_auto_merge: Optional[bool] = None


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    id: str
    name: str
    description: str
    enabled: bool = True
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 1000
    system_prompt: str
    capabilities: List[str] = Field(default_factory=list)
    endpoint: str = "/query"
    port: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    settings: AgentSettings = Field(default_factory=AgentSettings)


class GlobalSettings(BaseModel):
    """Global settings for all agents."""

    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.2
    default_max_tokens: int = 1000
    api_timeout: int = 30
    enable_logging: bool = True


class VectrasConfig(BaseModel):
    """Complete Vectras configuration."""

    agents: List[AgentConfig] = Field(default_factory=list)
    settings: GlobalSettings = Field(default_factory=GlobalSettings)


def _substitute_env_vars(obj):
    """Recursively substitute environment variables in configuration values."""
    if isinstance(obj, dict):
        return {key: _substitute_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Replace ${VAR_NAME} with environment variable values
        def replace_env_var(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is not None:
                print(f"🔧 Substituting ${var_name} with: {env_value[:10] if len(env_value) > 10 else env_value}...")
                return env_value
            else:
                print(f"⚠️ Environment variable {var_name} not found, keeping original: {match.group(0)}")
                return match.group(0)  # Return original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, obj)
    else:
        return obj

def load_config(config_path: Optional[str] = None) -> VectrasConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        # Try to find config.yaml relative to this file
        current_dir = Path(__file__).parent
        config_path = current_dir.parent.parent.parent / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    # Substitute environment variables
    config_data = _substitute_env_vars(config_data)

    return VectrasConfig(**config_data)


def get_agent_config(
    agent_id: str, config: Optional[VectrasConfig] = None
) -> Optional[AgentConfig]:
    """Get configuration for a specific agent."""
    if config is None:
        config = load_config()

    for agent in config.agents:
        if agent.id == agent_id:
            return agent

    return None


def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from this file and walk up to find the project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.parent
    return project_root.resolve()


def get_logs_directory() -> Path:
    """Get the logs directory path."""
    return get_project_root() / "logs"


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
