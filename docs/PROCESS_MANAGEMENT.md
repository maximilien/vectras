# Process Management

Vectras uses enhanced scripts to manage processes with improved status reporting and process identification.

## Scripts

### `start.sh`
Starts all Vectras services with enhanced features:
- **Commands**: `start` (default), `restart`, `status`, `help`
- **Features**: 
  - Shows process names alongside PIDs
  - Uses emojis for status indicators (✅ ❌ ⚠️)
  - Restart functionality to stop and start all services
  - Status command to check service health
  - Help command with usage information
- **Services started**:
  - UI (Frontend) - Port 8120
  - API - Port 8121
  - MCP Server - Port 8122
  - Supervisor Agent - Port 8123
  - Log Monitor Agent - Port 8124
  - Code Fixer Agent - Port 8125
  - Testing Agent - Port 8126
  - Linting Agent - Port 8127
  - GitHub Agent - Port 8128

### `stop.sh`
Stops all Vectras services with enhanced features:
- **Commands**: `stop` (default), `status`, `help`
- **Features**:
  - Shows process names alongside PIDs
  - Uses emojis for status indicators (✅ ❌ ⚠️)
  - Status command to check service health
  - Help command with usage information
  - Graceful shutdown with force kill fallback

### `tools/tail-logs.sh`
Tails logs and shows basic status for monitoring.

## Usage Examples

```bash
# Start all services
./start.sh

# Restart all services
./start.sh restart

# Check status of all services
./start.sh status
./stop.sh status

# Get help
./start.sh help
./stop.sh help

# Stop all services
./stop.sh
```

## Port Configuration

Ports can be controlled via `.env`:

- `VECTRAS_UI_PORT` (default 8120)
- `VECTRAS_API_PORT` (default 8121)
- `VECTRAS_MCP_PORT` (default 8122)
- `VECTRAS_AGENT_PORT` (default 8123)
- `VECTRAS_API_HOST` (default localhost)
- `VECTRAS_MCP_HOST` (default localhost)
- `VECTRAS_AGENT_HOST` (default localhost)
- `VECTRAS_UI_HOST` (default localhost)

## OpenAI Configuration

The agents can use OpenAI if configured:

- `OPENAI_API_KEY` (required for real OpenAI calls)
- `OPENAI_MODEL` (optional, default `gpt-4o-mini`)

## Status Indicators

The scripts use emojis to show service status:
- ✅ **Running**: Service is active and responding
- ❌ **Not listening**: Port is not in use
- ⚠️ **Stale PID**: Process ID exists but process is not running
- 🛑 **Stopping**: Service is being stopped
- 💀 **Force killing**: Service is being forcefully terminated
- 🚀 **Starting**: Service is being started
- 🔄 **Restarting**: Services are being restarted


