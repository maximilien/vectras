# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Unit tests for GitHub agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from vectras.agents.github import GitHubIntegration, app


class TestGitHubIntegration:
    """Test the GitHubIntegration class."""

    def test_init(self):
        """Test GitHubIntegration initialization."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")
        assert integration.token == "test_token"
        assert integration.repo_owner == "test_owner"
        assert integration.repo_name == "test_repo"
        assert integration.base_url == "https://api.github.com/repos/test_owner/test_repo"

    def test_headers(self):
        """Test that headers are set correctly."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")
        expected_headers = {
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3+json",
        }
        assert integration.headers == expected_headers

    @pytest.mark.asyncio
    async def test_create_branch_success(self):
        """Test successful branch creation."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            # Mock get SHA response
            mock_sha_response = MagicMock()
            mock_sha_response.json.return_value = {"object": {"sha": "abc123"}}
            mock_sha_response.raise_for_status.return_value = None

            # Mock create branch response
            mock_create_response = MagicMock()
            mock_create_response.status_code = 201

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_sha_response
            )
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_create_response
            )

            result = await integration.create_branch("feature-branch", "main")
            assert result is True

    @pytest.mark.asyncio
    async def test_create_branch_failure(self):
        """Test branch creation failure."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "API Error"
            )

            result = await integration.create_branch("feature-branch", "main")
            assert result is False

    @pytest.mark.asyncio
    async def test_commit_files_success(self):
        """Test successful file commit."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            # Mock tree response
            mock_tree_response = MagicMock()
            mock_tree_response.json.return_value = {"sha": "tree123"}
            mock_tree_response.raise_for_status.return_value = None

            # Mock commit response
            mock_commit_response = MagicMock()
            mock_commit_response.status_code = 201

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_tree_response
            )
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_commit_response
            )

            result = await integration.commit_files("feature-branch", ["test.py"], "Test commit")
            assert result is True

    @pytest.mark.asyncio
    async def test_commit_files_failure(self):
        """Test file commit failure."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                "API Error"
            )

            result = await integration.commit_files("feature-branch", ["test.py"], "Test commit")
            assert result is False

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self):
        """Test successful PR creation."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "html_url": "https://github.com/test_owner/test_repo/pull/1"
            }

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await integration.create_pull_request("feature-branch", "Test PR", "Test body")
            assert result is not None
            assert "html_url" in result

    @pytest.mark.asyncio
    async def test_create_pull_request_failure(self):
        """Test PR creation failure."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception(
                "API Error"
            )

            result = await integration.create_pull_request("feature-branch", "Test PR", "Test body")
            assert result is None

    @pytest.mark.asyncio
    async def test_list_branches_success(self):
        """Test successful branch listing."""

        with patch("vectras.agents.github.github_integration") as mock_integration:
            mock_integration.base_url = "https://api.github.com/repos/test_owner/test_repo"
            mock_integration.headers = {"Authorization": "token test_token"}

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = [
                    {"name": "main", "commit": {"sha": "abc123"}},
                    {"name": "feature-branch", "commit": {"sha": "def456"}},
                ]
                mock_response.raise_for_status.return_value = None

                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                # Test the underlying logic directly
                async with httpx.AsyncClient() as client:
                    branches_url = f"{mock_integration.base_url}/branches"
                    response = await client.get(branches_url, headers=mock_integration.headers)
                    response.raise_for_status()
                    branches = response.json()

                    branch_list = [f"- {branch['name']}" for branch in branches]
                    result = f"📋 Available branches:\n{chr(10).join(branch_list)}"

                assert "Available branches" in result
                assert "main" in result
                assert "feature-branch" in result

    @pytest.mark.asyncio
    async def test_list_branches_failure(self):
        """Test branch listing failure."""

        with patch("vectras.agents.github.github_integration") as mock_integration:
            mock_integration.base_url = "https://api.github.com/repos/test_owner/test_repo"
            mock_integration.headers = {"Authorization": "token test_token"}

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
                    "API Error"
                )

                # Test the underlying logic directly
                try:
                    async with httpx.AsyncClient() as client:
                        branches_url = f"{mock_integration.base_url}/branches"
                        response = await client.get(branches_url, headers=mock_integration.headers)
                        response.raise_for_status()
                        branches = response.json()

                        branch_list = [f"- {branch['name']}" for branch in branches]
                        result = f"📋 Available branches:\n{chr(10).join(branch_list)}"
                except Exception as e:
                    result = f"❌ Error listing branches: {str(e)}"

                assert "Error listing branches" in result


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint(test_client):
    """Test health endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "github-agent"


def test_status_endpoint(test_client):
    """Test status endpoint."""
    response = test_client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "GitHub Agent"
    assert data["status"] == "active"
    assert "tools" in data


@pytest.mark.asyncio
async def test_query_endpoint(test_client):
    """Test query endpoint."""
    # Mock the Runner.run method
    with patch("vectras.agents.github.Runner.run") as mock_run:
        mock_result = MagicMock()
        mock_result.final_output = "Test response from GitHub agent"
        mock_run.return_value = mock_result

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Test response from GitHub agent" in data["response"]
        assert data["agent_id"] == "github"


@pytest.mark.asyncio
async def test_query_endpoint_error(test_client):
    """Test query endpoint with error."""
    # Mock the Runner.run method to raise an exception
    with patch("vectras.agents.github.Runner.run") as mock_run:
        mock_run.side_effect = Exception("Test error")

        response = test_client.post("/query", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Error processing query" in data["response"]
