# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for coding agent."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.coding import CodeAnalysis, CodeFixerManager, app


@pytest.fixture
def code_fixer_manager():
    """Create a code fixer manager for tests."""
    return CodeFixerManager()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_code_analysis_creation():
    """Test CodeAnalysis creation."""
    analysis = CodeAnalysis(
        file_path="test.py",
        error_content="SyntaxError: invalid syntax",
        analysis="The code has a syntax error on line 10",
        suggested_fix="Fix the syntax error by adding missing colon",
    )

    assert analysis.file_path == "test.py"
    assert analysis.error_content == "SyntaxError: invalid syntax"
    assert analysis.analysis == "The code has a syntax error on line 10"
    assert analysis.suggested_fix == "Fix the syntax error by adding missing colon"
    assert analysis.severity == "high"  # SyntaxError is high severity
    assert analysis.confidence in ["low", "medium", "high"]


def test_code_analysis_to_dict():
    """Test CodeAnalysis to_dict method."""
    analysis = CodeAnalysis(
        file_path="test.py",
        error_content="ValueError: invalid value",
        analysis="The value is invalid",
        suggested_fix="Use a valid value",
    )

    analysis_dict = analysis.to_dict()
    assert analysis_dict["file_path"] == "test.py"
    assert analysis_dict["error_content"] == "ValueError: invalid value"
    assert analysis_dict["analysis"] == "The value is invalid"
    assert analysis_dict["suggested_fix"] == "Use a valid value"
    assert analysis_dict["severity"] == "medium"  # ValueError is medium severity
    assert "timestamp" in analysis_dict


def test_code_fixer_manager_initialization(code_fixer_manager):
    """Test code fixer manager initializes correctly."""
    assert code_fixer_manager.project_root == Path(".")
    assert isinstance(code_fixer_manager.analyses, list)
    assert isinstance(code_fixer_manager.fix_history, list)


def test_extract_file_path(code_fixer_manager):
    """Test file path extraction from error content."""
    # Test different error message patterns
    error1 = 'File "test.py", line 10, in <module>'
    error2 = "File 'main.py', line 5, in function"
    error3 = "at module.py:15"
    error4 = "in utils.py"

    assert code_fixer_manager._extract_file_path(error1) == "test.py"
    assert code_fixer_manager._extract_file_path(error2) == "main.py"
    assert code_fixer_manager._extract_file_path(error3) == "module.py"
    assert code_fixer_manager._extract_file_path(error4) == "utils.py"

    # Test with no file path
    assert code_fixer_manager._extract_file_path("Some error message") is None


@pytest.mark.asyncio
async def test_analyze_code(code_fixer_manager):
    """Test code analysis."""
    result = await code_fixer_manager.analyze_code("test.py")
    assert "Could not read file" in result or "Code Analysis" in result
    assert "test.py" in result


@pytest.mark.asyncio
async def test_analyze_error(code_fixer_manager):
    """Test error analysis."""
    error_content = "SyntaxError: invalid syntax at line 10"
    result = await code_fixer_manager.analyze_error(error_content)
    assert "Error Analysis" in result
    assert "SyntaxError" in result


@pytest.mark.asyncio
async def test_fix_code(code_fixer_manager):
    """Test code fixing."""
    result = await code_fixer_manager.fix_code("test.py", "Fix division by zero")
    assert "Successfully applied fix" in result or "Could not read file" in result
    assert "test.py" in result


@pytest.mark.asyncio
async def test_fix_sample_tool(code_fixer_manager):
    """Test sample tool fixing."""
    result = await code_fixer_manager.fix_sample_tool()
    assert "Successfully applied fix" in result or "Could not read file" in result


@pytest.mark.asyncio
async def test_get_code_fixer_status(code_fixer_manager):
    """Test getting code fixer status."""
    result = code_fixer_manager.get_status()
    assert "Coding Agent Status" in result
    assert "Total Analyses" in result


@pytest.mark.asyncio
async def test_get_recent_analyses(code_fixer_manager):
    """Test getting recent analyses."""
    result = code_fixer_manager.get_recent_analyses()
    assert "Recent Code Analyses" in result or "No analyses performed yet" in result


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "coding-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "Coding Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.coding.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from coding agent"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from coding agent" in data["response"]
        assert data["agent_id"] == "coding"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.coding.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
