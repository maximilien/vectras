#!/bin/bash

# Vectras AI Setup Script
# This script sets up all dependencies for the Vectras AI project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

print_help() {
    echo -e "${BLUE}Vectras AI Setup Script${NC}"
    echo ""
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --skip-python     Skip Python dependency installation"
    echo "  --skip-node       Skip Node.js dependency installation"
    echo "  --skip-brew       Skip Homebrew dependency installation"
    echo "  --force           Force reinstall all dependencies"
    echo "  --dev             Install development dependencies"
    echo ""
    echo "This script will:"
    echo "  1. Check and install system dependencies (Homebrew, Node.js, Python)"
    echo "  2. Install Python dependencies using uv"
    echo "  3. Install Node.js dependencies for frontend linting"
    echo "  4. Set up configuration files"
    echo "  5. Create necessary directories"
    echo "  6. Run initial tests to verify setup"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                    # Full setup"
    echo "  ./setup.sh --skip-python      # Skip Python setup"
    echo "  ./setup.sh --force            # Force reinstall everything"
    echo "  ./setup.sh --dev              # Install with development dependencies"
}

# Parse command line arguments
SKIP_PYTHON=false
SKIP_NODE=false
SKIP_BREW=false
FORCE=false
DEV_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            print_help
            exit 0
            ;;
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-node)
            SKIP_NODE=true
            shift
            ;;
        --skip-brew)
            SKIP_BREW=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

print_header "Starting Vectras AI Setup..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_warning "This script is optimized for macOS. Some features may not work on other systems."
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Homebrew if not present
install_homebrew() {
    if ! command_exists brew; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        print_status "Homebrew is already installed"
    fi
}

# Function to install Node.js if not present
install_nodejs() {
    if ! command_exists node; then
        print_status "Installing Node.js..."
        brew install node
    else
        print_status "Node.js is already installed ($(node --version))"
    fi
    
    if ! command_exists npm; then
        print_error "npm not found after Node.js installation"
        exit 1
    fi
}

# Function to install Python dependencies
install_python_deps() {
    print_header "Setting up Python dependencies..."
    
    # Check if uv is installed
    if ! command_exists uv; then
        print_status "Installing uv (Python package manager)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.cargo/env
    else
        print_status "uv is already installed ($(uv --version))"
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    uv sync
    
    # Install development dependencies if requested
    if [ "$DEV_MODE" = true ]; then
        print_status "Installing development dependencies..."
        uv pip install -e ".[dev]"
    fi
    
    print_status "Python dependencies installed successfully!"
}

# Function to install Node.js dependencies
install_node_deps() {
    print_header "Setting up Node.js dependencies..."
    
    # Clean install if force flag is set
    if [ "$FORCE" = true ]; then
        print_status "Force reinstalling Node.js dependencies..."
        rm -rf node_modules package-lock.json
    fi
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Test ESLint configuration
    print_status "Testing ESLint configuration..."
    if npm run lint:js >/dev/null 2>&1; then
        print_status "✅ ESLint configuration verified"
    else
        print_warning "⚠️  ESLint found some issues (this is normal for initial setup)"
    fi
    
    print_status "Node.js dependencies installed successfully!"
}

# Function to setup configuration files
setup_config_files() {
    print_header "Setting up configuration files..."
    
    # Create config directory if it doesn't exist
    mkdir -p config
    
    # Copy config.yaml.example to config.yaml if it doesn't exist
    if [ ! -f config.yaml ]; then
        print_status "Creating config.yaml from template..."
        cp config.yaml.example config.yaml
        print_warning "Created config.yaml from template. Please edit it with your settings."
    else
        print_status "config.yaml already exists"
    fi
    
    # Create necessary directories
    print_status "Creating necessary directories..."
    mkdir -p logs frontend tools test_tools data
    
    print_status "Configuration files setup complete!"
}

# Function to setup environment file
setup_env_file() {
    if [ ! -f .env ]; then
        print_status "Creating .env file..."
        cat > .env << EOF
# Vectras AI Environment Configuration
# Copy this file and customize for your environment

# OpenAI Configuration (Required for real AI responses)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# For testing without API key (set to 1)
VECTRAS_FAKE_OPENAI=0

# Service Ports (optional - defaults shown)
VECTRAS_UI_PORT=8120
VECTRAS_API_PORT=8121
VECTRAS_MCP_PORT=8122
VECTRAS_AGENT_PORT=8123

# Service Hosts (optional - defaults shown)
VECTRAS_UI_HOST=localhost
VECTRAS_API_HOST=localhost
VECTRAS_MCP_HOST=localhost
VECTRAS_AGENT_HOST=localhost

# GitHub Configuration (optional)
GITHUB_TOKEN=your_github_token_here
GITHUB_ORG=your_github_org
GITHUB_REPO=your_github_repo

# Development/Testing
PYTHONPATH=./src
EOF
        print_warning "Created .env file. Please edit it with your API keys and settings."
    else
        print_status ".env file already exists"
    fi
}

# Function to run initial tests
run_initial_tests() {
    print_header "Running initial tests..."
    
    # Test Python setup
    print_status "Testing Python setup..."
    if uv run --active python -c "import sys; print(f'Python {sys.version}')"; then
        print_status "✅ Python setup verified"
    else
        print_error "❌ Python setup failed"
        exit 1
    fi
    
    # Test FastAPI imports
    print_status "Testing FastAPI imports..."
    if uv run --active python -c "import fastapi, uvicorn, pydantic; print('✅ FastAPI dependencies verified')"; then
        print_status "✅ FastAPI dependencies verified"
    else
        print_error "❌ FastAPI dependencies failed"
        exit 1
    fi
    
    # Test Node.js setup
    print_status "Testing Node.js setup..."
    if node --version && npm --version; then
        print_status "✅ Node.js setup verified"
    else
        print_error "❌ Node.js setup failed"
        exit 1
    fi
    
    # Run basic linting
    print_status "Running basic linting checks..."
    if ./tools/lint.sh >/dev/null 2>&1; then
        print_status "✅ Linting checks passed"
    else
        print_warning "⚠️  Some linting checks failed (this is normal for initial setup)"
    fi
    
    # Test service startup (dry run)
    print_status "Testing service configuration..."
    if [ -f start.sh ] && [ -x start.sh ]; then
        print_status "✅ Service scripts are executable"
    else
        print_warning "⚠️  Service scripts may need permissions"
    fi
}

# Function to check system requirements
check_system_requirements() {
    print_header "Checking system requirements..."
    
    # Check Python version
    if command_exists python3; then
        python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        required_version="3.11"
        if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
            print_status "✅ Python version $python_version meets requirements (>=3.11)"
        else
            print_error "❌ Python version $python_version is too old. Required: >=3.11"
            exit 1
        fi
    else
        print_error "❌ Python 3.11+ is required but not found"
        exit 1
    fi
    
    # Check available disk space (at least 500MB)
    available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 512000 ]; then
        print_error "Insufficient disk space. Need at least 500MB available."
        exit 1
    fi
    
    # Check available memory (at least 1GB)
    total_mem=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    if [ "$total_mem" -lt 1073741824 ]; then
        print_warning "Low memory detected. Some operations may be slow."
    fi
    
    print_status "System requirements check passed"
}

# Function to display next steps
display_next_steps() {
    print_header "Setup Complete! 🎉"
    echo "================================"
    print_status "Vectras AI is now ready to use!"
    echo ""
    print_status "Next steps:"
    echo "  1. Edit .env file with your API keys:"
    echo "     - OPENAI_API_KEY: Your OpenAI API key"
    echo "     - GITHUB_TOKEN: Your GitHub token (optional)"
    echo "  2. Edit config.yaml with your settings"
    echo "  3. Run './start.sh' to start all services"
    echo "  4. Visit http://localhost:8120 to access the UI"
    echo ""
    print_status "Useful commands:"
    echo "  ./start.sh              # Start all services"
    echo "  ./stop.sh               # Stop all services"
    echo "  ./test.sh               # Run tests"
    echo "  ./tools/lint.sh         # Run linting checks"
    echo "  ./tools/tail-logs.sh    # Monitor logs"
    echo ""
    print_status "Service endpoints:"
    echo "  🧪 UI:           http://localhost:8120/"
    echo "  🧪 API:          http://localhost:8121/health"
    echo "  🧪 MCP:          http://localhost:8122/health"
    echo "  🧪 Supervisor:   http://localhost:8123/health"
    echo ""
    print_status "For more information, see README.md and docs/"
}

# Main setup process
main() {
    print_header "Vectras AI Setup Process"
    echo "================================"
    
    # Check system requirements
    check_system_requirements
    
    # Install system dependencies
    if [ "$SKIP_BREW" = false ]; then
        print_header "Installing system dependencies..."
        install_homebrew
        install_nodejs
    else
        print_status "Skipping system dependency installation"
    fi
    
    # Setup configuration files
    setup_config_files
    setup_env_file
    
    # Install Python dependencies
    if [ "$SKIP_PYTHON" = false ]; then
        install_python_deps
    else
        print_status "Skipping Python dependency installation"
    fi
    
    # Install Node.js dependencies
    if [ "$SKIP_NODE" = false ]; then
        install_node_deps
    else
        print_status "Skipping Node.js dependency installation"
    fi
    
    # Run initial tests
    run_initial_tests
    
    # Display next steps
    display_next_steps
}

# Run main function
main "$@"
