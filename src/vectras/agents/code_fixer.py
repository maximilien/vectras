"""Code Fixer Agent - Analyzes errors and suggests code fixes."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .base_agent import BaseAgent
from .config import get_project_root


class CodeAnalysis(dict):
    """Represents code analysis results."""

    def __init__(self, file_path: str, error_content: str, analysis: str, suggested_fix: str):
        super().__init__()
        self["file_path"] = file_path
        self["error_content"] = error_content
        self["analysis"] = analysis
        self["suggested_fix"] = suggested_fix
        self["timestamp"] = datetime.now()
        self["severity"] = self._assess_severity(error_content)
        self["confidence"] = self._assess_confidence(analysis)

    def _assess_severity(self, error_content: str) -> str:
        """Assess the severity of the error."""
        high_severity_patterns = [
            "fatal",
            "critical",
            "syntaxerror",
            "importerror",
            "modulenotfound",
        ]
        medium_severity_patterns = ["attributeerror", "typeerror", "valueerror", "keyerror"]

        content_lower = error_content.lower()

        if any(pattern in content_lower for pattern in high_severity_patterns):
            return "high"
        elif any(pattern in content_lower for pattern in medium_severity_patterns):
            return "medium"
        else:
            return "low"

    def _assess_confidence(self, analysis: str) -> str:
        """Assess confidence in the analysis."""
        # Simple heuristic based on analysis length and specificity
        if len(analysis) > 200 and ("specific" in analysis.lower() or "line" in analysis.lower()):
            return "high"
        elif len(analysis) > 100:
            return "medium"
        else:
            return "low"


class CodeFixerAgent(BaseAgent):
    """Agent that analyzes code errors and suggests fixes."""

    def __init__(self):
        super().__init__("code-fixer")
        self.project_root = get_project_root()
        self.analyses: List[CodeAnalysis] = []
        self.github_integration = None  # Initialize to None for testing

    async def analyze_error(
        self,
        error_content: str,
        file_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CodeAnalysis:
        """Analyze an error and suggest a fix."""
        try:
            # Extract file path from error content if not provided
            if not file_path:
                file_path = self._extract_file_path(error_content)

            # Read the relevant file content if possible
            file_content = ""
            if file_path:
                full_path = self.project_root / file_path
                if full_path.exists() and full_path.is_file():
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                    except Exception:
                        pass

            # Prepare analysis prompt
            analysis_prompt = f"""
Analyze this error and suggest a specific code fix:

Error: {error_content}

File: {file_path or "Unknown"}

File Content (if available):
{file_content[:2000] if file_content else "Not available"}

Additional Context: {context if context else "None"}

Please provide:
1. Root cause analysis
2. Specific code fix with exact changes
3. Explanation of the fix
4. Any additional considerations

Be specific about line numbers and exact code changes where possible.
"""

            messages = [
                {
                    "role": "system",
                    "content": self.config.system_prompt
                    + """
                    
Focus on providing actionable, specific code fixes. Include:
- Exact line numbers when possible
- Complete code snippets showing before/after
- Clear explanation of what went wrong
- Validation that the fix addresses the root cause
""",
                },
                {"role": "user", "content": analysis_prompt},
            ]

            analysis_result = await self.llm_completion(messages)

            # Create analysis object
            analysis = CodeAnalysis(
                file_path=file_path or "unknown",
                error_content=error_content,
                analysis=analysis_result,
                suggested_fix=self._extract_suggested_fix(analysis_result),
            )

            # Store analysis
            self.analyses.append(analysis)
            if len(self.analyses) > 100:  # Keep last 100 analyses
                self.analyses = self.analyses[-100:]

            self.log_activity(
                "error_analyzed",
                {
                    "file": file_path,
                    "severity": analysis["severity"],
                    "confidence": analysis["confidence"],
                },
            )

            return analysis

        except Exception as e:
            self.log_activity("analysis_error", {"error": str(e)})
            raise

    def _extract_file_path(self, error_content: str) -> Optional[str]:
        """Extract file path from error content."""
        # Common patterns for file paths in error messages
        patterns = [
            r'File "([^"]+)"',
            r"File '([^']+)'",
            r"in ([^/\s]+\.py)",
            r"File: ([^\s]+)",
            r"at ([^/\s]+\.py):",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_content)
            if match:
                file_path = match.group(1)
                # Make relative to project root if absolute
                if file_path.startswith("/"):
                    rel_path = Path(file_path).relative_to(self.project_root)
                    return str(rel_path) if rel_path.exists() else file_path
                return file_path

        return None

    def _extract_suggested_fix(self, analysis: str) -> str:
        """Extract the suggested fix from analysis."""
        # Look for code blocks or fix sections
        patterns = [
            r"```python\n(.*?)\n```",
            r"```\n(.*?)\n```",
            r"Fix:\s*(.*?)(?:\n\n|\n[A-Z]|\Z)",
            r"Solution:\s*(.*?)(?:\n\n|\n[A-Z]|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, analysis, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: return first paragraph that mentions specific changes
        paragraphs = analysis.split("\n\n")
        for para in paragraphs:
            if any(word in para.lower() for word in ["change", "replace", "add", "remove", "fix"]):
                return para.strip()

        return analysis[:500] + "..." if len(analysis) > 500 else analysis

    async def create_fix_branch(
        self, analysis: CodeAnalysis, apply_fix: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create a GitHub branch with the suggested fix using GitHub Agent."""
        try:
            # Generate branch name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_prefix = self.config.settings.branch_prefix or "vectras-fix"
            branch_name = f"{branch_prefix}-{timestamp}"

            # Apply fix to file if requested and file exists
            applied_files = []
            if apply_fix and analysis["file_path"] != "unknown":
                file_path = self.project_root / analysis["file_path"]
                if file_path.exists():
                    # For now, just add a comment with the suggested fix
                    # In a real implementation, you'd parse and apply the actual fix
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()

                        # Add fix as comment at the beginning
                        fix_comment = f"# VECTRAS AUTO-FIX SUGGESTION:\n# {analysis['suggested_fix'][:200]}...\n\n"
                        new_content = fix_comment + content

                        with open(file_path, "w") as f:
                            f.write(new_content)

                        applied_files.append(str(file_path.relative_to(self.project_root)))
                    except Exception as e:
                        return {"error": f"Failed to apply fix: {str(e)}"}

            # Create commit message
            commit_message = f"Vectras auto-fix suggestion for {analysis['file_path']}\n\nError: {analysis['error_content'][:100]}..."

            # Run linting on changed files if auto-lint-fixes is enabled
            linting_result = ""
            if self.config.settings.auto_lint_fixes and applied_files:
                linting_result = await self._run_linting_on_changes(applied_files)
                if not linting_result.startswith("❌"):
                    # Update commit message to include linting info
                    commit_message = f"{commit_message}\n\nLinting applied: {linting_result}"

            # Hand off to GitHub agent for all GitHub operations
            # 1. Create branch
            branch_result = await self._handoff_to_github_agent(
                "create_branch", {"branch_name": branch_name, "base_branch": "main"}
            )
            if branch_result.startswith("❌"):
                return {"error": f"Failed to create branch: {branch_result}"}

            # 2. Commit files (if any were modified)
            commit_result = "No files to commit"
            if applied_files:
                commit_result = await self._handoff_to_github_agent(
                    "commit_files",
                    {
                        "branch_name": branch_name,
                        "files": applied_files,
                        "commit_message": commit_message,
                    },
                )
                if commit_result.startswith("❌"):
                    return {"error": f"Failed to commit files: {commit_result}"}

            # 3. Create PR
            pr_title = f"Auto-fix for {analysis['file_path']}"
            pr_body = f"""
## Vectras Auto-Fix

**Error Analyzed:**
```
{analysis["error_content"][:500]}
```

**Analysis:**
{analysis["analysis"][:1000]}

**Suggested Fix:**
{analysis["suggested_fix"]}

**Severity:** {analysis["severity"]}
**Confidence:** {analysis["confidence"]}

---
*This PR was automatically created by Vectras Code Fixer Agent*
"""

            pr_result = await self._handoff_to_github_agent(
                "create_pr", {"branch_name": branch_name, "title": pr_title, "body": pr_body}
            )

            result = {
                "branch": branch_name,
                "files_modified": applied_files,
                "github_operations": {
                    "branch_creation": branch_result,
                    "commit": commit_result,
                    "pull_request": pr_result,
                },
            }

            self.log_activity(
                "fix_branch_created",
                {"branch": branch_name, "files": len(applied_files), "github_agent_used": True},
            )

            return result

        except Exception as e:
            self.log_activity("fix_branch_error", {"error": str(e)})
            return {"error": f"Failed to create fix branch: {str(e)}"}

    async def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent code analyses."""
        analyses = sorted(self.analyses, key=lambda x: x["timestamp"], reverse=True)
        return [dict(a) for a in analyses[:limit]]

    async def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analyses."""
        total = len(self.analyses)
        by_severity = {}
        by_confidence = {}
        files_analyzed = set()

        for analysis in self.analyses:
            severity = analysis["severity"]
            confidence = analysis["confidence"]

            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
            files_analyzed.add(analysis["file_path"])

        return {
            "total_analyses": total,
            "by_severity": by_severity,
            "by_confidence": by_confidence,
            "files_analyzed": len(files_analyzed),
            "github_available": bool(
                self.github_integration
                and hasattr(self.github_integration, "is_available")
                and self.github_integration.is_available()
            ),
        }

    async def _run_linting_on_changes(self, changed_files: List[str]) -> str:
        """Run linting on changed files using the Linting Agent."""
        try:
            linting_port = self.config.settings.linting_agent_port or 8127
            linting_url = f"http://localhost:{linting_port}/query"

            # Create request to linting agent
            request_data = {
                "query": f"fix files: {', '.join(changed_files)}",
                "context": {"changed_files": changed_files, "from_code_fixer": True},
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(linting_url, json=request_data)

                if response.status_code == 200:
                    result = response.json()
                    self.log_activity("linting_success", {"files": changed_files, "result": result})
                    return result.get("response", "Linting completed successfully")
                else:
                    error_msg = f"Linting agent returned status {response.status_code}"
                    self.log_activity("linting_error", {"error": error_msg})
                    return f"❌ {error_msg}"

        except Exception as e:
            error_msg = f"Error calling linting agent: {str(e)}"
            self.log_activity("linting_error", {"error": error_msg})
            return f"❌ {error_msg}"

    async def _handoff_to_github_agent(self, operation: str, data: Dict[str, Any]) -> str:
        """Hand off GitHub operations to the GitHub agent."""
        github_agent_port = 8128  # GitHub agent port from config

        try:
            async with httpx.AsyncClient() as client:
                # Construct the appropriate query based on operation
                if operation == "create_branch":
                    query = f"create branch {data['branch_name']}"
                    if data.get("base_branch") and data["base_branch"] != "main":
                        query += f" from {data['base_branch']}"
                elif operation == "commit_files":
                    query = f'commit files to {data["branch_name"]} with message "{data["commit_message"]}"'
                elif operation == "create_pr":
                    query = f'create pr from {data["branch_name"]} with title "{data["title"]}" body "{data["body"]}"'
                else:
                    return f"❌ Unknown GitHub operation: {operation}"

                response = await client.post(
                    f"http://localhost:{github_agent_port}/query",
                    json={"query": query},
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "❌ No response from GitHub agent")
        except Exception as e:
            return f"❌ Error calling GitHub agent: {str(e)}"

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """Process queries for the code fixer agent."""
        query_lower = query.lower()

        # Status queries
        if "status" in query_lower:
            return {
                "recent_analyses": len(self.analyses),
                "project_root": str(self.project_root),
                "github_agent_available": True,  # Always available via handoff
                "github_integration": self.github_integration is not None,
            }

        # Analysis queries
        if "analyze error" in query_lower or context and "log_entry" in context:
            if context and "log_entry" in context:
                log_entry = context["log_entry"]
                error_content = log_entry["content"]
                file_path = log_entry.get("file_path")
            else:
                error_content = context.get("error_content", query) if context else query
                file_path = context.get("file_path") if context else None

            analysis = await self.analyze_error(error_content, file_path, context)
            return dict(analysis)

        if "recent analyses" in query_lower:
            limit = context.get("limit", 20) if context else 20
            return await self.get_recent_analyses(limit)

        if "analysis summary" in query_lower:
            return await self.get_analysis_summary()

        # GitHub operations (handed off to GitHub agent)
        if "create branch" in query_lower or "create pr" in query_lower:
            if not self.analyses:
                return {"error": "No analyses available to create branch from"}

            # Use most recent analysis
            analysis = self.analyses[-1]
            apply_fix = "apply fix" in query_lower

            return await self.create_fix_branch(analysis, apply_fix)

        # Default LLM response
        messages = [
            {
                "role": "system",
                "content": self.config.system_prompt
                + f"""
                
Current status:
- Analyses performed: {len(self.analyses)}
- GitHub operations: Handed off to GitHub Agent
- Project root: {self.project_root}

I can help with:
- Analyzing error messages and stack traces
- Suggesting specific code fixes
- Creating GitHub branches and pull requests (via GitHub Agent)
- Providing analysis summaries and reports
""",
            },
            {"role": "user", "content": query},
        ]

        return await self.llm_completion(messages)


# Create the agent instance
code_fixer = CodeFixerAgent()


def create_app():
    """Create FastAPI app for the code fixer agent."""
    return code_fixer.create_app()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = code_fixer.config.port or 8125
    uvicorn.run(app, host="0.0.0.0", port=port)
