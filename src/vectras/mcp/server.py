# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class ToolResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras MCP", description="MCP tool server", version="0.1.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "mcp"}

    @app.post("/tool/health", response_model=ToolResponse)
    async def tool_health() -> ToolResponse:
        return ToolResponse(success=True, data={"service": "mcp", "status": "ok"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_MCP_HOST", "localhost")
    port = int(os.getenv("VECTRAS_MCP_PORT", "8122"))
    uvicorn.run(app, host=host, port=port)
