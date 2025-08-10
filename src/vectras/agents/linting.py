# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""Linting Agent - Performs code quality checks and formatting."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent


class LintingAgent(BaseAgent):
    """Linting agent that runs linters and applies auto-fixes."""

    __test__ = False

    def __init__(self):
        super().__init__("linting")

        # Linting-specific attributes
        self.linters = self.config.settings.linters or {
            "python": ["ruff", "black"],
            "javascript": ["eslint", "prettier"],
            "bash": ["shellcheck"],
        }
        self.auto_fix = self.config.settings.auto_fix or True
        self.format_on_save = self.config.settings.format_on_save or True
        self.lint_directories = [
            Path(d)
            for d in (self.config.settings.lint_directories or ["./src", "./tests", "./frontend"])
        ]
        self.exclude_patterns = self.config.settings.exclude_patterns or [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.venv/**",
        ]

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process a query for the linting agent."""
        query_lower = query.lower()

        if "divide" in query_lower and "tool" in query_lower:
            return await self._handle_divide_tool_linting(query, context)
        elif "lint" in query_lower or "check" in query_lower:
            return await self._handle_lint_request(query, context)
        elif "fix" in query_lower or "format" in query_lower:
            return await self._handle_fix_request(query, context)
        elif "status" in query_lower or "info" in query_lower:
            return await self._handle_status_request(query, context)
        elif "files" in query_lower and "changed" in query_lower:
            return await self._handle_changed_files_request(query, context)
        else:
            return await self._handle_general_query(query, context)

    async def _handle_lint_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle linting requests."""
        try:
            # Extract target from query
            target = self._extract_target_from_query(query)

            if target and target != "all" and target != "files":
                result = await self._lint_specific_target(target)
            else:
                result = await self._lint_all_directories()

            self.log_activity("lint_executed", {"query": query, "target": target})
            return result

        except Exception as e:
            self.log_activity("lint_error", {"error": str(e)})
            return f"❌ Error during linting: {str(e)}"

    async def _handle_fix_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle auto-fix requests."""
        try:
            # Extract target from query
            target = self._extract_target_from_query(query)

            if target and target != "all" and target != "files":
                result = await self._fix_specific_target(target)
            else:
                result = await self._fix_all_directories()

            self.log_activity("fix_executed", {"query": query, "target": target})
            return result

        except Exception as e:
            self.log_activity("fix_error", {"error": str(e)})
            return f"❌ Error during fixing: {str(e)}"

    async def _handle_status_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle status/info requests."""
        status_info = f"""🧹 **Linting Agent Status**

**Configuration:**
- Auto-fix enabled: {"Yes" if self.auto_fix else "No"}
- Format on save: {"Yes" if self.format_on_save else "No"}
- Lint directories: {", ".join(str(d) for d in self.lint_directories)}

**Supported Linters:**
"""
        for language, linters in self.linters.items():
            status_info += f"- **{language.title()}**: {', '.join(linters)}\n"

        status_info += f"""
**Capabilities:**
- Code linting and quality checks
- Auto-fixing of common issues
- Multi-language support (Python, JavaScript, Bash)
- Integration with Code Fixer Agent
- Format checking and application

**Recent Activity:**
- Success operations: {self.success_count}
- Error operations: {self.error_count}
- Last activity: {self.last_activity or "None"}
"""

        return status_info

    async def _handle_changed_files_request(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle requests to lint only changed files."""
        try:
            changed_files = await self._get_changed_files()
            if not changed_files:
                return "📝 No changed files detected."

            result = await self._lint_files(changed_files)
            self.log_activity("changed_files_linted", {"files": changed_files})
            return result

        except Exception as e:
            self.log_activity("changed_files_error", {"error": str(e)})
            return f"❌ Error processing changed files: {str(e)}"

    async def _handle_divide_tool_linting(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle linting specifically for the divide tool."""
        try:
            # Check if the fixed divide tool exists
            fixed_file_path = Path("./test_tools/divide_fixed.py")
            test_file_path = Path("./test_tools/test_divide.py")

            if not fixed_file_path.exists():
                return "❌ Fixed divide tool not found. Please run the code fixer first."

            if not test_file_path.exists():
                return "❌ Test file not found. Please run the code fixer first."

            # Lint both files
            results = []

            # Lint the fixed divide function
            divide_result = await self._lint_file(fixed_file_path)
            results.append(f"**Divide Function Linting:**\n{divide_result}")

            # Lint the test file
            test_result = await self._lint_file(test_file_path)
            results.append(f"**Test File Linting:**\n{test_result}")

            # Check for any issues
            if "❌" in divide_result or "❌" in test_result:
                return "⚠️ Linting issues found:\n\n" + "\n\n".join(results)
            else:
                return "✅ All divide tool files passed linting!\n\n" + "\n\n".join(results)

        except Exception as e:
            self.log_activity("divide_tool_linting_error", {"error": str(e)})
            return f"❌ Error linting divide tool: {str(e)}"

    async def _handle_general_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle general queries about linting."""
        messages = [
            {
                "role": "system",
                "content": f"""You are the Vectras linting agent. You help with:

1. Running linters on code (ruff, eslint, shellcheck, etc.)
2. Applying auto-fixes to code issues
3. Ensuring code quality standards
4. Working with the Code Fixer Agent to finalize fixes

**Current Configuration:**
- Auto-fix: {self.auto_fix}
- Format on save: {self.format_on_save}
- Lint directories: {self.lint_directories}
- Supported linters: {self.linters}

Provide helpful information about linting capabilities and guide users on what they can do.""",
            },
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(
            messages, session_id=context.get("session_id") if context else None
        )

    async def _lint_all_directories(self) -> str:
        """Lint all configured directories."""
        results = []
        for directory in self.lint_directories:
            if directory.exists():
                result = await self._lint_directory(directory)
                results.append(f"**{directory}:**\n{result}")
            else:
                results.append(f"**{directory}:** Directory not found")

        return "\n\n".join(results)

    async def _fix_all_directories(self) -> str:
        """Fix all configured directories."""
        results = []
        for directory in self.lint_directories:
            if directory.exists():
                result = await self._fix_directory(directory)
                results.append(f"**{directory}:**\n{result}")
            else:
                results.append(f"**{directory}:** Directory not found")

        return "\n\n".join(results)

    async def _lint_specific_target(self, target: str) -> str:
        """Lint a specific target (file or directory)."""
        target_path = Path(target)
        if target_path.is_file():
            return await self._lint_files([target_path])
        elif target_path.is_dir():
            return await self._lint_directory(target_path)
        else:
            return f"❌ Target not found: {target}"

    async def _fix_specific_target(self, target: str) -> str:
        """Fix a specific target (file or directory)."""
        target_path = Path(target)
        if target_path.is_file():
            return await self._fix_files([target_path])
        elif target_path.is_dir():
            return await self._fix_directory(target_path)
        else:
            return f"❌ Target not found: {target}"

    async def _lint_directory(self, directory: Path) -> str:
        """Lint a specific directory."""
        results = []

        # Find files to lint
        files = self._find_files_to_lint(directory)

        if not files:
            return f"📝 No files to lint in {directory}"

        for file_path in files:
            result = await self._lint_file(file_path)
            if result:
                results.append(f"**{file_path.name}:** {result}")

        return "\n".join(results) if results else f"✅ All files in {directory} passed linting"

    async def _fix_directory(self, directory: Path) -> str:
        """Fix a specific directory."""
        results = []

        # Find files to fix
        files = self._find_files_to_lint(directory)

        if not files:
            return f"📝 No files to fix in {directory}"

        for file_path in files:
            result = await self._fix_file(file_path)
            if result:
                results.append(f"**{file_path.name}:** {result}")

        return (
            "\n".join(results) if results else f"✅ All files in {directory} are properly formatted"
        )

    async def _lint_files(self, files: List[Path]) -> str:
        """Lint specific files."""
        results = []
        for file_path in files:
            result = await self._lint_file(file_path)
            if result:
                results.append(f"**{file_path.name}:** {result}")

        return "\n".join(results) if results else "✅ All files passed linting"

    async def _fix_files(self, files: List[Path]) -> str:
        """Fix specific files."""
        results = []
        for file_path in files:
            result = await self._fix_file(file_path)
            if result:
                results.append(f"**{file_path.name}:** {result}")

        return "\n".join(results) if results else "✅ All files are properly formatted"

    async def _lint_file(self, file_path: Path) -> str:
        """Lint a specific file."""
        language = self._detect_language(file_path)
        if not language or language not in self.linters:
            return ""

        linters = self.linters[language]
        results = []

        for linter in linters:
            try:
                result = await self._run_linter(linter, file_path, fix=False)
                if result:
                    results.append(f"{linter}: {result}")
            except Exception as e:
                results.append(f"{linter}: Error - {str(e)}")

        return "; ".join(results) if results else ""

    async def _fix_file(self, file_path: Path) -> str:
        """Fix a specific file."""
        language = self._detect_language(file_path)
        if not language or language not in self.linters:
            return ""

        linters = self.linters[language]
        results = []

        for linter in linters:
            try:
                result = await self._run_linter(linter, file_path, fix=True)
                if result:
                    results.append(f"{linter}: {result}")
            except Exception as e:
                results.append(f"{linter}: Error - {str(e)}")

        return "; ".join(results) if results else ""

    async def _run_linter(self, linter: str, file_path: Path, fix: bool = False) -> str:
        """Run a specific linter on a file."""
        if linter == "ruff":
            return await self._run_ruff(file_path, fix)
        elif linter == "black":
            return await self._run_black(file_path, fix)
        elif linter == "eslint":
            return await self._run_eslint(file_path, fix)
        elif linter == "prettier":
            return await self._run_prettier(file_path, fix)
        elif linter == "shellcheck":
            return await self._run_shellcheck(file_path, fix)
        else:
            return f"Unknown linter: {linter}"

    async def _run_ruff(self, file_path: Path, fix: bool) -> str:
        """Run ruff linter/formatter."""
        cmd = ["uv", "run", "ruff"]
        if fix:
            cmd.extend(["--fix"])
        cmd.extend(["check", str(file_path)])

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return "✅ No issues found" if not fix else "✅ Fixed"
            else:
                output = stdout.decode() + stderr.decode()
                return f"⚠️ Issues found: {output.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _run_black(self, file_path: Path, fix: bool) -> str:
        """Run black formatter."""
        cmd = ["uv", "run", "black"]
        if not fix:
            cmd.append("--check")
        cmd.append(str(file_path))

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return "✅ Properly formatted" if not fix else "✅ Formatted"
            else:
                output = stdout.decode() + stderr.decode()
                return f"⚠️ Formatting issues: {output.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _run_eslint(self, file_path: Path, fix: bool) -> str:
        """Run eslint linter."""
        cmd = ["npx", "eslint"]
        if fix:
            cmd.append("--fix")
        cmd.append(str(file_path))

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return "✅ No issues found" if not fix else "✅ Fixed"
            else:
                output = stdout.decode() + stderr.decode()
                return f"⚠️ Issues found: {output.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _run_prettier(self, file_path: Path, fix: bool) -> str:
        """Run prettier formatter."""
        cmd = ["npx", "prettier"]
        if not fix:
            cmd.append("--check")
        else:
            cmd.append("--write")
        cmd.append(str(file_path))

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return "✅ Properly formatted" if not fix else "✅ Formatted"
            else:
                output = stdout.decode() + stderr.decode()
                return f"⚠️ Formatting issues: {output.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    async def _run_shellcheck(self, file_path: Path, fix: bool) -> str:
        """Run shellcheck linter."""
        cmd = ["shellcheck", str(file_path)]

        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                return "✅ No issues found"
            else:
                output = stdout.decode() + stderr.decode()
                return f"⚠️ Issues found: {output.strip()}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect the programming language of a file."""
        extension = file_path.suffix.lower()

        if extension in [".py", ".pyi"]:
            return "python"
        elif extension in [".js", ".jsx", ".ts", ".tsx"]:
            return "javascript"
        elif extension in [".sh", ".bash"]:
            return "bash"
        else:
            return None

    def _find_files_to_lint(self, directory: Path) -> List[Path]:
        """Find files to lint in a directory."""
        files = []

        for pattern in ["**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.sh"]:
            files.extend(directory.glob(pattern))

        # Filter out excluded patterns
        filtered_files = []
        for file_path in files:
            if not any(
                self._matches_pattern(file_path, pattern) for pattern in self.exclude_patterns
            ):
                filtered_files.append(file_path)

        return filtered_files

    def _matches_pattern(self, file_path: Path, pattern: str) -> bool:
        """Check if a file path matches an exclusion pattern."""
        import fnmatch

        return fnmatch.fnmatch(str(file_path), pattern)

    def _extract_target_from_query(self, query: str) -> Optional[str]:
        """Extract target from query."""
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() in ["lint", "fix", "format", "check"] and i + 1 < len(words):
                next_word = words[i + 1]
                # Handle quoted strings
                if next_word.startswith("'") or next_word.startswith('"'):
                    # Find the closing quote
                    start_quote = next_word[0]
                    if next_word.endswith(start_quote):
                        return next_word
                    else:
                        # Multi-word quoted string
                        result = [next_word]
                        for j in range(i + 2, len(words)):
                            result.append(words[j])
                            if words[j].endswith(start_quote):
                                return " ".join(result)
                        return " ".join(result)
                else:
                    return next_word
        return None

    async def _get_changed_files(self) -> List[Path]:
        """Get list of changed files (simplified implementation)."""
        # In a real implementation, this would check git status
        # For now, return empty list
        return []


# Create the agent instance
linting_agent = LintingAgent()


def create_app():
    """Create FastAPI app for the linting agent."""
    return linting_agent.create_app()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = linting_agent.config.port or 8127
    uvicorn.run(app, host="0.0.0.0", port=port)
