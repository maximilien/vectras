# Troubleshooting

- Ports busy: run `./stop.sh` to clear or kill ports 8121/8122/8123.
- Logs: `./tools/tail-logs.sh status` or tail specific logs in `logs/`.
- OpenAI errors: set `VECTRAS_FAKE_OPENAI=1` to bypass or set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default `gpt5-mini`).
- Tests: run `./test.sh`. If integration hangs, ensure uvicorn is available and ports are free.


