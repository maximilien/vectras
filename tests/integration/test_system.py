import os
import subprocess
import sys
import time

import requests


def wait_for(url: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError(f"Service not ready: {url}")


def test_components_end_to_end(tmp_path):
    env = os.environ.copy()
    env.setdefault("VECTRAS_API_PORT", "8121")
    env.setdefault("VECTRAS_MCP_PORT", "8122")
    env.setdefault("VECTRAS_AGENT_PORT", "8123")
    env.setdefault("VECTRAS_API_HOST", "127.0.0.1")
    env.setdefault("VECTRAS_MCP_HOST", "127.0.0.1")
    env.setdefault("VECTRAS_AGENT_HOST", "127.0.0.1")
    env.setdefault("VECTRAS_FAKE_OPENAI", "1")

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.vectras.apis.api:app",
            "--host",
            env["VECTRAS_API_HOST"],
            "--port",
            env["VECTRAS_API_PORT"],
        ],
        stdout=open(logs_dir / "api.log", "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )
    mcp = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.vectras.mcp.server:app",
            "--host",
            env["VECTRAS_MCP_HOST"],
            "--port",
            env["VECTRAS_MCP_PORT"],
        ],
        stdout=open(logs_dir / "mcp.log", "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )
    agent = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.vectras.agents.supervisor:app",
            "--host",
            env["VECTRAS_AGENT_HOST"],
            "--port",
            env["VECTRAS_AGENT_PORT"],
        ],
        stdout=open(logs_dir / "agent.log", "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )

    try:
        wait_for(f"http://{env['VECTRAS_API_HOST']}:{env['VECTRAS_API_PORT']}/health")
        wait_for(f"http://{env['VECTRAS_MCP_HOST']}:{env['VECTRAS_MCP_PORT']}/health")
        wait_for(f"http://{env['VECTRAS_AGENT_HOST']}:{env['VECTRAS_AGENT_PORT']}/health")

        # Agent query about backend status triggers MCP tool + API health checks
        r = requests.post(
            f"http://{env['VECTRAS_AGENT_HOST']}:{env['VECTRAS_AGENT_PORT']}/query",
            json={"query": "tell me the status on the backend"},
            timeout=5.0,
        )
        assert r.status_code == 200
        data = r.json()["response"]
        assert data["api"]["status"] == "healthy"
        assert data["mcp"]["status"] == "healthy"

        # Direct calls as tools
        r_api = requests.get(
            f"http://{env['VECTRAS_API_HOST']}:{env['VECTRAS_API_PORT']}/health",
            timeout=3.0,
        )
        assert r_api.status_code == 200

        r_mcp = requests.post(
            f"http://{env['VECTRAS_MCP_HOST']}:{env['VECTRAS_MCP_PORT']}/tool/health",
            json={},
            timeout=3.0,
        )
        assert r_mcp.status_code == 200
        assert r_mcp.json()["success"] is True
    finally:
        for p in (agent, mcp, api):
            try:
                p.terminate()
            except Exception:
                pass
        for p in (agent, mcp, api):
            try:
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
