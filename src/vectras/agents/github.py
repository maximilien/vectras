import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .base_agent import BaseAgent


class GitHubIntegration:
    """Handles GitHub API operations."""

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Vectras-GitHub-Agent",
        }

    def get_default_branch(self) -> str:
        """Get the default branch name."""
        try:
            import httpx

            with httpx.Client() as client:
                response = client.get(self.base_url, headers=self.headers)
                response.raise_for_status()
                return response.json()["default_branch"]
        except Exception:
            return "main"

    def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create a new branch from the base branch."""
        try:
            # First get the SHA of the base branch
            import httpx

            with httpx.Client() as client:
                ref_url = f"{self.base_url}/git/ref/heads/{base_branch}"
                response = client.get(ref_url, headers=self.headers)
                response.raise_for_status()
                sha = response.json()["object"]["sha"]

                # Create the new branch
                new_ref_url = f"{self.base_url}/git/refs"
                new_ref_data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
                response = client.post(new_ref_url, headers=self.headers, json=new_ref_data)
                response.raise_for_status()
                return True
        except Exception:
            return False

    def commit_files(self, branch_name: str, files: List[str], commit_message: str) -> bool:
        """Commit files to a branch."""
        try:
            # Get the current tree SHA
            import httpx

            with httpx.Client() as client:
                ref_url = f"{self.base_url}/git/ref/heads/{branch_name}"
                response = client.get(ref_url, headers=self.headers)
                response.raise_for_status()
                current_sha = response.json()["object"]["sha"]

                # Create blobs for each file
                tree_items = []
                for file_path in files:
                    if Path(file_path).exists():
                        with open(file_path, "r") as f:
                            content = f.read()

                        # Create blob
                        blob_url = f"{self.base_url}/git/blobs"
                        blob_data = {"content": content, "encoding": "utf-8"}
                        response = client.post(blob_url, headers=self.headers, json=blob_data)
                        response.raise_for_status()
                        blob_sha = response.json()["sha"]

                        tree_items.append(
                            {"path": file_path, "mode": "100644", "type": "blob", "sha": blob_sha}
                        )

                # Create tree
                tree_url = f"{self.base_url}/git/trees"
                tree_data = {"base_tree": current_sha, "tree": tree_items}
                response = client.post(tree_url, headers=self.headers, json=tree_data)
                response.raise_for_status()
                tree_sha = response.json()["sha"]

                # Create commit
                commit_url = f"{self.base_url}/git/commits"
                commit_data = {
                    "message": commit_message,
                    "tree": tree_sha,
                    "parents": [current_sha],
                }
                response = client.post(commit_url, headers=self.headers, json=commit_data)
                response.raise_for_status()
                commit_sha = response.json()["sha"]

                # Update branch reference
                ref_url = f"{self.base_url}/git/refs/heads/{branch_name}"
                ref_data = {"sha": commit_sha}
                response = client.patch(ref_url, headers=self.headers, json=ref_data)
                response.raise_for_status()
                return True
        except Exception:
            return False

    def create_pull_request(
        self, branch_name: str, title: str, body: str, base_branch: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """Create a pull request."""
        try:
            import httpx

            with httpx.Client() as client:
                pr_url = f"{self.base_url}/pulls"
                pr_data = {"title": title, "body": body, "head": branch_name, "base": base_branch}
                response = client.post(pr_url, headers=self.headers, json=pr_data)
                response.raise_for_status()
                return response.json()
        except Exception:
            return None


class GitHubAgent(BaseAgent):
    """GitHub operations agent for Vectras."""

    def __init__(self, agent_id: str = "github"):
        super().__init__(agent_id)
        self.github_integration = None
        self._init_github_integration()

    def _init_github_integration(self):
        """Initialize GitHub integration with token and repo info."""
        github_token = os.getenv("GITHUB_TOKEN") or getattr(
            self.config.settings, "github_token", None
        )
        repo_owner = getattr(self.config.settings, "repo_owner", "maximilien")
        repo_name = getattr(self.config.settings, "repo_name", "vectras")

        if github_token:
            self.github_integration = GitHubIntegration(github_token, repo_owner, repo_name)
        else:
            self.github_integration = None
            self.log_activity("github_init_error", {"error": "No GitHub token found"})

    async def process_query(self, query: str) -> str:
        """Process GitHub-related queries."""
        query_lower = query.lower().strip()

        if "status" in query_lower:
            return await self._handle_status_request()
        elif "create branch" in query_lower:
            return await self._handle_create_branch_request(query)
        elif "commit" in query_lower and "files" in query_lower:
            return await self._handle_commit_request(query)
        elif "create pr" in query_lower or "pull request" in query_lower:
            return await self._handle_create_pr_request(query)
        elif "list branches" in query_lower:
            return await self._handle_list_branches_request()
        elif "help" in query_lower:
            return self._get_help_text()
        else:
            return await self._handle_general_query(query)

    async def _handle_status_request(self) -> str:
        """Handle status requests."""
        status_info = {
            "agent": "GitHub Agent",
            "status": "active",
            "github_configured": self.github_integration is not None,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }

        if self.github_integration:
            status_info["repo"] = (
                f"{self.github_integration.repo_owner}/{self.github_integration.repo_name}"
            )

        return f"GitHub Agent Status:\n{self._format_dict(status_info)}"

    async def _handle_create_branch_request(self, query: str) -> str:
        """Handle branch creation requests."""
        if not self.github_integration:
            return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

        # Extract branch name from query
        branch_match = re.search(r"create branch ([a-zA-Z0-9_-]+)", query.lower())
        if not branch_match:
            return "❌ Please specify a branch name. Usage: 'create branch feature-name'"

        branch_name = branch_match.group(1)
        base_branch = "main"  # Default base branch

        # Extract base branch if specified
        base_match = re.search(r"from ([a-zA-Z0-9_-]+)", query.lower())
        if base_match:
            base_branch = base_match.group(1)

        try:
            success = self.github_integration.create_branch(branch_name, base_branch)
            if success:
                self.log_activity("branch_created", {"branch": branch_name, "base": base_branch})
                return f"✅ Successfully created branch '{branch_name}' from '{base_branch}'"
            else:
                self.log_activity("branch_creation_failed", {"branch": branch_name})
                return f"❌ Failed to create branch '{branch_name}'"
        except Exception as e:
            self.log_activity("branch_creation_error", {"error": str(e)})
            return f"❌ Error creating branch: {str(e)}"

    async def _handle_commit_request(self, query: str) -> str:
        """Handle commit requests."""
        if not self.github_integration:
            return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

        # Extract branch name
        branch_match = re.search(r"to (\w+)", query.lower())
        if not branch_match:
            return "❌ Please specify a branch. Usage: 'commit files to branch-name'"

        branch_name = branch_match.group(1)

        # Extract commit message
        message_match = re.search(r'message ["\']([^"\']+)["\']', query)
        if not message_match:
            return "❌ Please specify a commit message. Usage: 'commit files to branch-name with message \"your message\"'"

        commit_message = message_match.group(1)

        # Extract file list (simplified - in real implementation, this would be more sophisticated)
        files = self.config.settings.get("files_to_commit", [])
        if not files:
            return "❌ No files specified for commit"

        try:
            success = self.github_integration.commit_files(branch_name, files, commit_message)
            if success:
                self.log_activity("files_committed", {"branch": branch_name, "files": files})
                return f"✅ Successfully committed {len(files)} files to branch '{branch_name}'"
            else:
                self.log_activity("commit_failed", {"branch": branch_name})
                return f"❌ Failed to commit files to branch '{branch_name}'"
        except Exception as e:
            self.log_activity("commit_error", {"error": str(e)})
            return f"❌ Error committing files: {str(e)}"

    async def _handle_create_pr_request(self, query: str) -> str:
        """Handle pull request creation requests."""
        if not self.github_integration:
            return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

        # Extract branch name
        branch_match = re.search(r"from ([a-zA-Z0-9_-]+)", query.lower())
        if not branch_match:
            return "❌ Please specify a branch. Usage: 'create pr from branch-name'"

        branch_name = branch_match.group(1)

        # Extract title
        title_match = re.search(r'title ["\']([^"\']+)["\']', query)
        if not title_match:
            return "❌ Please specify a PR title. Usage: 'create pr from branch-name with title \"your title\"'"

        title = title_match.group(1)

        # Extract body
        body_match = re.search(r'body ["\']([^"\']+)["\']', query)
        body = (
            body_match.group(1)
            if body_match
            else f"PR created by Vectras GitHub Agent from branch {branch_name}"
        )

        try:
            pr = self.github_integration.create_pull_request(branch_name, title, body)
            if pr:
                self.log_activity(
                    "pr_created", {"branch": branch_name, "pr_number": pr.get("number")}
                )
                return f"✅ Successfully created PR #{pr.get('number')}: {title}\nURL: {pr.get('html_url')}"
            else:
                self.log_activity("pr_creation_failed", {"branch": branch_name})
                return f"❌ Failed to create PR from branch '{branch_name}'"
        except Exception as e:
            self.log_activity("pr_creation_error", {"error": str(e)})
            return f"❌ Error creating PR: {str(e)}"

    async def _handle_list_branches_request(self) -> str:
        """Handle branch listing requests."""
        if not self.github_integration:
            return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                branches_url = f"{self.github_integration.base_url}/branches"
                response = await client.get(branches_url, headers=self.github_integration.headers)
                response.raise_for_status()
                branches = response.json()

                branch_list = [f"- {branch['name']}" for branch in branches]
                return f"📋 Available branches:\n{chr(10).join(branch_list)}"
        except Exception as e:
            self.log_activity("list_branches_error", {"error": str(e)})
            return f"❌ Error listing branches: {str(e)}"

    def _get_help_text(self) -> str:
        """Get help text for the GitHub agent."""
        return """🤖 GitHub Agent Help

Available commands:
- status - Show agent status and GitHub configuration
- create branch <name> [from <base>] - Create a new branch
- commit files to <branch> with message "<message>" - Commit files to a branch
- create pr from <branch> with title "<title>" [body "<body>"] - Create a pull request
- list branches - List all branches in the repository
- help - Show this help text

Examples:
- create branch feature-123
- create branch hotfix from main
- commit files to feature-123 with message "Fix bug in login"
- create pr from feature-123 with title "Add new feature" body "This PR adds..."
- list branches

Note: Requires GITHUB_TOKEN environment variable to be set."""

    async def _handle_general_query(self, query: str) -> str:
        """Handle general queries with LLM."""
        system_prompt = """You are the Vectras GitHub Agent. You help with GitHub operations like creating branches, committing code, and creating pull requests. 

If the user is asking about GitHub operations, guide them to use the specific commands. If they're asking about something else, be helpful but remind them of your GitHub focus.

Available commands: create branch, commit files, create pr, list branches, status, help"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(messages)

    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for display."""
        return "\n".join([f"- **{k}**: {v}" for k, v in data.items()])


def create_app() -> FastAPI:
    """Create FastAPI app for the GitHub agent."""
    agent = GitHubAgent("github")

    app = FastAPI(
        title="Vectras GitHub Agent",
        description="GitHub operations agent for Vectras - handles branches, commits, and PRs",
        version="0.1.0",
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/query")
    async def query(request: Dict[str, Any]):
        query_text = request.get("query", "")
        response = await agent.process_query(query_text)
        return {"response": response}

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "github-agent"}

    @app.get("/status")
    async def status():
        return agent.get_status().model_dump()

    return app


app = create_app()
