# Vectras Settings Panel

## Overview

The Vectras Settings panel provides a comprehensive configuration viewer for the Vectras multi-agent system. It displays all settings from `config.yaml` in an organized, user-friendly interface. The system supports multiple configuration approaches:

- **config.yaml**: Primary configuration file with environment variable substitution
- **.env file**: Traditional environment variable file
- **Environment variables**: Direct system environment variables

Configuration priority: Environment variables > .env file > config.yaml

## Features

### 🌐 Global Settings
- Displays all system-wide configuration settings
- Shows key-value pairs in a clean, readable format
- Handles different data types (strings, numbers, booleans, arrays, objects)

### 🔍 Default Queries
- Lists all configured default queries for the recent messages feature
- Shows each query in a dedicated row for easy reading

### 🤖 Agents Configuration
- **Agent Selector**: Dropdown menu with agent icons to choose which agent's configuration to view
- **Detailed Agent View**: Comprehensive agent information including:
  - Basic Information (name, description, enabled status, model, temperature, max tokens, port)
  - Capabilities (displayed as colored tags)
  - Tags (displayed as styled badges)
  - Memory Configuration (nested settings)
  - Agent Settings (nested configuration)

### 🖥️ System Status (Collapsible)
- Core services health monitoring
- Agent services status
- System information and statistics
- Manual refresh capability

## Access Methods

### Via Hamburger Menu
1. Click the ☰ hamburger menu button
2. Select "⚙️ Settings"
3. Vectras Settings panel slides in from the left

### Panel Behavior
- **Animation**: Slides in from left to right
- **Width**: 50% of viewport width
- **Close**: Click X button, click outside panel, or press Escape key

## Security Features

- **Sensitive Data Redaction**: Automatically redacts:
  - API tokens and keys
  - System prompts
  - Long alphanumeric strings that might be secrets
- **Safe Configuration Display**: Only shows configuration data that is safe to expose

## Technical Implementation

### API Endpoint
- **URL**: `/api/config`
- **Method**: GET
- **Response**: JSON containing `default_queries`, `settings`, and `agents` arrays
- **Configuration Sources**: Reads from config.yaml with environment variable substitution

### Frontend Components
- **Dual Panel System**: Separate panels for System Status and Vectras Settings
- **Configuration Sections**: Organized sections for different config types
- **Agent Selector**: Interactive dropdown with agent icons
- **Responsive Design**: Adapts to different screen sizes

### Data Formatting
- **Key Formatting**: Converts snake_case to Title Case for display
- **Value Formatting**: Handles different data types appropriately:
  - Booleans: "Yes"/"No"
  - Arrays: Formatted as lists
  - Objects: JSON-formatted with proper indentation
  - Strings: Quoted for clarity

## Configuration Files

### config.yaml
The primary configuration file containing:
- Agent configurations with system prompts and capabilities
- Global settings and defaults
- Environment variable references using `${VAR_NAME}` syntax
- Memory and session management settings

### config.yaml.example
Comprehensive example file with:
- Detailed comments explaining each setting
- Environment variable reference section
- Usage examples and best practices
- Complete documentation of all available options

### .env.example
Traditional environment variable file with:
- All available environment variables
- Detailed comments and usage instructions
- Quick start guide
- Development vs production configurations

## Future Enhancements

The current implementation is read-only. Future versions may include:
- **Edit Mode**: Ability to modify configuration values
- **Save Functionality**: Write changes back to `config.yaml`
- **Validation**: Real-time validation of configuration changes
- **Backup**: Automatic backup before making changes
- **Search**: Search functionality across all configuration sections
- **Enhanced Response Type Detection**: LLM-based content type detection for optimal frontend rendering
- **OpenAI Agents SDK Integration**: All agents now use the latest SDK for enhanced capabilities

## Usage Examples

### Viewing Agent Configuration
1. Open Vectras Settings via hamburger menu
2. Scroll to "🤖 Agents Configuration" section
3. Select an agent from the dropdown
4. View detailed configuration including capabilities, memory settings, and agent-specific settings

### Checking System Status
1. Open Vectras Settings
2. Scroll to "🖥️ System Status" section
3. Click the toggle button to expand
4. View service health and system information
5. Click "🔄 Refresh Status" to update

### Viewing Global Settings
1. Open Vectras Settings
2. The "🌐 Global Settings" section is displayed at the top
3. All global configuration values are shown in key-value format
