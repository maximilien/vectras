# Vectras

A multi-agent AI system for automated code testing, error detection, and fix generation. Built with FastAPI, OpenAI, and a modular agent architecture.

## 🚀 Quickstart

1. **Setup Environment:**
   ```bash
   cp .env.example .env
   # Set OPENAI_API_KEY for real AI responses
   ```

2. **Start All Agents:**
   ```bash
   ./start.sh
   ```

3. **Run End-to-End Tests:**
   ```bash
   ./test.sh
   # Or run specific e2e test:
   python tests/integration/run_e2e_test.py
   ```

4. **Monitor Logs:**
   ```bash
   ./tools/tail-logs.sh all
   ```

## 🤖 Multi-Agent System

Vectras consists of 5 specialized AI agents working together:

### **Testing Agent** (Port 8126)
- Creates test tools with intentional bugs
- Generates integration tests
- Coordinates testing workflows
- Supports Python, JavaScript, and Bash tools

### **Log Monitor Agent** (Port 8124)
- Monitors application logs in real-time
- Detects errors, exceptions, and stack traces
- Handles error pattern recognition
- Triggers alerts and handoffs to other agents

### **Code Fixer Agent** (Port 8125)
- Analyzes code issues and stack traces
- Suggests automated fixes
- Creates GitHub branches and pull requests
- Integrates with testing and linting agents

### **Linting Agent** (Port 8127)
- Performs code quality checks
- Suggests formatting improvements
- Supports multiple linters (ruff, black, eslint, etc.)
- Auto-fixes common issues

### **GitHub Agent** (Port 8128)
- Manages version control operations
- Creates branches and pull requests
- Handles repository operations
- Integrates with code fixer for automated PRs

## 🧪 Testing

### **End-to-End Integration Tests**
```bash
# Run comprehensive e2e test with real OpenAI
python tests/integration/run_e2e_test.py

# Run with verbose output
cd tests/integration && python -m pytest test_e2e_agent_flow.py -v -s
```

### **Unit Tests**
```bash
# Run all unit tests
pytest tests/unit/

# Run specific test
pytest tests/unit/test_api.py
```

### **Test Coverage**
- ✅ Agent communication and coordination
- ✅ Error detection and analysis
- ✅ Code quality and linting
- ✅ Version control operations
- ✅ Real OpenAI integration

## 🔧 Configuration

### **Environment Variables**
```bash
# Required for real AI responses
OPENAI_API_KEY=your_api_key_here

# Optional OpenAI settings
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_ORG_ID=your_org_id

# For development/testing without OpenAI
VECTRAS_FAKE_OPENAI=1

# GitHub integration
GITHUB_TOKEN=your_github_token
```

### **Agent Configuration**
Each agent is configured in `config.yaml` with:
- System prompts and capabilities
- Model settings and temperature
- Memory and session management
- Service-specific settings

## 📁 Project Structure

```
vectras/
├── src/vectras/
│   ├── agents/           # Multi-agent system
│   │   ├── testing.py    # Test tool creation
│   │   ├── log_monitor.py # Error detection
│   │   ├── code_fixer.py # Code analysis & fixes
│   │   ├── linting.py    # Code quality
│   │   └── github.py     # Version control
│   ├── apis/             # REST APIs
│   ├── mcp/              # Model Context Protocol
│   └── frontend/         # Web interface
├── tests/
│   ├── integration/      # E2E tests
│   └── unit/            # Unit tests
├── test_tools/          # Generated test tools
├── logs/               # Application logs
└── config/             # Configuration files
```

## 🎯 Key Features

- **Multi-Agent Coordination**: Agents communicate and handoff tasks
- **Real OpenAI Integration**: Uses actual AI models for intelligent responses
- **Automated Testing**: Creates and executes test tools with bugs
- **Error Detection**: Monitors logs and detects issues automatically
- **Code Quality**: Performs linting and suggests improvements
- **Version Control**: Automated branch and PR creation
- **End-to-End Testing**: Comprehensive integration test suite

## 🚀 Development

### **Adding New Agents**
1. Create agent class in `src/vectras/agents/`
2. Add configuration to `config.yaml`
3. Update `start.sh` to include new agent
4. Add tests in `tests/unit/` and `tests/integration/`

### **Running Locally**
```bash
# Start all services
./start.sh

# Run tests
./test.sh

# Stop all services
./stop.sh
```

## 📊 Status

- ✅ **Multi-Agent System**: 5 specialized agents working together
- ✅ **E2E Testing**: Comprehensive integration test suite
- ✅ **Real OpenAI**: Full AI integration with real models
- ✅ **Error Detection**: Automated log monitoring and analysis
- ✅ **Code Quality**: Linting and formatting capabilities
- ✅ **Version Control**: GitHub integration for automated PRs
- 🔄 **Tool Creation**: Testing agent tool creation (in progress)
- 🔄 **Agent Handoffs**: Real-time agent coordination (in progress)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the e2e test suite
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
