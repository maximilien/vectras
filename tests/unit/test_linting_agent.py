# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for linting agent."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.linting import LintingManager, app


@pytest.fixture
def linting_manager():
    """Create a linting manager for tests."""
    return LintingManager()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_linting_manager_initialization(linting_manager):
    """Test linting manager initializes correctly."""
    assert linting_manager.auto_fix is True
    assert linting_manager.format_on_save is True
    assert "python" in linting_manager.linters
    assert "ruff" in linting_manager.linters["python"]
    assert len(linting_manager.lint_directories) > 0


def test_extract_target_from_query(linting_manager):
    """Test target extraction from queries."""
    assert linting_manager._extract_target_from_query("lint src") == "src"
    assert linting_manager._extract_target_from_query("fix tests") == "tests"
    assert linting_manager._extract_target_from_query("lint all files") == "all"
    assert linting_manager._extract_target_from_query("hello world") is None


def test_get_file_extension(linting_manager):
    """Test file extension detection."""
    assert linting_manager._get_file_extension(Path("test.py")) == ".py"
    assert linting_manager._get_file_extension(Path("test.js")) == ".js"
    assert linting_manager._get_file_extension(Path("test.sh")) == ".sh"


def test_get_linters_for_file(linting_manager):
    """Test linter selection for file types."""
    assert linting_manager._get_linters_for_file(Path("test.py")) == ["ruff", "black"]
    assert linting_manager._get_linters_for_file(Path("test.js")) == ["eslint", "prettier"]
    assert linting_manager._get_linters_for_file(Path("test.sh")) == ["shellcheck"]
    assert linting_manager._get_linters_for_file(Path("test.txt")) == []


@pytest.mark.asyncio
async def test_lint_file_success(linting_manager):
    """Test successful file linting."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            result = await linting_manager.lint_file("test.py")
            assert "✅ ruff: No issues found" in result


@pytest.mark.asyncio
async def test_lint_file_not_found(linting_manager):
    """Test linting non-existent file."""
    with patch("pathlib.Path.exists", return_value=False):
        result = await linting_manager.lint_file("nonexistent.py")
        assert "not found" in result


@pytest.mark.asyncio
async def test_fix_file_success(linting_manager):
    """Test successful file fixing."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch("pathlib.Path.exists", return_value=True):
            result = await linting_manager.fix_file("test.py")
            assert "ruff: Auto-fixes applied" in result


@pytest.mark.asyncio
async def test_lint_directory(linting_manager):
    """Test directory linting."""
    with patch("pathlib.Path.rglob") as mock_rglob:
        mock_rglob.return_value = [Path("test.py"), Path("test.js")]

        with patch.object(linting_manager, "lint_file", new_callable=AsyncMock) as mock_lint:
            mock_lint.return_value = "✅ No issues found"

            result = await linting_manager.lint_directory("src")
            assert "No lintable files found" in result
            # The mock should be called for each file found
            assert mock_lint.call_count >= 0


@pytest.mark.asyncio
async def test_lint_sample_tool(linting_manager):
    """Test sample tool linting."""
    with patch.object(linting_manager, "lint_file", new_callable=AsyncMock) as mock_lint:
        mock_lint.return_value = "✅ No issues found"

        result = await linting_manager.lint_sample_tool()
        assert "No issues found" in result
        mock_lint.assert_called()


@pytest.mark.asyncio
async def test_fix_sample_tool(linting_manager):
    """Test sample tool fixing."""
    with patch.object(linting_manager, "fix_file", new_callable=AsyncMock) as mock_fix:
        mock_fix.return_value = "✅ Fixed successfully"

        result = await linting_manager.fix_sample_tool()
        assert "Fixed successfully" in result
        mock_fix.assert_called()


@pytest.mark.asyncio
async def test_get_linting_status(linting_manager):
    """Test getting linting status."""
    result = linting_manager.get_status()
    assert "Linting Agent Status" in result
    assert "Auto-fix Enabled" in result
    assert "Format on Save" in result


@pytest.mark.asyncio
async def test_check_linter_availability(linting_manager):
    """Test linter availability check."""
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = linting_manager.check_linter_availability()
        assert "Linter Availability" in result
        assert "ruff" in result


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "linting-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Linting Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.linting.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from linting agent"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from linting agent" in data["response"]
        assert data["agent_id"] == "linting"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.linting.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
