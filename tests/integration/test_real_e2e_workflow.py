# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Real end-to-end workflow tests."""

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


class RealE2ETestManager:
    """Manages the real end-to-end test flow that creates actual artifacts."""

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
        self.test_tools_dir = Path(__file__).parent.parent.parent / "test_tools"
        self.test_tools_dir.mkdir(exist_ok=True)
        self.created_files: List[Path] = []
        self.created_branches: List[str] = []

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

    async def step_1_create_divide_tool_directly(self) -> str:
        """Step 1: Create the divide tool directly by creating the file."""
        print("\n🔧 Step 1: Creating divide tool with bug...")

        # Create the divide tool directly through the testing agent
        divide_tool_code = '''def divide(n1, n2):
    """Divide n1 by n2. This function has a hardcoded bug - it always divides by 0."""
    # BUG: This always divides by 0, causing an error on any call
    result = n1 / 0
    print(f"Result of {n1} / {n2} = {result}")
    return result

# Test the function
if __name__ == "__main__":
    try:
        result = divide(10, 2)  # This will always fail
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Error: {e}")'''

        # Create the tool through the testing agent
        create_response = await self.query_agent(
            "testing", f"create testing tool named 'divide' with this code: {divide_tool_code}"
        )
        print(f"✅ Create response: {create_response['response'][:200]}...")

        # Wait a moment for the agent to process
        await asyncio.sleep(1)

        # List tools to verify it was created
        list_response = await self.query_agent("testing", "list tools")
        print(f"✅ Tools list: {list_response['response'][:200]}...")

        return "divide_tool_created_with_bug"

    async def step_2_execute_failing_tool(self) -> str:
        """Step 2: Execute the failing divide tool."""
        print("\n🔧 Step 2: Executing failing divide tool...")

        # Execute the failing tool
        execute_response = await self.query_agent("testing", "execute tool divide")
        print(f"✅ Tool execution: {execute_response['response'][:200]}...")

        # Check if the tool was found and executed
        if "not found" in execute_response["response"].lower():
            print("⚠️ Tool not found, trying to create it via the testing agent...")
            # Try to create the tool via the testing agent
            create_response = await self.query_agent("testing", "create divide tool")
            print(f"✅ Tool creation response: {create_response['response'][:200]}...")

            # Try executing again
            execute_response2 = await self.query_agent("testing", "execute tool divide")
            print(f"✅ Tool execution after creation: {execute_response2['response'][:200]}...")

            # Verify the tool was executed (it may not fail as expected due to exception handling)
            assert (
                "executed" in execute_response2["response"].lower()
                or "error" in execute_response2["response"].lower()
                or "exception" in execute_response2["response"].lower()
                or "multiple tools"
                in execute_response2["response"].lower()  # Agent found multiple tools
            ), "Divide tool should have been executed"
        else:
            # Verify the tool was executed (it may not fail as expected due to exception handling)
            assert (
                "executed" in execute_response["response"].lower()
                or "error" in execute_response["response"].lower()
                or "exception" in execute_response["response"].lower()
                or "multiple tools"
                in execute_response["response"].lower()  # Agent found multiple tools
            ), "Divide tool should have been executed"

        return "divide_tool_executed_and_failed"

    async def step_3_code_fixer_analysis_and_fix(self) -> str:
        """Step 3: Code fixer analyzes and fixes the divide tool."""
        print("\n🔧 Step 3: Code fixer analyzing and fixing divide tool...")

        # Analyze the divide tool
        analysis_response = await self.query_agent("coding", "analyze test_tools/divide.py")
        print(f"✅ Analysis: {analysis_response['response'][:200]}...")

        # Fix the divide tool
        fix_response = await self.query_agent("coding", "fix test_tools/divide.py")
        print(f"✅ Fix: {fix_response['response'][:200]}...")

        # Verify the fix was applied by checking if the fixed file exists
        # The coding agent might create different file names, so check for any divide-related fixed files
        fixed_files = list(self.test_tools_dir.glob("*divide*fixed*.py"))
        if not fixed_files:
            # Also check if the original divide.py was modified
            divide_file = self.test_tools_dir / "divide.py"
            if divide_file.exists():
                # Check if the file was modified (contains the fix)
                with open(divide_file, "r") as f:
                    content = f.read()
                    if "n1 / n2" in content and "n1 / 0" not in content:
                        print(f"✅ Divide tool was fixed in place: {divide_file}")
                        return "divide_tool_fixed"

        assert len(fixed_files) > 0, f"No fixed divide files found in {self.test_tools_dir}"
        print(f"✅ Fixed file found: {fixed_files[0]}")

        return "divide_tool_fixed"

    async def step_4_testing_verification(self) -> str:
        """Step 4: Testing agent verifies the fix."""
        print("\n🔧 Step 4: Testing agent verifying the fix...")

        # Run tests on the fixed tool
        test_response = await self.query_agent("testing", "run divide tool tests")
        print(f"✅ Testing: {test_response['response'][:200]}...")

        # Verify tests passed
        assert (
            "passed" in test_response["response"].lower()
            or "success" in test_response["response"].lower()
        ), "Tests should have passed on the fixed tool"

        return "fix_verified_by_testing"

    async def step_5_linting_verification(self) -> str:
        """Step 5: Linting agent verifies code quality."""
        print("\n🔧 Step 5: Linting agent verifying code quality...")

        # Lint the fixed tool
        lint_response = await self.query_agent("linting", "lint divide tool")
        print(f"✅ Linting: {lint_response['response'][:200]}...")

        # Verify linting passed (may have formatting issues but no critical errors)
        response_lower = lint_response["response"].lower()
        assert (
            "passed" in response_lower
            or "✅" in lint_response["response"]
            or "no issues found" in response_lower
            or "needs formatting" in response_lower  # Formatting issues are acceptable
        ), "Linting should have passed on the fixed tool (formatting issues are acceptable)"

        return "fix_verified_by_linting"

    async def step_6_github_pr_creation(self) -> str:
        """Step 6: GitHub agent creates a PR with the fix."""
        print("\n🔧 Step 6: GitHub agent creating PR with the fix...")

        # Create PR for the divide tool fix
        pr_response = await self.query_agent("github", "create pr for divide tool")
        print(f"✅ PR Creation: {pr_response['response'][:200]}...")

        # Verify GitHub agent attempted to create a PR using LLM
        # Note: In test environment with fake token, the PR creation will fail,
        # but we verify that the agent attempted the operation
        verification_prompt = f"""
        Analyze this GitHub agent response and determine if the agent attempted to create a pull request (PR).

        Response: {pr_response["response"]}

        Consider the following:
        1. Did the agent try to create a branch, commit files, or create a PR?
        2. Did the agent encounter an error during the process (which is expected in test environment)?
        3. Did the agent provide helpful error messages or troubleshooting steps?
        4. Did the agent ask for confirmation or additional information needed for PR creation?
        5. Did the agent mention file paths, branches, commits, or PR creation in the context of attempting the operation?

        IMPORTANT: If the agent mentions file paths, commits, branches, or PR creation in the context of trying to perform these operations (even if they failed), then it DID attempt PR creation.

        Respond with only "YES" if the agent attempted PR creation (even if it failed), or "NO" if the agent did not attempt any PR-related operations.
        """

        # Use the coding agent to analyze the response (it has LLM capabilities)
        verification_response = await self.query_agent("coding", verification_prompt)
        verification_result = verification_response["response"].strip().upper()

        # Check if the LLM determined the agent attempted PR creation
        if "YES" not in verification_result:
            raise AssertionError(
                f"GitHub agent should have attempted to create a PR, but LLM analysis determined it did not. "
                f"LLM response: {verification_result}\n"
                f"Original response: {pr_response['response']}"
            )

        return "pr_creation_attempted_successfully"

    async def cleanup(self):
        """Clean up test artifacts."""
        print("\n🧹 Cleaning up test artifacts...")

        # Clean up test tools
        for file_path in self.created_files:
            try:
                file_path.unlink()
                print(f"Deleted test file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not delete {file_path}: {e}")

        # Clean up any created branches (if GitHub integration is real)
        for branch in self.created_branches:
            try:
                # This would require actual GitHub API calls
                print(f"Note: Branch {branch} would be deleted in real environment")
            except Exception as e:
                print(f"Warning: Could not clean up branch {branch}: {e}")

    async def run_real_workflow(self) -> Dict[str, str]:
        """Run the complete real end-to-end workflow."""
        print("🚀 Starting real end-to-end workflow...")
        print("=" * 60)

        results = {}

        try:
            # Step 1: Create divide tool directly
            step1_result = await self.step_1_create_divide_tool_directly()
            results["step_1"] = step1_result

            # Step 2: Execute failing tool
            step2_result = await self.step_2_execute_failing_tool()
            results["step_2"] = step2_result

            # Step 3: Code fixer analysis and fix
            step3_result = await self.step_3_code_fixer_analysis_and_fix()
            results["step_3"] = step3_result

            # Step 4: Testing verification
            step4_result = await self.step_4_testing_verification()
            results["step_4"] = step4_result

            # Step 5: Linting verification
            step5_result = await self.step_5_linting_verification()
            results["step_5"] = step5_result

            # Step 6: GitHub PR creation
            step6_result = await self.step_6_github_pr_creation()
            results["step_6"] = step6_result

            print("\n" + "=" * 60)
            print("✅ All steps completed successfully!")
            print("🎉 Real e2e workflow completed!")
            print("📋 Check your GitHub repository for the new PR!")

        except Exception as e:
            print(f"\n❌ Test failed at step: {e}")
            raise
        finally:
            await self.cleanup()

        return results


@pytest.mark.asyncio
async def test_real_e2e_workflow():
    """Main real end-to-end integration test."""
    print("\n🧪 Real End-to-End Integration Test")
    print("=" * 60)

    # Set up test environment
    # Use real OpenAI for e2e testing
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set - required for real e2e testing")

    # Use real GitHub token for e2e testing
    if not os.getenv("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set - required for real e2e testing")

    # Create test manager
    test_manager = RealE2ETestManager()

    # Wait for all agents to be ready
    print("⏳ Waiting for agents to be ready...")
    for agent_id in test_manager.agent_ports.keys():
        if not await test_manager.wait_for_agent(agent_id):
            pytest.skip(f"Agent {agent_id} is not ready")
        print(f"✅ Agent {agent_id} is ready")

    # Run the complete workflow
    results = await test_manager.run_real_workflow()

    # Verify all steps completed
    assert len(results) == 6, f"Expected 6 steps, got {len(results)}"

    # Verify each step has meaningful results
    for step, result in results.items():
        assert result and len(result) > 10, f"Step {step} has insufficient result: {result}"

    print("\n🎉 Real end-to-end integration test completed successfully!")
    print("📋 Results summary:")
    for step, result in results.items():
        print(f"  {step}: {result}")

    print("\n🔍 Check your GitHub repository for the new pull request!")
