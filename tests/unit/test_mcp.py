# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for MCP module."""

from fastapi.testclient import TestClient

from vectras.mcp.server import create_app


def test_tool_health_ok():
    app = create_app()
    client = TestClient(app)

    r = client.post("/tool/health", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["service"] == "mcp"
