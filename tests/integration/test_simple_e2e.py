# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Simple end-to-end tests."""

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pytest

# Load environment variables from .env file
try:
    from dotenv import find_dotenv, load_dotenv

    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(dotenv_path=_dotenv_path, override=False)
except ImportError:
    pass


class SimpleE2ETestManager:
    """Manages a simple end-to-end test flow."""

    def __init__(self, base_url: str = "http://127.0.0.1"):
        self.base_url = base_url
        self.agent_ports = {
            "testing": 8126,
            "logging-monitor": 8124,
            "coding": 8125,
            "linting": 8127,
            "github": 8128,
        }
        self.agent_urls = {agent: f"{base_url}:{port}" for agent, port in self.agent_ports.items()}
        self.test_tools_dir = Path("./test_tools")
        self.test_tools_dir.mkdir(exist_ok=True)
        self.created_files: List[Path] = []

    async def wait_for_agent(self, agent_id: str, timeout: float = 30.0) -> bool:
        """Wait for an agent to be ready."""
        url = f"{self.agent_urls[agent_id]}/health"
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=1.0)
                    if response.status_code == 200:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)

        return False

    async def query_agent(self, agent_id: str, query: str, context: Optional[Dict] = None) -> Dict:
        """Send a query to an agent and return the response."""
        url = f"{self.agent_urls[agent_id]}/query"
        payload = {"query": query}
        if context:
            payload["context"] = context

        print(f"🔍 Querying {agent_id} agent: {query[:100]}...")

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            print(f"✅ {agent_id} agent response: {result.get('response', '')[:200]}...")
            return result

    async def step_1_test_agent_capabilities(self) -> str:
        """Step 1: Test basic agent capabilities."""
        print("\n🔧 Step 1: Testing basic agent capabilities...")

        # Test testing agent status
        status_response = await self.query_agent("testing", "status")
        print(f"✅ Testing agent status: {status_response['response'][:200]}...")

        # Test coding agent capabilities
        fixer_response = await self.query_agent("coding", "what can you do?")
        print(f"✅ Coding agent capabilities: {fixer_response['response'][:200]}...")

        # Test linting agent capabilities
        linting_response = await self.query_agent("linting", "what do you do?")
        print(f"✅ Linting agent capabilities: {linting_response['response'][:200]}...")

        # Test GitHub agent capabilities
        github_response = await self.query_agent("github", "how do you create a PR?")
        print(f"✅ GitHub agent capabilities: {github_response['response'][:200]}...")

        return "agent_capabilities_tested"

    async def step_2_create_simple_buggy_code(self) -> str:
        """Step 2: Create a simple buggy code file."""
        print("\n🔧 Step 2: Creating simple buggy code...")

        # Create a simple buggy Python file
        buggy_code = '''def add_numbers(a, b):
    """Add two numbers. This function has a bug - it always returns 42."""
    # BUG: This should return a + b, not 42
    return 42

# Test the function
if __name__ == "__main__":
    result = add_numbers(5, 3)
    print(f"5 + 3 = {result}")  # Should be 8, but will be 42
'''

        buggy_file = self.test_tools_dir / "buggy_add.py"
        with open(buggy_file, "w") as f:
            f.write(buggy_code)

        self.created_files.append(buggy_file)
        print(f"✅ Created buggy code file: {buggy_file}")

        return "buggy_code_created"

    async def step_3_code_fixer_analysis(self) -> str:
        """Step 3: Coding agent analyzes the buggy code."""
        print("\n🔧 Step 3: Coding agent analyzing buggy code...")

        # Analyze the buggy code
        analysis_response = await self.query_agent(
            "coding",
            "analyze this code: def add_numbers(a, b): return 42  # This should return a + b",
        )
        print(f"✅ Code analysis: {analysis_response['response'][:200]}...")

        # Verify we get a meaningful response
        assert len(analysis_response["response"]) > 10, (
            "Coding agent should provide meaningful analysis"
        )

        return "code_analysis_completed"

    async def step_4_linting_check(self) -> str:
        """Step 4: Linting agent checks code quality."""
        print("\n🔧 Step 4: Linting agent checking code quality...")

        # Check if the buggy file exists and lint it
        if (self.test_tools_dir / "buggy_add.py").exists():
            lint_response = await self.query_agent("linting", "lint test_tools/buggy_add.py")
            print(f"✅ Linting result: {lint_response['response'][:200]}...")
        else:
            # If file doesn't exist, just test the linting agent's capabilities
            lint_response = await self.query_agent("linting", "how do you check code quality?")
            print(f"✅ Linting capabilities: {lint_response['response'][:200]}...")

        # Verify we get a meaningful response
        assert len(lint_response["response"]) > 10, (
            "Linting agent should provide meaningful response"
        )

        return "linting_check_completed"

    async def step_5_github_pr_creation(self) -> str:
        """Step 5: GitHub agent creates a PR."""
        print("\n🔧 Step 5: GitHub agent creating PR...")

        # Try to create a PR for the bug fix
        pr_response = await self.query_agent(
            "github",
            "create pr from main with title 'Fix buggy add function' body 'This PR fixes the add_numbers function to return the correct sum instead of always returning 42.'",
        )
        print(f"✅ PR Creation: {pr_response['response'][:200]}...")

        # Verify we get a meaningful response
        assert len(pr_response["response"]) > 10, (
            "GitHub agent should provide meaningful PR creation response"
        )

        return "pr_creation_attempted"

    async def cleanup(self):
        """Clean up test artifacts."""
        print("\n🧹 Cleaning up test artifacts...")

        # Clean up test files
        for file_path in self.created_files:
            try:
                file_path.unlink()
                print(f"Deleted test file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")

    async def run_simple_workflow(self) -> Dict[str, str]:
        """Run the simple end-to-end workflow."""
        print("🚀 Starting simple end-to-end workflow...")
        print("=" * 60)

        results = {}

        try:
            # Step 1: Test agent capabilities
            step1_result = await self.step_1_test_agent_capabilities()
            results["step_1"] = step1_result

            # Step 2: Create buggy code
            step2_result = await self.step_2_create_simple_buggy_code()
            results["step_2"] = step2_result

            # Step 3: Code fixer analysis
            step3_result = await self.step_3_code_fixer_analysis()
            results["step_3"] = step3_result

            # Step 4: Linting check
            step4_result = await self.step_4_linting_check()
            results["step_4"] = step4_result

            # Step 5: GitHub PR creation
            step5_result = await self.step_5_github_pr_creation()
            results["step_5"] = step5_result

            print("\n" + "=" * 60)
            print("✅ All steps completed successfully!")
            print("🎉 Simple e2e workflow completed!")

        except Exception as e:
            print(f"\n❌ Test failed at step: {e}")
            raise
        finally:
            await self.cleanup()

        return results


@pytest.mark.asyncio
async def test_simple_e2e_workflow():
    """Main simple end-to-end integration test."""
    print("\n🧪 Simple End-to-End Integration Test")
    print("=" * 60)

    # Set up test environment
    # Use real OpenAI for e2e testing
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set - required for simple e2e testing")
    os.environ.setdefault("GITHUB_TOKEN", "fake_token_for_testing")

    # Create test manager
    test_manager = SimpleE2ETestManager()

    # Wait for all agents to be ready
    print("⏳ Waiting for agents to be ready...")
    for agent_id in test_manager.agent_ports.keys():
        if not await test_manager.wait_for_agent(agent_id):
            pytest.skip(f"Agent {agent_id} is not ready")
        print(f"✅ Agent {agent_id} is ready")

    # Run the complete workflow
    results = await test_manager.run_simple_workflow()

    # Verify all steps completed
    assert len(results) == 5, f"Expected 5 steps, got {len(results)}"

    # Verify each step has meaningful results
    for step, result in results.items():
        assert result and len(result) > 10, f"Step {step} has insufficient result: {result}"

    print("\n🎉 Simple end-to-end integration test completed successfully!")
    print("📋 Results summary:")
    for step, result in results.items():
        print(f"  {step}: {result}")

    print("\n🔍 Check your GitHub repository for any new pull requests!")
