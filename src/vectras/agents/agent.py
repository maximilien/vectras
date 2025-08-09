import os
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    status: str
    response: Any


def _service_urls() -> tuple[str, str]:
    # Prefer explicit URLs if provided AND valid; otherwise construct from host/port.
    api_env_url = os.getenv("VECTRAS_API_URL") or ""
    mcp_env_url = os.getenv("VECTRAS_MCP_URL") or ""

    def is_valid_url(url: str) -> bool:
        url_lc = url.strip().lower()
        return url_lc.startswith("http://") or url_lc.startswith("https://")

    if is_valid_url(api_env_url):
        api_url = api_env_url
    else:
        api_host = os.getenv("VECTRAS_API_HOST", "localhost")
        api_port = os.getenv("VECTRAS_API_PORT", "8121")
        api_url = f"http://{api_host}:{api_port}"

    if is_valid_url(mcp_env_url):
        mcp_url = mcp_env_url
    else:
        mcp_host = os.getenv("VECTRAS_MCP_HOST", "localhost")
        mcp_port = os.getenv("VECTRAS_MCP_PORT", "8122")
        mcp_url = f"http://{mcp_host}:{mcp_port}"

    return api_url, mcp_url


async def _check_api_health(client: httpx.AsyncClient) -> dict:
    api_url, _ = _service_urls()
    resp = await client.get(f"{api_url}/health", timeout=5.0)
    resp.raise_for_status()
    return resp.json()


async def _check_mcp_health(client: httpx.AsyncClient) -> dict:
    _, mcp_url = _service_urls()
    resp = await client.post(f"{mcp_url}/tool/health", json={}, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


async def _llm_answer(query: str) -> str:
    # Use OpenAI SDK when available; allow fake fast-path for tests
    if os.getenv("VECTRAS_FAKE_OPENAI", "0") == "1":
        return f"[FAKE_OPENAI_RESPONSE] You asked: {query}"

    from openai import AsyncOpenAI

    # If OPENAI_API_KEY is not set, fail with a clear message
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Either set VECTRAS_FAKE_OPENAI=1 for tests/development "
            "or provide a valid OpenAI API key in your environment or .env file."
        )

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        organization=os.getenv("OPENAI_ORG_ID") or None,
    )
    completion = await client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content or ""


def create_app() -> FastAPI:
    app = FastAPI(title="Vectras Agent", description="Agent with query interface", version="0.1.0")

    # Enable CORS for frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "agent"}

    @app.post("/query", response_model=QueryResponse)
    async def query(req: QueryRequest) -> QueryResponse:
        text = req.query.strip()
        async with httpx.AsyncClient() as client:
            if "status" in text.lower() and "backend" in text.lower():
                api = await _check_api_health(client)
                mcp = await _check_mcp_health(client)
                summary = (
                    f"API: {api.get('status')}, MCP: {('ok' if (mcp.get('success')) else 'error')}"
                )
                return QueryResponse(
                    status="success", response={"summary": summary, "api": api, "mcp": mcp}
                )

            answer = await _llm_answer(text)
            return QueryResponse(status="success", response=answer)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("VECTRAS_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("VECTRAS_AGENT_PORT", "8123"))
    uvicorn.run(app, host=host, port=port)
