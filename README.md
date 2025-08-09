# Vectras

Minimal scaffold for API, MCP, and Agent services with tests and scripts. Inspired by RAGme-ai structure.

## Quickstart

- Create `.env` from example and edit values:

  ```
  cp .env.example .env
  # set OPENAI_API_KEY if you want real OpenAI responses
  ```

- Start services:

  ```
  ./start.sh
  ```

- Tail logs:

  ```
  ./tools/tail-logs.sh all
  ```

- Test:

  ```
  ./test.sh
  ```

## Services
- API: `src/vectras/apis/api.py` → GET `/health`
- MCP: `src/vectras/mcp/server.py` → GET `/health`, POST `/tool/health`
- Agent: `src/vectras/agents/agent.py` → POST `/query`
- UI: `src/vectras/frontend/app.py` → GET `/` (serves `frontend/`)

Agent recognizes queries like "tell me the status on the backend" and will check API and MCP health. Otherwise it answers via OpenAI.

### OpenAI configuration
- To use real OpenAI responses, set `OPENAI_API_KEY` in your environment or `.env`.
- Optional: `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_BASE_URL`, `OPENAI_ORG_ID`.
- For local dev/tests without OpenAI, set `VECTRAS_FAKE_OPENAI=1`.

## Scripts
- `start.sh`, `stop.sh`, `test.sh`
- `tools/tail-logs.sh`, `tools/lint.sh`

## Tests
- Unit: `tests/unit/*` for API, MCP, Agent
- Integration: `tests/integration/test_system.py` spins services and validates health and agent query

## Environment
Environment variables can be placed in `.env` (see `.env.example`).

### Frontend Configuration
- `APPLICATION_TITLE` (default `Vectras AI Assistant`) - displayed in browser title bar and top navigation

### Service Configuration
- `VECTRAS_API_HOST`/`VECTRAS_API_PORT` (default `localhost:8121`)
- `VECTRAS_MCP_HOST`/`VECTRAS_MCP_PORT` (default `localhost:8122`)
- `VECTRAS_AGENT_HOST`/`VECTRAS_AGENT_PORT` (default `localhost:8123`)
- `VECTRAS_UI_HOST`/`VECTRAS_UI_PORT` (default `localhost:8120`)
- `VECTRAS_API_URL`/`VECTRAS_MCP_URL` (optional explicit URLs for agent to call)
- `VECTRAS_FAKE_OPENAI` (default `0`) to force fake LLM responses
- `OPENAI_API_KEY` and `OPENAI_MODEL` for real OpenAI usage
