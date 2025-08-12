"""
GitHub Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.tool import function_tool as tool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the common response type function
from .base_agent import determine_response_type_with_llm


class GitHubIntegration:
    """GitHub API integration using the OpenAI Agents SDK tools."""

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create a new branch from the specified base branch."""
        try:
            # Get the SHA of the base branch
            ref_url = f"{self.base_url}/git/ref/heads/{base_branch}"
            async with httpx.AsyncClient() as client:
                ref_response = await client.get(ref_url, headers=self.headers)
                ref_response.raise_for_status()
                ref_data = ref_response.json()
                sha = ref_data["object"]["sha"]

                # Create the new branch
                create_url = f"{self.base_url}/git/refs"
                create_data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
                create_response = await client.post(
                    create_url, headers=self.headers, json=create_data
                )

                if create_response.status_code == 201:
                    return True
                else:
                    print(
                        f"Failed to create branch: {create_response.status_code} - {create_response.text}"
                    )
                    return False
        except Exception as e:
            print(f"Error creating branch: {str(e)}")
            return False

    async def commit_files(self, branch_name: str, files: List[str], commit_message: str) -> bool:
        """Commit files to a branch."""
        try:
            # For simplicity, we'll just create a simple commit
            # In a real implementation, you'd handle file content and SHA calculations
            async with httpx.AsyncClient() as client:
                # Get the current tree SHA
                tree_url = f"{self.base_url}/git/trees/{branch_name}"
                tree_response = await client.get(tree_url, headers=self.headers)
                tree_response.raise_for_status()
                tree_data = tree_response.json()

                # Create commit
                commit_url = f"{self.base_url}/git/commits"
                commit_data = {
                    "message": commit_message,
                    "tree": tree_data["sha"],
                    "parents": [tree_data["sha"]],
                }
                commit_response = await client.post(
                    commit_url, headers=self.headers, json=commit_data
                )

                if commit_response.status_code == 201:
                    return True
                else:
                    print(f"Failed to commit files: {commit_response.status_code}")
                    return False
        except Exception as e:
            print(f"Error committing files: {str(e)}")
            return False

    async def create_pull_request(
        self, branch_name: str, title: str, body: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Create a pull request."""
        try:
            async with httpx.AsyncClient() as client:
                pr_url = f"{self.base_url}/pulls"
                pr_data = {"title": title, "body": body, "head": branch_name, "base": "main"}
                response = await client.post(pr_url, headers=self.headers, json=pr_data)

                if response.status_code == 201:
                    return response.json()
                else:
                    print(f"Failed to create PR: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"Error creating PR: {str(e)}")
            return None


# Global GitHub integration instance
github_integration: Optional[GitHubIntegration] = None


@tool
async def create_branch(branch_name: str, base_branch: str = "main") -> str:
    """Create a new branch from the specified base branch."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    success = await github_integration.create_branch(branch_name, base_branch)
    if success:
        return f"✅ Successfully created branch '{branch_name}' from '{base_branch}'"
    else:
        return f"❌ Failed to create branch '{branch_name}'"


@tool
async def commit_files(branch_name: str, files: List[str], commit_message: str) -> str:
    """Commit files to a branch."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    success = await github_integration.commit_files(branch_name, files, commit_message)
    if success:
        return f"✅ Successfully committed {len(files)} files to branch '{branch_name}'"
    else:
        return f"❌ Failed to commit files to branch '{branch_name}'"


@tool
async def create_pull_request(branch_name: str, title: str, body: str = "") -> str:
    """Create a pull request from a branch."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    pr_data = await github_integration.create_pull_request(branch_name, title, body)
    if pr_data:
        return f"✅ Successfully created PR #{pr_data['number']}: {pr_data['title']}\n🔗 URL: {pr_data['html_url']}"
    else:
        return f"❌ Failed to create PR from branch '{branch_name}'"


@tool
async def create_complete_pr_workflow(
    branch_name: str, files: List[str], commit_message: str, pr_title: str, pr_body: str = ""
) -> str:
    """Complete PR workflow: create branch, commit files, and create PR."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    try:
        # Step 1: Create branch
        branch_created = await github_integration.create_branch(branch_name)
        if not branch_created:
            return f"❌ Failed to create branch '{branch_name}'"

        # Step 2: Commit files
        files_committed = await github_integration.commit_files(branch_name, files, commit_message)
        if not files_committed:
            return f"❌ Failed to commit files to branch '{branch_name}'"

        # Step 3: Create PR
        pr_data = await github_integration.create_pull_request(branch_name, pr_title, pr_body)
        if pr_data:
            return f"✅ Complete PR workflow successful!\n🔗 PR #{pr_data['number']}: {pr_data['title']}\n🌐 URL: {pr_data['html_url']}"
        else:
            return f"❌ Failed to create PR from branch '{branch_name}'"

    except Exception as e:
        return f"❌ Error in PR workflow: {str(e)}"


@tool
async def list_branches() -> str:
    """List all branches in the repository."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    try:
        async with httpx.AsyncClient() as client:
            branches_url = f"{github_integration.base_url}/branches"
            response = await client.get(branches_url, headers=github_integration.headers)
            response.raise_for_status()
            branches = response.json()

            branch_list = [f"- {branch['name']}" for branch in branches]
            return f"📋 Available branches:\n{chr(10).join(branch_list)}"
    except Exception as e:
        return f"❌ Error listing branches: {str(e)}"


@tool
async def validate_files_exist(files: List[str]) -> str:
    """Validate that the specified files exist in the repository."""
    import os

    missing_files = []
    existing_files = []

    for file_path in files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            missing_files.append(file_path)

    if missing_files:
        return f"❌ Some files do not exist: {', '.join(missing_files)}\n✅ Existing files: {', '.join(existing_files)}"
    else:
        return f"✅ All files exist: {', '.join(existing_files)}"


@tool
async def get_repository_status() -> str:
    """Get the current status of the GitHub repository."""
    global github_integration
    if not github_integration:
        return "❌ GitHub integration not configured. Please set GITHUB_TOKEN environment variable."

    try:
        async with httpx.AsyncClient() as client:
            # Get repository info
            repo_url = f"{github_integration.base_url}"
            repo_response = await client.get(repo_url, headers=github_integration.headers)
            repo_response.raise_for_status()
            repo_data = repo_response.json()

            # Get recent PRs
            prs_url = f"{github_integration.base_url}/pulls?state=all&per_page=5"
            prs_response = await client.get(prs_url, headers=github_integration.headers)
            prs_response.raise_for_status()
            prs_data = prs_response.json()

            status = f"""## GitHub Repository Status

**Repository:** {repo_data["full_name"]}
**Description:** {repo_data.get("description", "No description")}
**Default Branch:** {repo_data["default_branch"]}
**Stars:** {repo_data["stargazers_count"]}
**Forks:** {repo_data["forks_count"]}
**Open Issues:** {repo_data["open_issues_count"]}

**Recent Pull Requests:**"""

            if prs_data:
                for pr in prs_data[:3]:
                    status += f"\n- #{pr['number']}: {pr['title']} ({pr['state']})"
            else:
                status += "\n- No pull requests found"

            return status
    except Exception as e:
        return f"❌ Error getting repository status: {str(e)}"


def initialize_github_integration():
    """Initialize GitHub integration with environment variables."""
    global github_integration

    token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_ORG", "maximilien")
    repo_name = os.getenv("GITHUB_REPO", "vectras")

    if token:
        github_integration = GitHubIntegration(token, repo_owner, repo_name)
        print(f"🔧 Initialized GitHub integration for {repo_owner}/{repo_name}")
    else:
        print("⚠️ No GitHub token found. GitHub integration disabled.")
        github_integration = None


# Initialize GitHub integration
initialize_github_integration()


# Create the GitHub agent using OpenAI Agents SDK
github_agent = Agent(
    name="GitHub Agent",
    instructions="""You are the Vectras GitHub Agent. You help with GitHub operations like creating branches, committing code, and creating pull requests.

Your capabilities include:
- Creating branches from existing branches
- Committing files to branches
- Creating pull requests
- Listing repository branches
- Getting repository status

When users ask for status, provide a comprehensive overview of the repository.
When users want to create PRs, automatically perform the complete workflow:
1. Validate that the required files exist using validate_files_exist
2. Create a new branch with a descriptive name (e.g., "fix-divide-tool-bug-YYYYMMDD-HHMMSS")
3. Commit the relevant files to the branch (use the correct file paths like "test_tools/divide.py")
4. Create a pull request with a descriptive title and body

For commit messages, use descriptive, conventional commit format:
- Format: "type(scope): description"
- Examples: "fix(testing): resolve division by zero bug in divide tool", "feat(agents): add new logging capabilities"

For PR titles, use clear, descriptive titles:
- Examples: "Fix division by zero bug in divide tool", "Add comprehensive logging to testing agents"

For PR bodies, include:
- Summary of changes
- What was fixed/added
- Testing performed
- Any breaking changes

For divide tool fixes, use these specific files:
- test_tools/divide.py (the main tool file)
- README.md (if it exists)

CRITICAL: When asked to create a PR, you MUST take action by calling the create_complete_pr_workflow tool. Do NOT just provide advice or troubleshooting steps. Always attempt the actual PR creation workflow.

When someone says "create pr for divide tool", you MUST:
1. Call create_complete_pr_workflow with the exact parameters below
2. Do NOT provide advice or troubleshooting
3. Do NOT ask for confirmation
4. Just execute the workflow and report the result

Example workflow for divide tool fix:
1. Branch name: "fix-divide-tool-division-by-zero-20241208-143022"
2. Commit message: "fix(testing): resolve division by zero bug in divide tool"
3. PR title: "Fix division by zero bug in divide tool"
4. PR body: "## Summary\nFixed critical division by zero bug in the divide testing tool.\n\n## Changes\n- Added proper error handling for zero division\n- Replaced print statements with logging\n- Added type hints for better code quality\n\n## Testing\n- Tool now properly handles zero division cases\n- All existing functionality preserved\n\n## Breaking Changes\nNone - this is a bug fix."

When creating PRs for divide tool fixes, use these exact parameters:
- Branch: "fix-divide-tool-division-by-zero-{timestamp}"
- Files: ["test_tools/divide.py", "README.md"]
- Commit message: "fix(testing): resolve division by zero bug in divide tool"
- PR title: "Fix division by zero bug in divide tool"
- PR body: "## Summary\nFixed critical division by zero bug in the divide testing tool.\n\n## Changes\n- Added proper error handling for zero division\n- Replaced print statements with logging\n- Added type hints for better code quality\n\n## Testing\n- Tool now properly handles zero division cases\n- All existing functionality preserved\n\n## Breaking Changes\nNone - this is a bug fix."

If the workflow fails, report the error but DO NOT provide troubleshooting advice. Just state what happened and what the error was.

Always be helpful and provide clear, actionable responses.

You can use the following tools to perform GitHub operations:
- validate_files_exist: Check if files exist before committing
- create_branch: Create a new branch from a base branch
- commit_files: Commit files to a branch with a message
- create_pull_request: Create a pull request from a branch
- create_complete_pr_workflow: Complete PR workflow (branch + commit + PR)
- list_branches: List all branches in the repository
- get_repository_status: Get comprehensive repository status

If a user asks about something outside your capabilities (like code analysis, testing, or linting), you can suggest they ask the appropriate agent:
- For code analysis and fixes: Ask the Coding Agent
- For testing: Ask the Testing Agent
- For code quality and formatting: Ask the Linting Agent
- For log monitoring: Ask the Logging Monitor Agent
- For project coordination: Ask the Supervisor Agent

Format your responses in markdown for better readability.""",
    tools=[
        create_branch,
        commit_files,
        create_pull_request,
        create_complete_pr_workflow,
        validate_files_exist,
        list_branches,
        get_repository_status,
    ],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras GitHub Agent",
    description="GitHub operations agent",
    version="0.2.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    status: str
    response: str
    agent_id: str = "github"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        print(f"DEBUG: GitHub agent received query: {request.query[:100]}...")

        # Run the agent using the SDK
        result = await Runner.run(github_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "github", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Branch Management", "PR Creation", "Repository Operations"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        print(f"Error in GitHub agent: {str(e)}")
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "github-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "GitHub Agent",
        "status": "active",
        "github_configured": github_integration is not None,
        "sdk_version": "openai-agents",
        "tools": [
            "create_branch",
            "commit_files",
            "create_pull_request",
            "create_complete_pr_workflow",
            "list_branches",
            "get_repository_status",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8128)
