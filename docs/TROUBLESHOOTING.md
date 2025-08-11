# Troubleshooting

## Process Management

- **Ports busy**: Run `./stop.sh` to clear or kill all Vectras ports (8120-8128)
- **Check service status**: Use `./start.sh status` or `./stop.sh status` to see which services are running
- **Restart services**: Use `./start.sh restart` to stop and start all services
- **Process identification**: Scripts now show process names alongside PIDs for better debugging

## Logs and Monitoring

- **View all logs**: `./tools/tail-logs.sh all`
- **Check specific logs**: Tail specific logs in `logs/` directory
- **Service status**: Use status commands to see which services are running and on which ports

## OpenAI Configuration

- **OpenAI errors**: Set `VECTRAS_FAKE_OPENAI=1` to bypass or set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default `gpt-4o-mini`)
- **API key issues**: Ensure `OPENAI_API_KEY` is properly set in `.env` file

## Testing

- **Run tests**: `./test.sh` for all tests
- **Integration hangs**: Ensure uvicorn is available and ports are free
- **E2E tests**: Require OpenAI API key to be set

## Status Indicators

The scripts use emojis to help identify issues:
- ✅ **Running**: Service is active and responding
- ❌ **Not listening**: Port is not in use (service may have crashed)
- ⚠️ **Stale PID**: Process ID exists but process is not running (clean up with restart)
- 🛑 **Stopping**: Service is being stopped
- 💀 **Force killing**: Service is being forcefully terminated


