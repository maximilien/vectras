# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ConfigResponse(BaseModel):
    default_queries: list[str]


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {"default_queries": ["status", "latest actions", "up time"]}


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras API", description="Simple health API", version="0.1.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="api")

    @app.get("/config", response_model=ConfigResponse)
    async def config() -> ConfigResponse:
        config_data = load_config()
        return ConfigResponse(
            default_queries=config_data.get(
                "default_queries", ["status", "latest actions", "up time"]
            )
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_API_HOST", "localhost")
    port = int(os.getenv("VECTRAS_API_PORT", "8121"))
    uvicorn.run(app, host=host, port=port)
