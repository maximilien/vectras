# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Base agent class for all Vectras agents."""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

try:
    from openai_agents import SQLiteSession

    HAS_AGENTS_SDK = True
except ImportError:
    HAS_AGENTS_SDK = False
    SQLiteSession = None

from .config import get_agent_config


class QueryRequest(BaseModel):
    """Request model for agent queries."""

    query: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for agent queries."""

    status: str
    response: Any
    agent_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class AgentStatus(BaseModel):
    """Agent status information."""

    agent_id: str
    name: str
    status: str  # "active", "idle", "error", "disabled"
    uptime_seconds: float
    last_activity: datetime
    current_task: Optional[str] = None
    recent_activities: List[Dict[str, Any]] = []
    error_count: int = 0
    success_count: int = 0


class BaseAgent(ABC):
    """Base class for all Vectras agents."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.config = get_agent_config(agent_id)
        if not self.config:
            raise ValueError(f"No configuration found for agent: {agent_id}")

        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.current_task: Optional[str] = None
        self.recent_activities: List[Dict[str, Any]] = []
        self.error_count = 0
        self.success_count = 0
        self.status = "idle"

        # Initialize OpenAI client
        self._openai_client: Optional[AsyncOpenAI] = None

        # Initialize memory session if configured
        self._memory_session = None
        self._init_memory()

    @property
    def openai_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._openai_client is None:
            if not os.getenv("OPENAI_API_KEY") and os.getenv("VECTRAS_FAKE_OPENAI", "0") != "1":
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Either set VECTRAS_FAKE_OPENAI=1 for tests/development "
                    "or provide a valid OpenAI API key in your environment."
                )

            self._openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL") or None,
                organization=os.getenv("OPENAI_ORG_ID") or None,
            )
        return self._openai_client

    def _init_memory(self) -> None:
        """Initialize memory session if configured and agents SDK is available."""
        if not HAS_AGENTS_SDK:
            return

        memory_config = getattr(self.config, "memory", None)
        if not memory_config or not memory_config.get("enabled", False):
            return

        db_path = memory_config.get("database_path", f"./data/{self.agent_id}_memory.db")

        # Ensure the data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            self._memory_session = SQLiteSession(agent_id=self.agent_id, database_path=db_path)
        except Exception as e:
            # Log error but don't fail agent initialization
            self.recent_activities.append(
                {
                    "timestamp": datetime.now(),
                    "action": "memory_init_error",
                    "details": f"Failed to initialize memory: {str(e)}",
                }
            )

    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return AgentStatus(
            agent_id=self.agent_id,
            name=self.config.name,
            status=self.status,
            uptime_seconds=uptime,
            last_activity=self.last_activity,
            current_task=self.current_task,
            recent_activities=self.recent_activities[-10:],  # Last 10 activities
            error_count=self.error_count,
            success_count=self.success_count,
        )

    def log_activity(self, activity: str, details: Optional[Dict[str, Any]] = None):
        """Log an activity."""
        activity_entry = {
            "timestamp": datetime.now(),
            "activity": activity,
            "details": details or {},
        }
        self.recent_activities.append(activity_entry)
        # Keep only the last 50 activities
        if len(self.recent_activities) > 50:
            self.recent_activities = self.recent_activities[-50:]

        self.last_activity = datetime.now()

    async def llm_completion(
        self, messages: List[Dict[str, str]], session_id: Optional[str] = None, **kwargs
    ) -> str:
        """Get LLM completion with optional memory."""
        # Use fake response for testing
        if os.getenv("VECTRAS_FAKE_OPENAI", "0") == "1":
            user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")
            system_message = next(
                (msg["content"] for msg in messages if msg["role"] == "system"), ""
            )

            # Provide better fake responses for testing agent
            if self.agent_id == "testing":
                if (
                    "create a test tool" in system_message.lower()
                    or "tool creator" in system_message.lower()
                ):
                    return """Here's a test tool with a divide by zero bug:

```python
def divide(n1, n2):
    \"\"\"Divide n1 by n2. This function has a bug - it divides by 0 instead of n2.\"\"\"
    # BUG: This should be n2, not 0
    result = n1 / 0
    print(f"Result of {n1} / {n2} = {result}")
    return result
```

This tool has a high severity bug where it divides by 0 instead of the second parameter."""
                elif "integration test" in system_message.lower():
                    return """Here's an integration test for the agent system:

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_agent_coordination():
    \"\"\"Test that agents can coordinate and hand off tasks.\"\"\"
    # Test implementation would go here
    assert True
```"""

            # Provide better fake responses for other agents
            elif self.agent_id == "log-monitor":
                if "error" in user_message.lower() or "handoff" in user_message.lower():
                    return "Error detected in divide tool execution. Handing off to code-fixer agent for analysis and fix."
                return "Monitoring logs for errors and issues."
            elif self.agent_id == "code-fixer":
                if "divide" in user_message.lower() or "bug" in user_message.lower():
                    return """Fixed the divide tool bug:

```python
def divide(n1, n2):
    \"\"\"Divide n1 by n2. Fixed version.\"\"\"
    if n2 == 0:
        raise ValueError("Cannot divide by zero")
    result = n1 / n2
    print(f"Result of {n1} / {n2} = {result}")
    return result
```

The bug was fixed by changing the division from `n1 / 0` to `n1 / n2` and adding proper error handling."""
                return "Analyzing code for bugs and providing fixes."
            elif self.agent_id == "linting":
                if "lint" in user_message.lower() or "quality" in user_message.lower():
                    return "Code quality check passed. No linting issues found in the fixed divide tool."
                return "Performing code quality and linting checks."
            elif self.agent_id == "github":
                if "branch" in user_message.lower() or "pr" in user_message.lower():
                    return "Created branch 'fix-divide-tool-bug' and pull request #123 with the fix for the divide tool."
                return "Managing GitHub operations and pull requests."

            return f"[FAKE_OPENAI_RESPONSE] Agent {self.agent_id}: {user_message}"

        try:
            # If memory is available and agents SDK is present, use it
            if HAS_AGENTS_SDK and self._memory_session and session_id:
                # Import Runner here to avoid import issues if agents SDK is not available
                from openai_agents import Agent, Runner

                # Get the user message from the messages array
                user_message = next(
                    (msg["content"] for msg in messages if msg["role"] == "user"), ""
                )
                if not user_message:
                    raise ValueError("No user message found in messages array")

                # Create a simple agent wrapper for the agents SDK
                agent = Agent(
                    model=kwargs.get("model", self.config.model),
                    instructions=self.config.system_prompt,
                    temperature=kwargs.get("temperature", self.config.temperature),
                )

                # Use the session for memory-enabled conversation
                session = SQLiteSession(session_id, self._memory_session._database_path)
                result = await Runner.run(agent, user_message, session=session)

                return result or ""
            else:
                # Fallback to standard OpenAI API without memory
                completion = await self.openai_client.chat.completions.create(
                    model=kwargs.get("model", self.config.model),
                    messages=messages,
                    temperature=kwargs.get("temperature", self.config.temperature),
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    **{
                        k: v
                        for k, v in kwargs.items()
                        if k not in ["model", "temperature", "max_tokens", "session_id"]
                    },
                )
                return completion.choices[0].message.content or ""

        except Exception as e:
            self.error_count += 1
            self.log_activity("llm_error", {"error": str(e)})
            raise

    async def handoff_to_agent(
        self, target_agent_id: str, query: str, context: Optional[Dict[str, Any]] = None
    ) -> QueryResponse:
        """Hand off a task to another agent."""
        try:
            # Get target agent config to find its port
            target_config = get_agent_config(target_agent_id)
            if not target_config or not target_config.port:
                raise ValueError(
                    f"Target agent {target_agent_id} not found or has no port configured"
                )

            url = f"http://localhost:{target_config.port}/query"
            request_data = {"query": query, "context": context or {}}

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=request_data, timeout=self.config.settings.handoff_timeout or 30
                )
                response.raise_for_status()

                self.log_activity(
                    "handoff",
                    {
                        "target_agent": target_agent_id,
                        "query": query[:100] + "..." if len(query) > 100 else query,
                    },
                )

                return QueryResponse(**response.json())

        except Exception as e:
            self.error_count += 1
            self.log_activity("handoff_error", {"target_agent": target_agent_id, "error": str(e)})
            raise

    @abstractmethod
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process a query. Must be implemented by subclasses."""
        pass

    async def query(self, request: QueryRequest) -> QueryResponse:
        """Main query endpoint."""
        try:
            print(f"DEBUG: {self.agent_id} agent received query: {request.query[:100]}...")
            self.status = "active"
            self.current_task = (
                request.query[:50] + "..." if len(request.query) > 50 else request.query
            )

            response = await self.process_query(request.query, request.context)

            self.success_count += 1
            self.log_activity("query_success", {"query": request.query[:100]})

            return QueryResponse(
                status="success",
                response=response,
                agent_id=self.agent_id,
                timestamp=datetime.now(),
                metadata={"model": self.config.model, "capabilities": self.config.capabilities},
            )

        except Exception as e:
            self.error_count += 1
            self.log_activity("query_error", {"query": request.query[:100], "error": str(e)})

            return QueryResponse(
                status="error",
                response=f"Error processing query: {str(e)}",
                agent_id=self.agent_id,
                timestamp=datetime.now(),
            )

        finally:
            self.status = "idle"
            self.current_task = None

    def create_app(self) -> FastAPI:
        """Create FastAPI app for this agent."""
        app = FastAPI(
            title=f"Vectras {self.config.name}",
            description=self.config.description,
            version="0.1.0",
        )

        # Enable CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/health")
        async def health():
            return {"status": "ok", "service": self.agent_id}

        @app.get("/status")
        async def status():
            return self.get_status().model_dump()

        @app.post("/query", response_model=QueryResponse)
        async def query_endpoint(request: QueryRequest) -> QueryResponse:
            return await self.query(request)

        return app
