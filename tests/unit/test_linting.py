"""Unit tests for linting agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vectras.agents.linting import LintingAgent


@pytest.fixture
def linting_agent():
    """Create a linting agent for tests."""
    with patch("vectras.agents.config.get_agent_config") as mock_config:
        # Mock configuration
        mock_config.return_value = MagicMock(
            id="linting",
            name="Linting Agent",
            port=8127,
            system_prompt="You are the Vectras linting agent.",
            settings=MagicMock(
                linters={
                    "python": ["ruff", "black"],
                    "javascript": ["eslint", "prettier"],
                    "bash": ["shellcheck"],
                },
                auto_fix=True,
                format_on_save=True,
                lint_directories=["./src", "./tests", "./frontend"],
                exclude_patterns=["**/node_modules/**", "**/__pycache__/**"],
            ),
        )
        return LintingAgent()


@pytest.mark.asyncio
async def test_process_query_lint_request(linting_agent):
    """Test linting request processing."""
    linting_agent._lint_all_directories = AsyncMock(return_value="✅ All files passed linting")

    result = await linting_agent.process_query("lint all files")

    assert "✅ All files passed linting" in result
    linting_agent._lint_all_directories.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_fix_request(linting_agent):
    """Test fix request processing."""
    linting_agent._fix_all_directories = AsyncMock(
        return_value="✅ All files are properly formatted"
    )

    result = await linting_agent.process_query("fix all files")

    assert "✅ All files are properly formatted" in result
    linting_agent._fix_all_directories.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_status(linting_agent):
    """Test status request processing."""
    result = await linting_agent.process_query("status")

    assert "Linting Agent Status" in result
    assert "Auto-fix enabled: Yes" in result
    assert "Format on save: Yes" in result


@pytest.mark.asyncio
async def test_process_query_general(linting_agent):
    """Test general query processing."""
    linting_agent.llm_completion = AsyncMock(return_value="I can help with linting!")

    result = await linting_agent.process_query("what can you do?")

    assert result == "I can help with linting!"
    linting_agent.llm_completion.assert_called_once()


@pytest.mark.asyncio
async def test_lint_specific_target_file(linting_agent):
    """Test linting a specific file."""
    linting_agent._lint_files = AsyncMock(return_value="✅ test.py: No issues found")

    # Mock the Path constructor to return a mock object
    mock_path_instance = MagicMock()
    mock_path_instance.is_file.return_value = True
    mock_path_instance.is_dir.return_value = False

    with patch("vectras.agents.linting.Path", return_value=mock_path_instance):
        result = await linting_agent._lint_specific_target("test.py")

        assert "✅ test.py: No issues found" in result
        linting_agent._lint_files.assert_called_once()


@pytest.mark.asyncio
async def test_fix_specific_target_directory(linting_agent):
    """Test fixing a specific directory."""
    linting_agent._fix_directory = AsyncMock(
        return_value="✅ All files in ./src are properly formatted"
    )

    result = await linting_agent._fix_specific_target("./src")

    assert "✅ All files in ./src are properly formatted" in result
    linting_agent._fix_directory.assert_called_once()


@pytest.mark.asyncio
async def test_lint_file_python(linting_agent):
    """Test linting a Python file."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.suffix = ".py"
        linting_agent._run_ruff = AsyncMock(return_value="✅ No issues found")
        linting_agent._run_black = AsyncMock(return_value="✅ Properly formatted")

        result = await linting_agent._lint_file(mock_path.return_value)

        assert "ruff: ✅ No issues found" in result
        assert "black: ✅ Properly formatted" in result


@pytest.mark.asyncio
async def test_fix_file_javascript(linting_agent):
    """Test fixing a JavaScript file."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.suffix = ".js"
        linting_agent._run_eslint = AsyncMock(return_value="✅ Fixed")
        linting_agent._run_prettier = AsyncMock(return_value="✅ Formatted")

        result = await linting_agent._fix_file(mock_path.return_value)

        assert "eslint: ✅ Fixed" in result
        assert "prettier: ✅ Formatted" in result


@pytest.mark.asyncio
async def test_run_ruff_success(linting_agent):
    """Test running ruff successfully."""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await linting_agent._run_ruff("test.py", fix=False)

        assert result == "✅ No issues found"


@pytest.mark.asyncio
async def test_run_black_fix(linting_agent):
    """Test running black with fix."""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        result = await linting_agent._run_black("test.py", fix=True)

        assert result == "✅ Formatted"


@pytest.mark.asyncio
async def test_detect_language_python(linting_agent):
    """Test language detection for Python."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.suffix = ".py"
        result = linting_agent._detect_language(mock_path.return_value)
        assert result == "python"


@pytest.mark.asyncio
async def test_detect_language_javascript(linting_agent):
    """Test language detection for JavaScript."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.suffix = ".js"
        result = linting_agent._detect_language(mock_path.return_value)
        assert result == "javascript"


@pytest.mark.asyncio
async def test_detect_language_unknown(linting_agent):
    """Test language detection for unknown file type."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.suffix = ".txt"
        result = linting_agent._detect_language(mock_path.return_value)
        assert result is None


def test_extract_target_from_query(linting_agent):
    """Test extracting target from query."""
    assert linting_agent._extract_target_from_query("lint test.py") == "test.py"
    assert linting_agent._extract_target_from_query("fix ./src") == "./src"
    assert linting_agent._extract_target_from_query("format 'my file.py'") == "'my file.py'"
    assert linting_agent._extract_target_from_query("check something") == "something"


def test_matches_pattern(linting_agent):
    """Test pattern matching for exclusions."""
    with patch("pathlib.Path") as mock_path:
        mock_path.return_value.__str__ = lambda self: "src/__pycache__/test.py"
        result = linting_agent._matches_pattern(mock_path.return_value, "**/__pycache__/**")
        assert result is True


@pytest.mark.asyncio
async def test_linting_agent_fastapi_app(linting_agent):
    """Test FastAPI app creation."""
    app = linting_agent.create_app()
    assert app.title == "Vectras Linting Agent"
    assert "linters on code changes" in app.description


if __name__ == "__main__":
    pytest.main([__file__])
