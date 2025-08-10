# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for API module."""

from fastapi.testclient import TestClient

from vectras.apis.api import create_app


def test_health_ok():
    app = create_app()
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "api"
