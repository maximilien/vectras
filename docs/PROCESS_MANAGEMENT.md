# Process Management

Vectras uses simple scripts to manage processes.

- `start.sh`: starts API, MCP, and Agent; writes PIDs to `.pid`; logs to `logs/*`
- `stop.sh`: stops processes via PID file and frees ports
- `tools/tail-logs.sh`: tails logs and shows basic status

Ports can be controlled via `.env`:

- `VECTRAS_API_PORT` (default 8121)
- `VECTRAS_MCP_PORT` (default 8122)
- `VECTRAS_AGENT_PORT` (default 8123)

Additionally, the agent can use OpenAI if configured:

- `OPENAI_API_KEY` (required for real OpenAI calls)
- `OPENAI_MODEL` (optional, default `gpt5-mini`)


