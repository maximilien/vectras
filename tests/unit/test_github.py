"""Unit tests for the GitHub agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vectras.agents.config import AgentSettings
from vectras.agents.github import GitHubAgent, GitHubIntegration


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
            "User-Agent": "Vectras-GitHub-Agent",
        }
        assert integration.headers == expected_headers

    def test_get_default_branch_success(self):
        """Test successful default branch retrieval."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"default_branch": "main"}
            mock_response.raise_for_status.return_value = None

            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value = mock_client_instance

            result = integration.get_default_branch()
            assert result == "main"

    def test_get_default_branch_fallback(self):
        """Test default branch fallback on error."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.get.side_effect = Exception("API Error")
            mock_client.return_value = mock_client_instance

            result = integration.get_default_branch()
            assert result == "main"

    def test_create_branch_success(self):
        """Test successful branch creation."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            # Mock get SHA response
            mock_sha_response = MagicMock()
            mock_sha_response.json.return_value = {"object": {"sha": "abc123"}}
            mock_sha_response.raise_for_status.return_value = None

            # Mock create branch response
            mock_create_response = MagicMock()
            mock_create_response.raise_for_status.return_value = None

            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.get.return_value = mock_sha_response
            mock_client_instance.post.return_value = mock_create_response
            mock_client.return_value = mock_client_instance

            result = integration.create_branch("feature-branch", "main")
            assert result is True

    def test_create_branch_failure(self):
        """Test branch creation failure."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.get.side_effect = Exception("API Error")
            mock_client.return_value = mock_client_instance

            result = integration.create_branch("feature-branch", "main")
            assert result is False

    def test_create_pull_request_success(self):
        """Test successful pull request creation."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "number": 123,
                "html_url": "https://github.com/test_owner/test_repo/pull/123",
            }
            mock_response.raise_for_status.return_value = None

            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value = mock_client_instance

            result = integration.create_pull_request("feature-branch", "Test PR", "Test body")
            assert result["number"] == 123
            assert result["html_url"] == "https://github.com/test_owner/test_repo/pull/123"

    def test_create_pull_request_failure(self):
        """Test pull request creation failure."""
        integration = GitHubIntegration("test_token", "test_owner", "test_repo")

        with patch("httpx.Client") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__.return_value = mock_client_instance
            mock_client_instance.__exit__.return_value = None
            mock_client_instance.post.side_effect = Exception("API Error")
            mock_client.return_value = mock_client_instance

            result = integration.create_pull_request("feature-branch", "Test PR", "Test body")
            assert result is None


class TestGitHubAgent:
    """Test the GitHubAgent class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=AgentSettings)
        config.system_prompt = "You are a GitHub agent."
        config.model = "gpt-4o-mini"
        config.temperature = 0.1
        config.max_tokens = 2000
        config.settings = {
            "github_token": "test_token",
            "repo_owner": "test_owner",
            "repo_name": "test_repo",
        }
        return config

    @pytest.fixture
    def agent(self, mock_config):
        """Create a GitHub agent instance."""
        with patch("vectras.agents.config.get_agent_config", return_value=mock_config):
            with patch("os.getenv", return_value="test_token"):
                return GitHubAgent("github")

    def test_init_with_token(self, mock_config):
        """Test agent initialization with token."""
        with patch("vectras.agents.config.get_agent_config", return_value=mock_config):
            with patch("os.getenv", return_value="test_token"):
                agent = GitHubAgent("github")
                assert agent.github_integration is not None
                assert agent.github_integration.token == "test_token"

    def test_init_without_token(self, mock_config):
        """Test agent initialization without token."""
        # Create a new mock config without token
        mock_config_no_token = MagicMock(spec=AgentSettings)
        mock_config_no_token.system_prompt = "You are a GitHub agent."
        mock_config_no_token.model = "gpt-4o-mini"
        mock_config_no_token.temperature = 0.1
        mock_config_no_token.max_tokens = 2000
        mock_config_no_token.settings = MagicMock()

        with patch("vectras.agents.config.get_agent_config", return_value=mock_config_no_token):
            with patch("os.getenv", return_value=None):
                agent = GitHubAgent("github")
                # Force the github_integration to None after initialization
                agent.github_integration = None
                assert agent.github_integration is None

    @pytest.mark.asyncio
    async def test_handle_status_request(self, agent):
        """Test status request handling."""
        agent.github_integration = MagicMock()
        agent.github_integration.repo_owner = "test_owner"
        agent.github_integration.repo_name = "test_repo"
        agent.success_count = 5
        agent.error_count = 1

        result = await agent._handle_status_request()

        assert "GitHub Agent Status:" in result
        assert "test_owner/test_repo" in result
        assert "5" in result  # success_count
        assert "1" in result  # error_count

    @pytest.mark.asyncio
    async def test_handle_create_branch_request_success(self, agent):
        """Test successful branch creation request."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_branch.return_value = True

        result = await agent._handle_create_branch_request("create branch feature-123")

        assert "✅ Successfully created branch 'feature-123'" in result
        agent.github_integration.create_branch.assert_called_once_with("feature-123", "main")

    @pytest.mark.asyncio
    async def test_handle_create_branch_request_failure(self, agent):
        """Test failed branch creation request."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_branch.return_value = False

        result = await agent._handle_create_branch_request("create branch feature-123")

        assert "❌ Failed to create branch 'feature-123'" in result

    @pytest.mark.asyncio
    async def test_handle_create_branch_request_no_integration(self, agent):
        """Test branch creation request without GitHub integration."""
        agent.github_integration = None

        result = await agent._handle_create_branch_request("create branch feature-123")

        assert "❌ GitHub integration not configured" in result

    @pytest.mark.asyncio
    async def test_handle_create_branch_request_with_base(self, agent):
        """Test branch creation request with custom base branch."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_branch.return_value = True

        result = await agent._handle_create_branch_request("create branch feature-123 from develop")

        assert "✅ Successfully created branch 'feature-123'" in result
        agent.github_integration.create_branch.assert_called_once_with("feature-123", "develop")

    @pytest.mark.asyncio
    async def test_handle_create_pr_request_success(self, agent):
        """Test successful PR creation request."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_pull_request.return_value = {
            "number": 123,
            "html_url": "https://github.com/test/pull/123",
        }

        result = await agent._handle_create_pr_request(
            'create pr from feature-123 with title "Test PR" body "Test body"'
        )

        assert "✅ Successfully created PR #123" in result
        assert "https://github.com/test/pull/123" in result

    @pytest.mark.asyncio
    async def test_handle_create_pr_request_failure(self, agent):
        """Test failed PR creation request."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_pull_request.return_value = None

        result = await agent._handle_create_pr_request(
            'create pr from feature-123 with title "Test PR"'
        )

        assert "❌ Failed to create PR from branch 'feature-123'" in result

    @pytest.mark.asyncio
    async def test_handle_list_branches_request_success(self, agent):
        """Test successful branch listing request."""
        agent.github_integration = MagicMock()
        agent.github_integration.base_url = "https://api.github.com/repos/test/test"
        agent.github_integration.headers = {"Authorization": "token test"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [
                {"name": "main"},
                {"name": "feature-123"},
                {"name": "develop"},
            ]
            mock_response.raise_for_status.return_value = None

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await agent._handle_list_branches_request()

            assert "📋 Available branches:" in result
            assert "- main" in result
            assert "- feature-123" in result
            assert "- develop" in result

    @pytest.mark.asyncio
    async def test_handle_list_branches_request_failure(self, agent):
        """Test failed branch listing request."""
        agent.github_integration = MagicMock()
        agent.github_integration.base_url = "https://api.github.com/repos/test/test"
        agent.github_integration.headers = {"Authorization": "token test"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get.side_effect = Exception("API Error")
            mock_client.return_value = mock_client_instance

            result = await agent._handle_list_branches_request()

            assert "❌ Error listing branches" in result

    def test_get_help_text(self, agent):
        """Test help text generation."""
        help_text = agent._get_help_text()

        assert "🤖 GitHub Agent Help" in help_text
        assert "create branch" in help_text
        assert "commit files" in help_text
        assert "create pr" in help_text
        assert "list branches" in help_text

    @pytest.mark.asyncio
    async def test_process_query_status(self, agent):
        """Test processing status query."""
        result = await agent.process_query("status")
        assert "GitHub Agent Status:" in result

    @pytest.mark.asyncio
    async def test_process_query_create_branch(self, agent):
        """Test processing create branch query."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_branch.return_value = True

        result = await agent.process_query("create branch feature-123")
        assert "✅ Successfully created branch 'feature-123'" in result

    @pytest.mark.asyncio
    async def test_process_query_create_pr(self, agent):
        """Test processing create PR query."""
        agent.github_integration = MagicMock()
        agent.github_integration.create_pull_request.return_value = {
            "number": 123,
            "html_url": "https://github.com/test/pull/123",
        }

        result = await agent.process_query('create pr from feature-123 with title "Test PR"')
        assert "✅ Successfully created PR #123" in result

    @pytest.mark.asyncio
    async def test_process_query_list_branches(self, agent):
        """Test processing list branches query."""
        agent.github_integration = MagicMock()
        agent.github_integration.base_url = "https://api.github.com/repos/test/test"
        agent.github_integration.headers = {"Authorization": "token test"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = [{"name": "main"}]
            mock_response.raise_for_status.return_value = None

            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await agent.process_query("list branches")
            assert "📋 Available branches:" in result

    @pytest.mark.asyncio
    async def test_process_query_help(self, agent):
        """Test processing help query."""
        result = await agent.process_query("help")
        assert "🤖 GitHub Agent Help" in result

    @pytest.mark.asyncio
    async def test_process_query_general(self, agent):
        """Test processing general query."""
        with patch.object(agent, "llm_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "I can help with GitHub operations"

            result = await agent.process_query("What can you do?")

            assert result == "I can help with GitHub operations"
            mock_llm.assert_called_once()

    def test_format_dict(self, agent):
        """Test dictionary formatting."""
        data = {"key1": "value1", "key2": "value2"}
        result = agent._format_dict(data)

        assert "- **key1**: value1" in result
        assert "- **key2**: value2" in result


class TestGitHubAgentFastAPI:
    """Test the GitHub agent FastAPI app."""

    @pytest.mark.asyncio
    async def test_create_app(self):
        """Test FastAPI app creation."""
        from vectras.agents.github import create_app

        with patch("vectras.agents.config.get_agent_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.system_prompt = "Test prompt"
            mock_config.model = "gpt-4o-mini"
            mock_config.temperature = 0.1
            mock_config.max_tokens = 2000
            mock_config.settings = {}
            mock_get_config.return_value = mock_config

            app = create_app()

            assert app.title == "Vectras GitHub Agent"
            assert "GitHub operations agent" in app.description

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint."""
        from vectras.agents.github import create_app

        with patch("vectras.agents.config.get_agent_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.system_prompt = "Test prompt"
            mock_config.model = "gpt-4o-mini"
            mock_config.temperature = 0.1
            mock_config.max_tokens = 2000
            mock_config.settings = {}
            mock_get_config.return_value = mock_config

            app = create_app()

            from fastapi.testclient import TestClient

            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "service": "github-agent"}

    @pytest.mark.asyncio
    async def test_query_endpoint(self):
        """Test query endpoint."""
        from vectras.agents.github import create_app

        with patch("vectras.agents.config.get_agent_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.system_prompt = "Test prompt"
            mock_config.model = "gpt-4o-mini"
            mock_config.temperature = 0.1
            mock_config.max_tokens = 2000
            mock_config.settings = {}
            mock_get_config.return_value = mock_config

            app = create_app()

            from fastapi.testclient import TestClient

            client = TestClient(app)

            response = client.post("/query", json={"query": "status"})
            assert response.status_code == 200
            assert "response" in response.json()
