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
  - Coding Agent - Port 8125
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

Ports can be controlled via environment variables in multiple ways:

**Option 1: config.yaml (Recommended)**
```yaml
settings:
  environment:
    vectras_ui_port: "${VECTRAS_UI_PORT:-8120}"
    vectras_api_port: "${VECTRAS_API_PORT:-8121}"
    vectras_mcp_port: "${VECTRAS_MCP_PORT:-8122}"
    vectras_agent_port: "${VECTRAS_AGENT_PORT:-8123}"
    vectras_ui_host: "${VECTRAS_UI_HOST:-localhost}"
    vectras_api_host: "${VECTRAS_API_HOST:-localhost}"
    vectras_mcp_host: "${VECTRAS_MCP_HOST:-localhost}"
    vectras_agent_host: "${VECTRAS_AGENT_HOST:-localhost}"
```

**Option 2: .env file**
```bash
VECTRAS_UI_PORT=8120
VECTRAS_API_PORT=8121
VECTRAS_MCP_PORT=8122
VECTRAS_AGENT_PORT=8123
VECTRAS_UI_HOST=localhost
VECTRAS_API_HOST=localhost
VECTRAS_MCP_HOST=localhost
VECTRAS_AGENT_HOST=localhost
```

**Option 3: Environment variables**
```bash
export VECTRAS_UI_PORT=8120
export VECTRAS_API_PORT=8121
# ... etc
```

## OpenAI Configuration

The agents can use OpenAI if configured through any of these methods:

**Option 1: config.yaml (Recommended)**
```yaml
settings:
  environment:
    openai_api_key: "${OPENAI_API_KEY}"
    openai_model: "${OPENAI_MODEL:-gpt-4o-mini}"
```

**Option 2: .env file**
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

**Option 3: Environment variables**
```bash
export OPENAI_API_KEY=your_api_key_here
export OPENAI_MODEL=gpt-4o-mini
```

## Status Indicators

The scripts use emojis to show service status:
- ✅ **Running**: Service is active and responding
- ❌ **Not listening**: Port is not in use
- ⚠️ **Stale PID**: Process ID exists but process is not running
- 🛑 **Stopping**: Service is being stopped
- 💀 **Force killing**: Service is being forcefully terminated
- 🚀 **Starting**: Service is being started
- 🔄 **Restarting**: Services are being restarted


