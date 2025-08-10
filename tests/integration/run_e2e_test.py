# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""End-to-end test runner for Vectras agents."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import pytest

# Load environment variables from .env file
try:
    from dotenv import find_dotenv, load_dotenv

    _dotenv_path = find_dotenv(usecwd=True)
    if _dotenv_path:
        load_dotenv(dotenv_path=_dotenv_path, override=False)
        print(f"📄 Loaded environment from: {_dotenv_path}")
except ImportError:
    print("⚠️ python-dotenv not available, skipping .env file loading")


class AgentManager:
    """Manages the lifecycle of all agents for testing."""

    def __init__(self):
        self.agents = {
            "testing": {"port": 8126, "module": "src.vectras.agents.testing:app"},
            "log-monitor": {"port": 8124, "module": "src.vectras.agents.log_monitor:app"},
            "code-fixer": {"port": 8125, "module": "src.vectras.agents.code_fixer:app"},
            "linting": {"port": 8127, "module": "src.vectras.agents.linting:app"},
            "github": {"port": 8128, "module": "src.vectras.agents.github:app"},
        }
        self.processes: List[subprocess.Popen] = []
        self.base_dir = Path(__file__).parent.parent.parent

    def start_agents(self) -> bool:
        """Start all agents."""
        print("🚀 Starting Vectras agents...")

        # Set environment variables
        env = os.environ.copy()
        # Use real OpenAI for e2e testing
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY not set - required for e2e testing")
            print("Please set your OpenAI API key:")
            print("export OPENAI_API_KEY=your_api_key_here")
            return False
        env.setdefault("GITHUB_TOKEN", "fake_token_for_testing")

        for agent_name, config in self.agents.items():
            try:
                print(f"  Starting {agent_name} agent on port {config['port']}...")

                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        config["module"],
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(config["port"]),
                        "--log-level",
                        "warning",
                    ],
                    cwd=self.base_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                self.processes.append(process)
                print(f"    ✅ {agent_name} agent started (PID: {process.pid})")

            except Exception as e:
                print(f"    ❌ Failed to start {agent_name} agent: {e}")
                return False

        # Wait a bit for agents to start
        print("⏳ Waiting for agents to initialize...")
        time.sleep(3)

        return True

    def stop_agents(self):
        """Stop all agents."""
        print("🛑 Stopping Vectras agents...")

        for i, process in enumerate(self.processes):
            agent_name = list(self.agents.keys())[i]
            try:
                print(f"  Stopping {agent_name} agent (PID: {process.pid})...")
                process.terminate()

                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"    ✅ {agent_name} agent stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"    ⚠️ {agent_name} agent didn't stop gracefully, killing...")
                    process.kill()
                    process.wait()
                    print(f"    ✅ {agent_name} agent killed")

            except Exception as e:
                print(f"    ❌ Error stopping {agent_name} agent: {e}")

    def check_agent_health(self) -> bool:
        """Check if all agents are healthy."""
        import httpx

        print("🏥 Checking agent health...")

        for agent_name, config in self.agents.items():
            try:
                url = f"http://127.0.0.1:{config['port']}/health"
                response = httpx.get(url, timeout=5)

                if response.status_code == 200:
                    print(f"  ✅ {agent_name} agent is healthy")
                else:
                    print(f"  ❌ {agent_name} agent health check failed: {response.status_code}")
                    return False

            except Exception as e:
                print(f"  ❌ {agent_name} agent health check failed: {e}")
                return False

        return True


def run_e2e_test():
    """Run the end-to-end test."""
    print("🧪 Vectras End-to-End Integration Test")
    print("=" * 50)

    # Create agent manager
    manager = AgentManager()

    try:
        # Start agents
        if not manager.start_agents():
            print("❌ Failed to start agents")
            return False

        # Check agent health
        if not manager.check_agent_health():
            print("❌ Agent health check failed")
            return False

        print("✅ All agents are ready!")
        print("\n" + "=" * 50)

        # Run the e2e test
        print("🚀 Running end-to-end integration test...")

        # Change to the tests directory
        test_dir = Path(__file__).parent
        os.chdir(test_dir)

        # Run the test
        result = pytest.main(
            ["test_e2e_agent_flow.py", "-v", "--tb=short", "--no-header", "--no-summary"]
        )

        if result == 0:
            print("\n🎉 End-to-end test completed successfully!")
            return True
        else:
            print(f"\n❌ End-to-end test failed with exit code: {result}")
            return False

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    finally:
        # Always stop agents
        manager.stop_agents()


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Vectras End-to-End Integration Test Runner

Usage:
    python run_e2e_test.py          # Run the full e2e test
    python run_e2e_test.py --help   # Show this help

Requirements:
    - OPENAI_API_KEY environment variable must be set
    - Valid OpenAI API key for real agent interactions

This script:
1. Starts all Vectras agents (testing, log-monitor, code-fixer, linting, github)
2. Verifies agent health
3. Runs the comprehensive end-to-end test with real OpenAI
4. Cleans up and stops all agents

The test verifies the complete flow:
- Testing agent creates a failing tool (divide by zero)
- Testing agent executes the tool, causing an error
- Log monitor agent detects the error and hands off to code fixer
- Code fixer agent analyzes and fixes the code
- Code fixer asks testing and linting agents to verify the fix
- GitHub agent creates a branch and PR with the fix
""")
        return

    success = run_e2e_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
