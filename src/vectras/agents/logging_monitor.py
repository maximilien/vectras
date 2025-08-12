"""
Logging Monitor Agent using OpenAI Agents SDK

This demonstrates how to migrate from the custom agent implementation
to using the OpenAI Agents SDK for better tool management, handoffs, and tracing.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# OpenAI Agents SDK imports
from agents import Agent, Runner
from agents.tool import function_tool as tool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .base_agent import determine_response_type_with_llm


class LogEntry:
    """Represents a log entry with metadata."""

    def __init__(
        self, file_path: str, line_number: int, content: str, timestamp: Optional[datetime] = None
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.severity = self._detect_severity(content)
        self.error_type = self._detect_error_type(content)

    def _detect_severity(self, content: str) -> str:
        """Detect log severity level."""
        content_upper = content.upper()
        if any(level in content_upper for level in ["CRITICAL", "FATAL"]):
            return "critical"
        elif "ERROR" in content_upper:
            return "error"
        elif "WARNING" in content_upper or "WARN" in content_upper:
            return "warning"
        elif "INFO" in content_upper:
            return "info"
        else:
            return "debug"

    def _detect_error_type(self, content: str) -> Optional[str]:
        """Detect the type of error from content."""
        error_patterns = {
            "exception": r"Exception|Error:|Traceback",
            "http_error": r"HTTP.*[45]\d\d|status.*[45]\d\d",
            "connection_error": r"connection.*failed|timeout|refused",
            "import_error": r"ImportError|ModuleNotFoundError",
            "syntax_error": r"SyntaxError|IndentationError",
            "permission_error": r"PermissionError|Access.*denied",
            "file_error": r"FileNotFoundError|No such file",
        }

        for error_type, pattern in error_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                return error_type

        return None

    @property
    def is_error(self) -> bool:
        """Check if this log entry represents an error."""
        return self.severity in ["error", "critical"] or self.error_type is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "error_type": self.error_type,
            "is_error": self.is_error,
        }


class LogMonitorManager:
    """Manages log monitoring operations."""

    def __init__(self):
        self.logs_directory = Path("./logs")
        self.log_entries: List[LogEntry] = []
        self.error_count = 0
        self.warning_count = 0
        self.last_check = datetime.now()

    def _find_log_files(self) -> List[Path]:
        """Find all log files in the logs directory."""
        log_files = []

        if not self.logs_directory.exists():
            return log_files

        # Look for common log file patterns
        patterns = ["*.log", "*.txt", "*.out", "*.err"]

        for pattern in patterns:
            log_files.extend(self.logs_directory.glob(pattern))

        # Also look in subdirectories
        for subdir in self.logs_directory.iterdir():
            if subdir.is_dir():
                for pattern in patterns:
                    log_files.extend(subdir.glob(pattern))

        return log_files

    def _parse_log_file(self, file_path: Path) -> List[LogEntry]:
        """Parse a log file and extract entries."""
        entries = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        # Try to extract timestamp from the beginning of the line
                        timestamp = None
                        content = line

                        # Common timestamp patterns
                        timestamp_patterns = [
                            r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
                            r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})",
                            r"^(\d{2}:\d{2}:\d{2})",
                        ]

                        for pattern in timestamp_patterns:
                            match = re.match(pattern, line)
                            if match:
                                try:
                                    timestamp_str = match.group(1)
                                    if len(timestamp_str) == 8:  # HH:MM:SS
                                        timestamp = datetime.strptime(timestamp_str, "%H:%M:%S")
                                        # Use today's date
                                        today = datetime.now().date()
                                        timestamp = datetime.combine(today, timestamp.time())
                                    else:
                                        timestamp = datetime.strptime(
                                            timestamp_str, "%Y-%m-%d %H:%M:%S"
                                        )
                                    content = line[match.end() :].strip()
                                    break
                                except ValueError:
                                    continue

                        entry = LogEntry(
                            file_path=str(file_path),
                            line_number=line_number,
                            content=content,
                            timestamp=timestamp,
                        )
                        entries.append(entry)

        except Exception as e:
            print(f"Error parsing log file {file_path}: {e}")

        return entries

    async def check_logs(self) -> str:
        """Check all log files for errors and issues."""
        try:
            log_files = self._find_log_files()

            if not log_files:
                return "📋 No log files found in the logs directory."

            all_entries = []
            error_entries = []
            warning_entries = []

            for log_file in log_files:
                entries = self._parse_log_file(log_file)
                all_entries.extend(entries)

                for entry in entries:
                    if entry.is_error:
                        error_entries.append(entry)
                    elif entry.severity == "warning":
                        warning_entries.append(entry)

            # Update counts
            self.error_count = len(error_entries)
            self.warning_count = len(warning_entries)
            self.last_check = datetime.now()

            # Store recent entries
            self.log_entries = sorted(all_entries, key=lambda x: x.timestamp, reverse=True)[:100]

            status = f"""## Log Check Results

**Log Files Found:** {len(log_files)}
**Total Entries:** {len(all_entries)}
**Errors Found:** {self.error_count}
**Warnings Found:** {self.warning_count}
**Last Check:** {self.last_check.strftime("%Y-%m-%d %H:%M:%S")}

**Log Files:**"""

            for log_file in log_files:
                status += f"\n- {log_file.name}"

            if error_entries:
                status += "\n\n**Recent Errors:**"
                for entry in error_entries[:5]:
                    status += f"\n- **{entry.file_path}** (line {entry.line_number}): {entry.content[:100]}..."

            if warning_entries:
                status += "\n\n**Recent Warnings:**"
                for entry in warning_entries[:3]:
                    status += f"\n- **{entry.file_path}** (line {entry.line_number}): {entry.content[:100]}..."

            return status

        except Exception as e:
            return f"❌ Error checking logs: {str(e)}"

    async def check_recent_logs(self, hours: int = 1) -> str:
        """Check logs from the last N hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            recent_entries = [entry for entry in self.log_entries if entry.timestamp >= cutoff_time]

            error_entries = [entry for entry in recent_entries if entry.is_error]
            warning_entries = [entry for entry in recent_entries if entry.severity == "warning"]

            status = f"""## Recent Log Activity (Last {hours} hour{"s" if hours != 1 else ""})

**Total Entries:** {len(recent_entries)}
**Errors:** {len(error_entries)}
**Warnings:** {len(warning_entries)}
**Time Range:** {cutoff_time.strftime("%Y-%m-%d %H:%M:%S")} to {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

            if error_entries:
                status += "\n\n**Recent Errors:**"
                for entry in error_entries[:5]:
                    status += f"\n- **{entry.file_path}** ({entry.timestamp.strftime('%H:%M:%S')}): {entry.content[:100]}..."

            if warning_entries:
                status += "\n\n**Recent Warnings:**"
                for entry in warning_entries[:3]:
                    status += f"\n- **{entry.file_path}** ({entry.timestamp.strftime('%H:%M:%S')}): {entry.content[:100]}..."

            if not recent_entries:
                status += "\n\n✅ No log activity in the specified time range."

            return status

        except Exception as e:
            return f"❌ Error checking recent logs: {str(e)}"

    async def search_logs(self, search_term: str, file_pattern: Optional[str] = None) -> str:
        """Search logs for specific terms."""
        try:
            if not self.log_entries:
                await self.check_logs()

            matching_entries = []
            search_lower = search_term.lower()

            for entry in self.log_entries:
                # Check file pattern if specified
                if file_pattern and file_pattern not in entry.file_path:
                    continue

                # Check if search term matches
                if search_lower in entry.content.lower():
                    matching_entries.append(entry)

            status = f"""## Log Search Results

**Search Term:** "{search_term}"
**File Pattern:** {file_pattern or "All files"}
**Matches Found:** {len(matching_entries)}"""

            if matching_entries:
                status += "\n\n**Matching Entries:**"
                for entry in matching_entries[:10]:  # Limit to 10 results
                    status += f"\n- **{entry.file_path}** ({entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}): {entry.content[:150]}..."

                if len(matching_entries) > 10:
                    status += f"\n\n... and {len(matching_entries) - 10} more matches"
            else:
                status += "\n\n❌ No matching entries found."

            return status

        except Exception as e:
            return f"❌ Error searching logs: {str(e)}"

    async def get_error_summary(self) -> str:
        """Get a summary of errors by type."""
        try:
            if not self.log_entries:
                await self.check_logs()

            error_entries = [entry for entry in self.log_entries if entry.is_error]

            # Group errors by type
            error_types = {}
            for entry in error_entries:
                error_type = entry.error_type or "unknown"
                if error_type not in error_types:
                    error_types[error_type] = []
                error_types[error_type].append(entry)

            status = f"""## Error Summary

**Total Errors:** {len(error_entries)}
**Error Types:** {len(error_types)}"""

            if error_types:
                status += "\n\n**Errors by Type:**"
                for error_type, entries in sorted(
                    error_types.items(), key=lambda x: len(x[1]), reverse=True
                ):
                    status += f"\n- **{error_type.title()}:** {len(entries)} occurrences"

                    # Show example for each type
                    if entries:
                        example = entries[0]
                        status += f"\n  Example: {example.content[:100]}..."

            return status

        except Exception as e:
            return f"❌ Error getting error summary: {str(e)}"

    def get_status(self) -> str:
        """Get the status of the logging monitor agent."""
        status = f"""## Logging Monitor Agent Status

**Logs Directory:** {self.logs_directory}
**Total Log Entries:** {len(self.log_entries)}
**Current Error Count:** {self.error_count}
**Current Warning Count:** {self.warning_count}
**Last Check:** {self.last_check.strftime("%Y-%m-%d %H:%M:%S")}

**Available Operations:**
- Check all logs for errors and warnings
- Search logs for specific terms
- Get recent log activity
- Generate error summaries"""

        return status


# Global logging monitor manager
log_monitor_manager = LogMonitorManager()


@tool
async def check_logs() -> str:
    """Check all log files for errors and issues."""
    return await log_monitor_manager.check_logs()


@tool
async def check_recent_logs(hours: int = 1) -> str:
    """Check logs from the last N hours."""
    return await log_monitor_manager.check_recent_logs(hours)


@tool
async def search_logs(search_term: str, file_pattern: Optional[str] = None) -> str:
    """Search logs for specific terms."""
    return await log_monitor_manager.search_logs(search_term, file_pattern)


@tool
async def get_error_summary() -> str:
    """Get a summary of errors by type."""
    return await log_monitor_manager.get_error_summary()


@tool
async def get_log_monitor_status() -> str:
    """Get the current status of the logging monitor agent."""
    return log_monitor_manager.get_status()


# Create the Logging Monitor agent using OpenAI Agents SDK
log_monitor_agent = Agent(
    name="Logging Monitor Agent",
    instructions="""You are the Vectras Logging Monitor Agent. You help monitor log files for errors and issues.

Your capabilities include:
- Checking all log files for errors and warnings
- Searching logs for specific terms
- Monitoring recent log activity
- Generating error summaries
- Providing status information about log monitoring

When users ask for status, provide a comprehensive overview of log monitoring activities.
When users want to check logs, scan all log files and report findings clearly.
When users want to search logs, find matching entries and present results.

You can use the following tools to perform log monitoring operations:
- check_logs: Check all log files for errors and issues
- check_recent_logs: Check logs from the last N hours
- search_logs: Search logs for specific terms
- get_error_summary: Get a summary of errors by type
- get_log_monitor_status: Get comprehensive logging monitor agent status

If a user asks about something outside your capabilities (like GitHub operations, testing, or code analysis), you can suggest they ask the appropriate agent:
- For GitHub operations: Ask the GitHub Agent
- For testing: Ask the Testing Agent
- For code analysis and fixes: Ask the Coding Agent
- For code quality and formatting: Ask the Linting Agent
- For project coordination: Ask the Supervisor Agent

Format your responses in markdown for better readability.""",
    tools=[check_logs, check_recent_logs, search_logs, get_error_summary, get_log_monitor_status],
)


# FastAPI app for web interface compatibility
app = FastAPI(
    title="Vectras Logging Monitor Agent",
    description="Log monitoring and analysis agent",
    version="0.2.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    status: str
    response: str
    agent_id: str = "logging-monitor"
    timestamp: datetime
    metadata: Dict[str, Any]


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Main query endpoint that uses the OpenAI Agents SDK."""
    try:
        print(f"DEBUG: Logging Monitor agent received query: {request.query[:100]}...")

        # Run the agent using the SDK
        result = await Runner.run(log_monitor_agent, request.query)

        # Determine response type for frontend rendering using LLM when needed
        response_type = await determine_response_type_with_llm(
            "logging-monitor", request.query, result.final_output
        )

        return QueryResponse(
            status="success",
            response=result.final_output,
            timestamp=datetime.now(),
            metadata={
                "model": "gpt-4o-mini",
                "capabilities": ["Log Monitoring", "Error Detection", "Log Analysis"],
                "response_type": response_type,
                "sdk_version": "openai-agents",
            },
        )

    except Exception as e:
        print(f"Error in Logging Monitor agent: {str(e)}")
        return QueryResponse(
            status="error",
            response=f"Error processing query: {str(e)}",
            timestamp=datetime.now(),
            metadata={"error": str(e)},
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "logging-monitor-agent"}


@app.get("/status")
async def status():
    return {
        "agent": "Logging Monitor Agent",
        "status": "active",
        "log_entries_count": len(log_monitor_manager.log_entries),
        "error_count": log_monitor_manager.error_count,
        "sdk_version": "openai-agents",
        "tools": [
            "check_logs",
            "check_recent_logs",
            "search_logs",
            "get_error_summary",
            "get_log_monitor_status",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8124)
