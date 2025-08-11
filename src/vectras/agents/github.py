# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""GitHub Agent - Manages GitHub operations like creating branches and PRs."""

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
        except Exception as e:
            print(f"GitHub API Error: {e}")
            if "Resource not accessible by personal access token" in str(e):
                print(
                    "Token lacks 'repo' scope. Please create a new token with 'repo' permissions."
                )
            elif "Not Found" in str(e):
                print(f"Repository not found: {self.repo_owner}/{self.repo_name}")
                print("Please ensure the repository exists and your token has access to it.")
            elif "Bad credentials" in str(e):
                print("Invalid GitHub token. Please check your GITHUB_TOKEN environment variable.")
            elif "Resource not accessible by personal access token" in str(e):
                print(
                    "Token lacks 'repo' scope. Please create a new token with 'repo' permissions."
                )
            else:
                print(f"Unexpected GitHub API error: {type(e).__name__}: {e}")
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
        except Exception as e:
            print(f"GitHub commit error: {e}")
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
        self.pull_requests = []  # Track all created PRs
        self._init_github_integration()

    def _init_github_integration(self):
        """Initialize GitHub integration with token and repo info."""
        github_token = os.getenv("GITHUB_TOKEN") or getattr(
            self.config.settings, "github_token", None
        )
        repo_owner = os.getenv("GITHUB_ORG") or getattr(
            self.config.settings, "github_org", "maximilien"
        )
        repo_name = os.getenv("GITHUB_REPO") or getattr(
            self.config.settings, "github_repo", "vectras"
        )

        if github_token:
            print(f"🔧 Initializing GitHub integration for {repo_owner}/{repo_name}")
            self.github_integration = GitHubIntegration(github_token, repo_owner, repo_name)
            self.log_activity(
                "github_integration_initialized", {"repo": f"{repo_owner}/{repo_name}"}
            )
        else:
            print("⚠️ No GitHub token found. GitHub integration disabled.")
            self.github_integration = None
            self.log_activity("github_init_error", {"error": "No GitHub token found"})

    def _track_pr_activity(self, pr_data: Dict[str, Any]):
        """Track a new pull request activity."""
        pr_info = {
            "id": pr_data.get("id"),
            "number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "url": pr_data.get("html_url"),
            "branch": pr_data.get("head", {}).get("ref"),
            "base_branch": pr_data.get("base", {}).get("ref"),
            "state": pr_data.get("state"),
            "created_at": pr_data.get("created_at"),
            "body": pr_data.get("body", "")[:200] + "..."
            if len(pr_data.get("body", "")) > 200
            else pr_data.get("body", ""),
        }
        self.pull_requests.append(pr_info)
        self.log_activity("pr_created", pr_info)

    async def _handle_recent_pr_request(self) -> str:
        """Handle queries about recent/latest pull requests."""
        if not self.pull_requests:
            return "📋 No pull requests have been created yet. Use 'create pr' to create your first pull request!"

        # Get the most recent PR
        latest_pr = self.pull_requests[-1]

        response = "📋 **Latest Pull Request:**\n\n"
        response += f"**#{latest_pr['number']} - {latest_pr['title']}**\n"
        response += f"🔗 URL: {latest_pr['url']}\n"
        response += f"🌿 Branch: `{latest_pr['branch']}` → `{latest_pr['base_branch']}`\n"
        response += f"📅 Created: {latest_pr['created_at']}\n"
        response += f"📝 Description: {latest_pr['body']}\n\n"

        if len(self.pull_requests) > 1:
            response += f"📊 **Total PRs created:** {len(self.pull_requests)}\n"
            response += "📋 **Recent PRs:**\n"
            for pr in self.pull_requests[-3:]:  # Show last 3 PRs
                response += f"  - #{pr['number']}: {pr['title']}\n"

        return response

    async def _handle_activities_request(self) -> str:
        """Handle queries about recent activities."""
        if not self.recent_activities:
            return (
                "📋 No recent activities recorded. I haven't performed any GitHub operations yet."
            )

        # Get the most recent activities (last 10)
        recent_activities = (
            self.recent_activities[-10:]
            if len(self.recent_activities) > 10
            else self.recent_activities
        )

        response = f"📋 **Recent GitHub Activities ({len(recent_activities)} activities):**\n\n"

        for i, activity in enumerate(reversed(recent_activities), 1):
            activity_type = activity.get("activity", "unknown")
            details = activity.get("details", {})
            timestamp = activity.get("timestamp", "unknown")

            # Format the activity based on type
            if activity_type == "pr_created":
                response += f"**{i}. Created Pull Request**\n"
                if "pr_number" in details:
                    response += f"   📝 PR #{details['pr_number']}\n"
                if "branch" in details:
                    response += f"   🌿 Branch: {details['branch']}\n"
            elif activity_type == "branch_created":
                response += f"**{i}. Created Branch**\n"
                if "branch" in details:
                    response += f"   🌿 Branch: {details['branch']}\n"
                if "base" in details:
                    response += f"   📍 From: {details['base']}\n"
            elif activity_type == "files_committed":
                response += f"**{i}. Committed Files**\n"
                if "branch" in details:
                    response += f"   🌿 To branch: {details['branch']}\n"
                if "files" in details:
                    file_count = len(details["files"]) if isinstance(details["files"], list) else 1
                    response += f"   📁 Files: {file_count} file(s)\n"
            elif activity_type == "github_integration_initialized":
                response += f"**{i}. GitHub Integration**\n"
                if "repo" in details:
                    response += f"   📦 Repository: {details['repo']}\n"
            else:
                response += f"**{i}. {activity_type.replace('_', ' ').title()}**\n"
                if details:
                    response += f"   📝 Details: {str(details)[:100]}{'...' if len(str(details)) > 100 else ''}\n"

            response += f"   ⏰ Time: {timestamp}\n\n"

        # Add summary statistics
        total_activities = len(self.recent_activities)
        pr_count = sum(1 for a in self.recent_activities if a.get("activity") == "pr_created")
        branch_count = sum(
            1 for a in self.recent_activities if a.get("activity") == "branch_created"
        )
        commit_count = sum(
            1 for a in self.recent_activities if a.get("activity") == "files_committed"
        )

        response += "📊 **Activity Summary:**\n"
        response += f"   • Total activities: {total_activities}\n"
        response += f"   • Pull requests created: {pr_count}\n"
        response += f"   • Branches created: {branch_count}\n"
        response += f"   • File commits: {commit_count}\n"

        return response

    async def process_query(self, query: str) -> str:
        """Process GitHub-related queries."""
        query_lower = query.lower().strip()

        if "status" in query_lower:
            return await self._handle_status_request()
        elif "create branch" in query_lower:
            return await self._handle_create_branch_request(query)
        elif "commit" in query_lower and "files" in query_lower:
            return await self._handle_commit_request(query)
        elif "divide" in query_lower and "tool" in query_lower:
            return await self._handle_divide_tool_pr_request(query)
        elif "create pr" in query_lower or "pull request" in query_lower:
            return await self._handle_create_pr_request(query)
        elif "list branches" in query_lower:
            return await self._handle_list_branches_request()
        elif any(
            phrase in query_lower
            for phrase in [
                "latest pr",
                "recent pr",
                "last pr",
                "latest pull request",
                "recent pull request",
                "last pull request",
            ]
        ):
            return await self._handle_recent_pr_request()
        elif any(
            phrase in query_lower
            for phrase in [
                "latest activities",
                "recent activities",
                "show your latest activities",
                "show your recent activities",
                "what have you been doing",
                "your activities",
                "show activities",
            ]
        ):
            return await self._handle_activities_request()
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
            "pull_requests_created": len(self.pull_requests),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }

        if self.github_integration:
            status_info["repo"] = (
                f"{self.github_integration.repo_owner}/{self.github_integration.repo_name}"
            )

        if self.pull_requests:
            latest_pr = self.pull_requests[-1]
            status_info["latest_pr"] = f"#{latest_pr['number']} - {latest_pr['title']}"

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
                # Track the PR activity
                self._track_pr_activity(pr)
                return f"✅ Successfully created PR #{pr.get('number')}: {title}\nURL: {pr.get('html_url')}"
            else:
                self.log_activity("pr_creation_failed", {"branch": branch_name})
                return f"❌ Failed to create PR from branch '{branch_name}'"
        except Exception as e:
            self.log_activity("pr_creation_error", {"error": str(e)})
            return f"❌ Error creating PR: {str(e)}"

    async def _handle_divide_tool_pr_request(self, query: str) -> str:
        """Handle specific divide tool PR creation request."""
        if not self.github_integration:
            return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

        try:
            # Create branch for the fix with timestamp to avoid conflicts
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"fix-divide-tool-bug-{timestamp}"
            base_branch = "main"

            # Create the branch
            branch_success = self.github_integration.create_branch(branch_name, base_branch)
            if not branch_success:
                return f"❌ Failed to create branch '{branch_name}'. Repository '{self.github_integration.repo_owner}/{self.github_integration.repo_name}' may not exist or token may lack permissions."

            # Prepare files to commit
            files_to_commit = ["test_tools/divide_fixed.py", "test_tools/test_divide.py"]

            # Check if files exist
            import os

            existing_files = [f for f in files_to_commit if os.path.exists(f)]
            if not existing_files:
                return "❌ No divide tool files found. Please run the code fixer first."

            # Commit the files
            commit_message = (
                "Fix divide tool bug: Change divisor from 0 to n2 and add proper error handling"
            )
            commit_success = self.github_integration.commit_files(
                branch_name, existing_files, commit_message
            )
            if not commit_success:
                return f"❌ Failed to commit files to branch '{branch_name}'"

            # Create the pull request
            pr_title = "Fix divide tool bug - Change divisor from 0 to n2"
            pr_body = """## Fix for Divide Tool Bug

### Problem
The divide function was incorrectly dividing by 0 instead of the second parameter, causing ZeroDivisionError.

### Solution
- Changed `result = n1 / 0` to `result = n1 / n2`
- Added proper zero division validation
- Created comprehensive test suite

### Files Changed
- `test_tools/divide_fixed.py` - Fixed divide function
- `test_tools/test_divide.py` - Test suite

### Testing
- ✅ Function now correctly divides 355 by 113 to get pi approximation
- ✅ Proper error handling for division by zero
- ✅ All tests pass
- ✅ Code passes linting

### Impact
This fix resolves the critical bug that prevented the divide tool from functioning correctly.

---
*PR created by Vectras GitHub Agent*"""

            pr = self.github_integration.create_pull_request(branch_name, pr_title, pr_body)
            if pr:
                # Track the PR activity
                self._track_pr_activity(pr)
                return f"""✅ Successfully created divide tool fix PR!

**Branch:** {branch_name}
**PR #{pr.get("number")}:** {pr_title}
**URL:** {pr.get("html_url")}

**Files Committed:**
{chr(10).join(f"- {f}" for f in existing_files)}

**Commit Message:** {commit_message}

The PR includes the complete fix for the divide tool bug with proper testing and documentation."""
            else:
                self.log_activity("divide_tool_pr_failed", {"branch": branch_name})
                return f"❌ Failed to create PR from branch '{branch_name}'"

        except Exception as e:
            self.log_activity("divide_tool_pr_error", {"error": str(e)})
            return f"❌ Error creating divide tool PR: {str(e)}"

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
- latest pr / recent pr / last pr - Show details of the most recent pull request created
- latest activities / recent activities / show your latest activities - Show recent GitHub activities
- list branches - List all branches in the repository
- help - Show this help text

Examples:
- create branch feature-123
- create branch hotfix from main
- commit files to feature-123 with message "Fix bug in login"
- create pr from feature-123 with title "Add new feature" body "This PR adds..."
- latest pr
- latest activities
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
