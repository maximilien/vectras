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
- **API key issues**: Ensure `OPENAI_API_KEY` is properly set in your configuration:
  - **Option 1**: Set in `config.yaml` under `settings.environment.openai_api_key`
  - **Option 2**: Set in `.env` file as `OPENAI_API_KEY=your_key`
  - **Option 3**: Set as environment variable: `export OPENAI_API_KEY=your_key`

## Testing

- **Run tests**: `./test.sh` for all tests
- **Fast tests**: `./test.sh integration-fast` for quick integration tests (no API key required)
- **Integration hangs**: Ensure uvicorn is available and ports are free
- **E2E tests**: Require OpenAI API key to be set

## Voice Input Issues

- **Microphone not working**: Ensure browser supports Web Speech API (Chrome, Firefox, Safari)
- **Permission denied**: Allow microphone access when prompted by the browser
- **Button not responding**: Check browser console for JavaScript errors
- **Speech recognition errors**: Try refreshing the page or restarting the browser
- **Keyboard shortcut**: Use Ctrl+Shift+M (or Cmd+Shift+M on Mac) as alternative to clicking the microphone button

## Status Indicators

The scripts use emojis to help identify issues:
- ✅ **Running**: Service is active and responding
- ❌ **Not listening**: Port is not in use (service may have crashed)
- ⚠️ **Stale PID**: Process ID exists but process is not running (clean up with restart)
- 🛑 **Stopping**: Service is being stopped
- 💀 **Force killing**: Service is being forcefully terminated


