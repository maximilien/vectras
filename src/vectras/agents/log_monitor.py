# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Log Monitor Agent - Monitors log files for errors and issues."""

import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .base_agent import BaseAgent
from .config import get_logs_directory


class LogEntry(dict):
    """Represents a log entry with metadata."""

    def __init__(
        self, file_path: str, line_number: int, content: str, timestamp: Optional[datetime] = None
    ):
        super().__init__()
        self["file_path"] = file_path
        self["line_number"] = line_number
        self["content"] = content
        self["timestamp"] = timestamp or datetime.now()
        self["severity"] = self._detect_severity(content)
        self["error_type"] = self._detect_error_type(content)

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
        return self["severity"] in ["error", "critical"] or self["error_type"] is not None


class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for log monitoring."""

    def __init__(self, log_monitor: "LogMonitorAgent"):
        self.log_monitor = log_monitor
        self.file_positions: Dict[str, int] = {}

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        if event.src_path.endswith(".log") or "/logs/" in event.src_path:
            # Simply add the file path to the queue for processing
            try:
                # Use a simple queue to avoid event loop issues
                if hasattr(self.log_monitor, "file_queue"):
                    # Schedule the file processing in the main event loop
                    if hasattr(self.log_monitor, "_loop") and self.log_monitor._loop:
                        self.log_monitor._loop.call_soon_threadsafe(
                            lambda: asyncio.create_task(
                                self.log_monitor.file_queue.put(event.src_path)
                            )
                        )
            except Exception as e:
                # Fallback: just log the error and continue
                print(f"Error scheduling log file processing: {e}")


class LogMonitorAgent(BaseAgent):
    """Agent that monitors application logs for errors and issues."""

    def __init__(self):
        super().__init__("log-monitor")
        self.logs_directory = get_logs_directory()
        self.observer: Optional[Observer] = None
        self.file_positions: Dict[str, int] = {}
        self.recent_errors: List[LogEntry] = []
        self.error_patterns = self.config.settings.error_patterns or [
            "ERROR",
            "Exception",
            "Traceback",
            "FATAL",
            "CRITICAL",
        ]
        self.monitoring = False
        self.file_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None

        # Note: Monitoring is started when the app runs, not during import

    async def start_monitoring(self):
        """Start monitoring log files."""
        if self.monitoring:
            return

        try:
            # Store reference to current event loop
            self._loop = asyncio.get_running_loop()

            # Ensure logs directory exists
            self.logs_directory.mkdir(exist_ok=True)

            # Set up file system watcher
            self.observer = Observer()
            handler = LogFileHandler(self)
            self.observer.schedule(handler, str(self.logs_directory), recursive=True)
            self.observer.start()

            # Start the file processing task
            self.processing_task = asyncio.create_task(self._process_file_queue())

            self.monitoring = True
            self.status = "active"
            self.log_activity("monitoring_started", {"directory": str(self.logs_directory)})

            # Process existing log files
            await self.scan_existing_logs()

        except Exception as e:
            self.log_activity("monitoring_start_error", {"error": str(e)})
            self.error_count += 1

    async def _process_file_queue(self):
        """Process files from the queue."""
        while self.monitoring:
            try:
                # Wait for a file to be queued
                file_path = await asyncio.wait_for(self.file_queue.get(), timeout=1.0)
                await self.process_log_file(file_path)
            except asyncio.TimeoutError:
                # No files in queue, continue monitoring
                continue
            except Exception as e:
                self.log_activity("queue_processing_error", {"error": str(e)})
                continue

    async def stop_monitoring(self):
        """Stop monitoring log files."""
        # Stop the processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None

        # Stop the file system observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        self.monitoring = False
        self.status = "idle"
        self.log_activity("monitoring_stopped")

    async def scan_existing_logs(self):
        """Scan existing log files for recent errors."""
        try:
            log_files = list(self.logs_directory.glob("*.log"))
            for log_file in log_files:
                await self.process_log_file_for_scan(str(log_file))

            self.log_activity("existing_logs_scanned", {"files_count": len(log_files)})

        except Exception as e:
            self.log_activity("scan_error", {"error": str(e)})

    async def process_log_file_for_scan(self, file_path: str):
        """Process a log file for scanning (reads entire file)."""
        try:
            path = Path(file_path)
            if not path.exists():
                return

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # Process all lines
            for line_number, line in enumerate(lines, 1):
                line = line.strip()
                if line:
                    await self.process_log_line(file_path, line_number, line)

        except Exception as e:
            self.log_activity("process_file_error", {"file": file_path, "error": str(e)})

    async def process_log_file(self, file_path: str):
        """Process a log file for new entries."""
        try:
            path = Path(file_path)
            if not path.exists():
                return

            # Get current position for this file
            current_pos = self.file_positions.get(file_path, 0)

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(current_pos)
                new_lines = f.readlines()
                self.file_positions[file_path] = f.tell()

            # Process new lines
            line_number = current_pos  # Approximate line number
            for line in new_lines:
                line = line.strip()
                if line:
                    await self.process_log_line(file_path, line_number, line)
                    line_number += 1

        except Exception as e:
            self.log_activity("process_file_error", {"file": file_path, "error": str(e)})

    async def process_log_line(self, file_path: str, line_number: int, content: str):
        """Process a single log line."""
        # Check if line contains error patterns
        if any(pattern in content for pattern in self.error_patterns):
            log_entry = LogEntry(file_path, line_number, content)

            if log_entry.is_error:
                self.recent_errors.append(log_entry)

                # Keep only recent errors (last 100)
                if len(self.recent_errors) > 100:
                    self.recent_errors = self.recent_errors[-100:]

                self.log_activity(
                    "error_detected",
                    {
                        "file": file_path,
                        "line": line_number,
                        "severity": log_entry["severity"],
                        "error_type": log_entry["error_type"],
                        "content": content[:200],
                    },
                )

                # Notify coding agent for critical errors
                if log_entry["severity"] == "critical" or log_entry["error_type"] in [
                    "exception",
                    "syntax_error",
                ]:
                    await self.notify_code_fixer(log_entry)

    async def notify_code_fixer(self, log_entry: LogEntry):
        """Notify the coding agent about a critical error."""
        try:
            context = {
                "log_entry": log_entry,
                "error_analysis_request": True,
                "source": "log_monitor",
            }

            query = (
                f"Analyze and fix error from {log_entry['file_path']}: {log_entry['content'][:500]}"
            )

            await self.handoff_to_agent("coding", query, context)

            self.log_activity(
                "code_fixer_notified",
                {"error_type": log_entry["error_type"], "file": log_entry["file_path"]},
            )

        except Exception as e:
            self.log_activity("notification_error", {"error": str(e)})

    async def get_recent_errors(
        self, limit: int = 20, severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent errors with optional filtering."""
        errors = self.recent_errors

        if severity:
            errors = [e for e in errors if e["severity"] == severity]

        # Sort by timestamp (most recent first)
        errors = sorted(errors, key=lambda x: x["timestamp"], reverse=True)

        return [dict(e) for e in errors[:limit]]

    async def get_recent_log_entries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent log entries from all monitored files."""
        try:
            all_entries = []

            # Get recent entries from all log files
            for log_file in self.logs_directory.glob("*.log"):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                        # Get the last N lines from each file
                        recent_lines = lines[-limit:] if len(lines) > limit else lines

                        for i, line in enumerate(recent_lines):
                            line = line.strip()
                            if line:
                                # Calculate line number
                                line_number = len(lines) - len(recent_lines) + i + 1
                                entry = LogEntry(str(log_file), line_number, line)
                                all_entries.append(dict(entry))
                except Exception:
                    # Skip files that can't be read
                    continue

            # Sort by timestamp (most recent first) and return the requested number
            all_entries.sort(key=lambda x: x["timestamp"], reverse=True)
            return all_entries[:limit]

        except Exception as e:
            self.log_activity("get_log_entries_error", {"error": str(e)})
            return []

    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.recent_errors if e["timestamp"] > cutoff_time]

        summary = {
            "total_errors": len(recent_errors),
            "error_types": {},
            "severity_counts": {},
            "files_with_errors": set(),
            "time_range_hours": hours,
        }

        for error in recent_errors:
            # Count by error type
            error_type = error["error_type"] or "unknown"
            summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1

            # Count by severity
            severity = error["severity"]
            summary["severity_counts"][severity] = summary["severity_counts"].get(severity, 0) + 1

            # Track files with errors
            summary["files_with_errors"].add(error["file_path"])

        summary["files_with_errors"] = list(summary["files_with_errors"])
        return summary

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process queries for the log monitor agent."""
        query_lower = query.lower()

        # Status queries
        if "status" in query_lower:
            status_info = {
                "monitoring": self.monitoring,
                "logs_directory": str(self.logs_directory),
                "files_monitored": len(self.file_positions),
                "recent_errors_count": len(self.recent_errors),
                "error_patterns": self.error_patterns,
            }

            # Add recent error summary if any errors exist
            if self.recent_errors:
                latest_error = self.recent_errors[-1]  # Most recent error
                status_info["latest_error"] = {
                    "file": latest_error["file_path"],
                    "line": latest_error["line_number"],
                    "severity": latest_error["severity"],
                    "content": latest_error["content"][:100] + "..."
                    if len(latest_error["content"]) > 100
                    else latest_error["content"],
                }

            return status_info

        # Log entry queries
        # Check for log entry queries with more flexible matching
        if (
            "log" in query_lower
            and "entries" in query_lower
            and ("last" in query_lower or "show" in query_lower)
        ) or ("show log last" in query_lower):
            # Extract number from query (e.g., "show last 10 log entries" or "show log last 10 entries")
            import re

            # Try different patterns to extract the number
            patterns = [
                r"show last (\d+) log entries",
                r"show log last (\d+) entries",
                r"last (\d+) log entries",
                r"log last (\d+) entries",
                r"(\d+) entries",
            ]

            limit = 10  # default
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    limit = int(match.group(1))
                    break

            return await self.get_recent_log_entries(limit)

        if "recent log entries" in query_lower or "show log entries" in query_lower:
            limit = context.get("limit", 20) if context else 20
            return await self.get_recent_log_entries(limit)

        # Error queries
        if (
            "recent errors" in query_lower
            or "show errors" in query_lower
            or "show recent errors" in query_lower
        ):
            limit = context.get("limit", 20) if context else 20
            severity = context.get("severity") if context else None
            errors = await self.get_recent_errors(limit, severity)

            if not errors:
                return "📋 No recent errors found. All systems are running smoothly! ✅"

            # Format the response in a readable way
            response = f"🚨 **Recent Errors ({len(errors)} found):**\n\n"

            for i, error in enumerate(errors, 1):
                response += (
                    f"**{i}. Error in {error['file_path']} (line {error['line_number']}):**\n"
                )
                response += f"📅 **Time:** {error['timestamp']}\n"
                response += f"⚠️ **Severity:** {error['severity'].upper()}\n"
                if error["error_type"]:
                    response += f"🔍 **Type:** {error['error_type']}\n"
                response += f"📝 **Content:** {error['content'][:200]}{'...' if len(error['content']) > 200 else ''}\n"
                response += "\n"

            return response

        if "error summary" in query_lower:
            hours = context.get("hours", 24) if context else 24
            return await self.get_error_summary(hours)

        # Control queries
        if "start monitoring" in query_lower:
            await self.start_monitoring()
            return {"status": "monitoring started", "directory": str(self.logs_directory)}

        if "stop monitoring" in query_lower:
            await self.stop_monitoring()
            return {"status": "monitoring stopped"}

        if (
            "scan logs" in query_lower
            or "check logs" in query_lower
            or "scan for errors" in query_lower
        ):
            await self.scan_existing_logs()
            errors_count = len(self.recent_errors)
            if errors_count > 0:
                return f"🔍 **Log scan completed!** Found {errors_count} errors. Use 'show recent errors' to see details."
            else:
                return "🔍 **Log scan completed!** No errors found. All systems are running smoothly! ✅"

        # Handle handoff to coding agent requests
        if "handoff" in query_lower and "coding" in query_lower:
            recent_errors = await self.get_recent_errors(5)
            if recent_errors:
                # Find the most recent error
                latest_error = recent_errors[0]
                log_entry = LogEntry(
                    latest_error["file_path"],
                    latest_error["line_number"],
                    latest_error["content"],
                    latest_error["timestamp"],
                )
                await self.notify_code_fixer(log_entry)
                return f"✅ Handed off error to coding agent: {latest_error['content'][:100]}..."
            else:
                return "ℹ️ No recent errors found to handoff to code-fixer."

        # Check for recent errors and handoff if any found
        if "check for recent errors" in query_lower and "handoff" in query_lower:
            recent_errors = await self.get_recent_errors(5)
            if recent_errors:
                # Find the most recent error
                latest_error = recent_errors[0]
                log_entry = LogEntry(
                    latest_error["file_path"],
                    latest_error["line_number"],
                    latest_error["content"],
                    latest_error["timestamp"],
                )
                await self.notify_code_fixer(log_entry)
                return f"✅ Found error and handed off to coding agent: {latest_error['content'][:100]}..."
            else:
                return "ℹ️ No recent errors found to handoff to code-fixer."

        # Default LLM response with monitoring context
        messages = [
            {
                "role": "system",
                "content": self.config.system_prompt
                + f"""
                
Current monitoring status: {"Active" if self.monitoring else "Inactive"}
Logs directory: {self.logs_directory}
Recent errors: {len(self.recent_errors)}
Error patterns: {", ".join(self.error_patterns)}

I can help with:
- Monitoring log files for errors
- Analyzing error patterns and trends
- Providing error summaries and reports
- Notifying other agents about critical issues
        - Handing off errors to coding agent
""",
            },
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(messages)


# Create the agent instance
log_monitor = LogMonitorAgent()


def create_app():
    """Create FastAPI app for the log monitor agent."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await log_monitor.start_monitoring()
        yield
        # Shutdown
        await log_monitor.stop_monitoring()

    # Create the base app from log_monitor
    base_app = log_monitor.create_app()

    # Create a new app with lifespan
    app = FastAPI(
        title=base_app.title,
        description=base_app.description,
        version=base_app.version,
        lifespan=lifespan,
    )

    # Add CORS middleware explicitly
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Copy all routes from the base app
    app.router.routes = base_app.router.routes

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = log_monitor.config.port or 8124
    uvicorn.run(app, host="0.0.0.0", port=port)
