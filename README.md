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
   
   # Or use specific commands:
   ./start.sh start      # Start all services (default)
   ./start.sh restart    # Restart all services
   ./start.sh status     # Check service status
   ./start.sh help       # Show usage information
   ```

3. **Run Tests:**
   ```bash
   # Run all tests (unit + integration)
   ./test.sh
   
   # Run specific test types
   ./test.sh unit          # Unit tests only
   ./test.sh integration   # Integration tests only
   ./test.sh e2e           # Comprehensive e2e tests (requires OpenAI API key)
   ./test.sh e2e -v        # E2e tests with verbose output
   
   # Or run specific e2e test manually:
   python -m pytest tests/integration/test_comprehensive_e2e.py -v
   ```

4. **Monitor Logs:**
   ```bash
   ./tools/tail-logs.sh all
   ```

5. **Stop Services:**
   ```bash
   ./stop.sh
   
   # Or use specific commands:
   ./stop.sh stop        # Stop all services (default)
   ./stop.sh status      # Check service status
   ./stop.sh help        # Show usage information
   ```

## 🤖 Multi-Agent System

Vectras consists of 5 specialized AI agents working together:

### **Testing Agent** (Port 8126)
- Creates and manages testing tools with custom code
- Executes tools and captures output
- Runs tests for specific tools
- Supports Python, JavaScript, and Bash tools
- Built with OpenAI Agents SDK for enhanced capabilities

### **Logging Monitor Agent** (Port 8124)
- Monitors application logs in real-time
- Detects errors, exceptions, and stack traces
- Handles error pattern recognition and classification
- Provides structured log summaries with markdown formatting
- Built with OpenAI Agents SDK for intelligent analysis

### **Coding Agent** (Port 8125)
- Analyzes code issues and stack traces
- Suggests automated fixes and improvements
- Integrates with testing and linting agents
- Provides detailed code analysis with structured responses
- Built with OpenAI Agents SDK for enhanced code understanding

### **Linting Agent** (Port 8127)
- Performs code quality checks and formatting
- Suggests improvements and auto-fixes
- Supports multiple linters (ruff, black, eslint, etc.)
- Provides detailed linting reports with markdown formatting
- Built with OpenAI Agents SDK for intelligent code analysis

### **GitHub Agent** (Port 8128)
- Manages version control operations
- Creates branches and pull requests
- Handles repository operations and status checks
- Integrates with coding agent for automated PRs
- Built with OpenAI Agents SDK for enhanced GitHub operations

### **Supervisor Agent** (Port 8123)
- Coordinates all other agents
- Manages file operations and user settings
- Provides system-wide status and health monitoring
- Handles agent handoffs and task coordination
- Built with OpenAI Agents SDK for intelligent orchestration

## 🎨 Frontend Features

### **Modern UI/UX**
- **Collapsible Panes**: Agent card, chat list, and agent list can be collapsed for more space
- **Recent Messages**: Quick access to last 5 messages and common queries per agent
- **Visual Indicators**: Agent icons, typing indicators, and status badges
- **Smart Scrolling**: Remembers scroll position per conversation
- **Responsive Design**: Smooth animations and modern styling
- **Settings Panel**: System status monitoring with scrollable content
- **Vectras Settings**: Configuration viewer with global settings, default queries, and detailed agent configurations

### **Agent Management**
- Real-time agent status monitoring
- Agent-specific chat conversations
- Configurable default queries via `config.yaml`
- Intuitive agent selection and switching

## 🧪 Testing

### **End-to-End Integration Tests**
```bash
# Run comprehensive e2e test with real OpenAI
./test.sh e2e

# Run e2e tests with verbose output
./test.sh e2e -v

# Run manually with verbose output
python -m pytest tests/integration/test_comprehensive_e2e.py -v -s

# Run the comprehensive e2e test directly
python -m pytest tests/integration/test_comprehensive_e2e.py
```

### **Unit Tests**
```bash
# Run all unit tests
./test.sh unit

# Run manually
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
│   ├── agents/              # Multi-agent system (OpenAI Agents SDK)
│   │   ├── base_agent.py    # Common agent functionality
│   │   ├── testing.py       # Test tool creation and execution
│   │   ├── logging_monitor.py # Error detection and analysis
│   │   ├── coding.py        # Code analysis & fixes
│   │   ├── linting.py       # Code quality and formatting
│   │   ├── github.py        # Version control operations
│   │   └── supervisor.py    # Agent coordination and orchestration
│   ├── apis/                # REST APIs
│   ├── mcp/                 # Model Context Protocol
│   └── frontend/            # Web interface
├── tests/
│   ├── integration/         # E2E tests
│   └── unit/               # Unit tests (marked for SDK migration)
├── test_tools/             # Generated test tools
├── logs/                   # Application logs
├── config/                 # Configuration files
└── frontend/               # Frontend assets
```

## 🎯 Key Features

- **OpenAI Agents SDK Integration**: All agents built with the latest OpenAI Agents SDK for enhanced capabilities
- **Enhanced Response Type Detection**: Intelligent content type detection with LLM fallback for optimal frontend rendering
- **Multi-Agent Coordination**: Agents communicate and handoff tasks seamlessly
- **Real OpenAI Integration**: Uses actual AI models for intelligent responses
- **Automated Testing**: Creates and executes test tools with custom code
- **Error Detection**: Monitors logs and detects issues automatically with structured analysis
- **Code Quality**: Performs linting and suggests improvements with detailed reports
- **Version Control**: Automated branch and PR creation
- **End-to-End Testing**: Comprehensive integration test suite
- **Modern Frontend**: Responsive UI with real-time agent status monitoring

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
./start.sh restart    # Restart all services
./start.sh status     # Check service status

# Run tests
./test.sh          # All tests
./test.sh unit     # Unit tests only
./test.sh e2e      # E2E tests (requires OpenAI API key)
./test.sh e2e -v   # E2E tests with verbose output

# Stop all services
./stop.sh
./stop.sh status     # Check service status
```

## 📊 Status

- ✅ **OpenAI Agents SDK Migration**: All agents migrated to latest SDK
- ✅ **Enhanced Response Type Detection**: LLM-based content type detection implemented
- ✅ **Multi-Agent System**: 6 specialized agents working together (including Supervisor)
- ✅ **E2E Testing**: Comprehensive integration test suite with updated agent references
- ✅ **Real OpenAI Integration**: Full AI integration with real models
- ✅ **Error Detection**: Automated log monitoring and analysis with structured output
- ✅ **Code Quality**: Linting and formatting capabilities with detailed reports
- ✅ **Version Control**: GitHub integration for automated PRs
- ✅ **Agent Coordination**: Real-time agent handoffs and task coordination
- ✅ **Modern Frontend**: Responsive UI with real-time status monitoring
- ✅ **Code Quality**: All lint and format checks passing
- 🔄 **Unit Test Migration**: Unit tests marked for future SDK migration (currently skipped)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the e2e test suite
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
