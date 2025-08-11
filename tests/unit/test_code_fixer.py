# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for code fixer agent."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from vectras.agents.code_fixer import CodeAnalysis, CodeFixerAgent, create_app


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create some test files
        (project_path / "test.py").write_text("print('hello world')")
        (project_path / "error.py").write_text("def test():\n    return invalid_variable")

        yield project_path


@pytest.fixture
def code_fixer_agent(monkeypatch, temp_project):
    """Create a code fixer agent with fake OpenAI."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    # Mock the project root to use our temp directory
    with patch("vectras.agents.code_fixer.get_project_root", return_value=temp_project):
        agent = CodeFixerAgent()
        yield agent


def test_code_analysis_creation():
    """Test CodeAnalysis creation and assessment."""
    analysis = CodeAnalysis(
        "test.py",
        "NameError: name 'undefined_var' is not defined",
        "The variable 'undefined_var' is not defined. It should be 'defined_var'.",
        "Replace 'undefined_var' with 'defined_var'",
    )

    assert analysis["file_path"] == "test.py"
    assert analysis["severity"] in ["low", "medium", "high"]
    assert analysis["confidence"] in ["low", "medium", "high"]
    assert "timestamp" in analysis


def test_severity_assessment():
    """Test error severity assessment."""
    # High severity
    critical_analysis = CodeAnalysis(
        "test.py", "SyntaxError: invalid syntax", "Syntax error", "Fix syntax"
    )
    assert critical_analysis["severity"] == "high"

    # Medium severity
    type_analysis = CodeAnalysis(
        "test.py", "TypeError: unsupported operand", "Type error", "Fix types"
    )
    assert type_analysis["severity"] == "medium"

    # Low severity
    low_analysis = CodeAnalysis(
        "test.py", "Warning: deprecated method", "Deprecation warning", "Update method"
    )
    assert low_analysis["severity"] == "low"


def test_code_fixer_initialization(code_fixer_agent):
    """Test code fixer agent initializes correctly."""
    assert code_fixer_agent.agent_id == "coding"
    assert code_fixer_agent.config is not None
    assert code_fixer_agent.project_root is not None
    assert isinstance(code_fixer_agent.analyses, list)


@pytest.mark.asyncio
async def test_file_path_extraction(code_fixer_agent):
    """Test extracting file path from error content."""
    error_content = 'File "test.py", line 10, in test_function\n    NameError: name undefined'
    file_path = code_fixer_agent._extract_file_path(error_content)
    assert file_path == "test.py"

    # Test with no file path
    error_content = "Generic error message"
    file_path = code_fixer_agent._extract_file_path(error_content)
    assert file_path is None


@pytest.mark.asyncio
async def test_analyze_error(code_fixer_agent):
    """Test error analysis functionality."""
    error_content = "NameError: name 'undefined_var' is not defined"

    analysis = await code_fixer_agent.analyze_error(error_content, "test.py")

    assert isinstance(analysis, CodeAnalysis)
    assert analysis["file_path"] == "test.py"
    assert analysis["error_content"] == error_content
    assert "Analyzing code for bugs and providing fixes" in analysis["analysis"]
    assert len(code_fixer_agent.analyses) == 1


def test_suggested_fix_extraction(code_fixer_agent):
    """Test extracting suggested fix from analysis."""
    analysis_text = """
    The error is caused by an undefined variable.
    
    Fix: Replace 'undefined_var' with 'defined_var'
    
    This should resolve the issue.
    """

    fix = code_fixer_agent._extract_suggested_fix(analysis_text)
    assert "Replace 'undefined_var' with 'defined_var'" in fix


@pytest.mark.asyncio
async def test_github_integration_unavailable(code_fixer_agent, monkeypatch):
    """Test behavior when GitHub integration is unavailable."""
    # GitHub integration should be None for testing
    assert code_fixer_agent.github_integration is None

    # Mock the HTTP call to GitHub agent to simulate failure
    async def mock_github_agent_call(*args, **kwargs):
        raise Exception("GitHub agent unavailable")

    monkeypatch.setattr(code_fixer_agent, "_handoff_to_github_agent", mock_github_agent_call)

    # Create a dummy analysis
    analysis = CodeAnalysis("test.py", "error", "analysis", "fix")

    # Try to create branch - should fail gracefully
    result = await code_fixer_agent.create_fix_branch(analysis)
    assert "error" in result
    assert "GitHub agent unavailable" in result["error"]


@pytest.mark.asyncio
async def test_get_recent_analyses(code_fixer_agent):
    """Test getting recent analyses."""
    # Add some test analyses
    analysis1 = CodeAnalysis("test1.py", "error1", "analysis1", "fix1")
    analysis2 = CodeAnalysis("test2.py", "error2", "analysis2", "fix2")

    code_fixer_agent.analyses.extend([analysis1, analysis2])

    recent = await code_fixer_agent.get_recent_analyses(limit=10)
    assert len(recent) >= 2
    assert all(isinstance(a, dict) for a in recent)


@pytest.mark.asyncio
async def test_get_analysis_summary(code_fixer_agent):
    """Test getting analysis summary."""
    # Add some test analyses
    analysis1 = CodeAnalysis("test1.py", "SyntaxError", "analysis1", "fix1")
    analysis2 = CodeAnalysis("test2.py", "TypeError", "analysis2", "fix2")

    code_fixer_agent.analyses.extend([analysis1, analysis2])

    summary = await code_fixer_agent.get_analysis_summary()

    assert "total_analyses" in summary
    assert "by_severity" in summary
    assert "by_confidence" in summary
    assert "files_analyzed" in summary
    assert "github_available" in summary
    assert summary["total_analyses"] >= 2


@pytest.mark.asyncio
async def test_query_processing(code_fixer_agent):
    """Test query processing."""
    # Test status query
    response = await code_fixer_agent.process_query("status")
    assert isinstance(response, dict)
    assert "github_integration" in response
    assert "recent_analyses" in response

    # Test analysis summary query
    response = await code_fixer_agent.process_query("analysis summary")
    assert isinstance(response, dict)
    assert "total_analyses" in response

    # Test general query (should use LLM)
    response = await code_fixer_agent.process_query("hello world")
    assert isinstance(response, str)
    assert "Analyzing code for bugs and providing fixes" in response


def test_code_fixer_fastapi_app(monkeypatch):
    """Test the FastAPI app endpoints."""
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("vectras.agents.code_fixer.get_project_root", return_value=Path(tmpdir)):
            app = create_app()
            client = TestClient(app)

            # Test health endpoint
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

            # Test status endpoint
            response = client.get("/status")
            assert response.status_code == 200
            data = response.json()
            assert "agent_id" in data
            assert data["agent_id"] == "coding"

            # Test query endpoint
            response = client.post("/query", json={"query": "status"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


@pytest.mark.asyncio
async def test_analyze_error_with_context(code_fixer_agent):
    """Test error analysis with additional context."""
    error_content = "ValueError: invalid literal for int()"
    context = {"source": "log_monitor", "severity": "medium"}

    analysis = await code_fixer_agent.analyze_error(error_content, "test.py", context)

    assert isinstance(analysis, CodeAnalysis)
    assert analysis["file_path"] == "test.py"
    assert "Analyzing code for bugs and providing fixes" in analysis["analysis"]


@pytest.mark.asyncio
async def test_process_log_entry_context(code_fixer_agent):
    """Test processing query with log entry context."""
    log_entry = {"file_path": "test.py", "content": "ERROR: Division by zero", "line_number": 42}

    context = {"log_entry": log_entry}
    response = await code_fixer_agent.process_query("analyze error", context)

    assert isinstance(response, dict)
    assert response["file_path"] == "test.py"
    assert "Analyzing code for bugs and providing fixes" in response["analysis"]


def test_error_type_patterns():
    """Test various error patterns are correctly classified."""
    patterns = [
        ("SyntaxError: invalid syntax", "high"),
        ("ImportError: No module named", "high"),
        ("TypeError: unsupported operand", "medium"),
        ("ValueError: invalid value", "medium"),
        ("Warning: deprecated feature", "low"),
        ("Info: processing complete", "low"),
    ]

    for error_content, expected_severity in patterns:
        analysis = CodeAnalysis("test.py", error_content, "analysis", "fix")
        assert analysis["severity"] == expected_severity, f"Failed for: {error_content}"
