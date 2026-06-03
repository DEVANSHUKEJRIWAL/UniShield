"""AST-based entry point and call-graph extraction for attack path analysis."""

from __future__ import annotations

import ast
import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

SANITIZER_NAMES = {
    "escape",
    "html_escape",
    "quote",
    "sanitize",
    "validate",
    "clean",
    "strip_tags",
    "bleach_clean",
    "parameterize",
    "bindparam",
    "mark_safe",
}

ROUTE_DECORATOR_PATTERNS = [
    (re.compile(r"@(app|router|api|bp)\.(get|post|put|delete|patch|route)\s*\(\s*['\"]([^'\"]+)['\"]"), "decorator"),
    (re.compile(r"@(app|router|api|bp)\.route\s*\(\s*['\"]([^'\"]+)['\"]"), "flask_route"),
]

SINK_CALL_PATTERNS = {
    "execute": "sql_injection",
    "executemany": "sql_injection",
    "raw": "sql_injection",
    "eval": "code_execution",
    "exec": "code_execution",
    "os.system": "command_injection",
    "subprocess.call": "command_injection",
    "subprocess.run": "command_injection",
    "pickle.loads": "deserialization",
    "yaml.load": "deserialization",
    "open": "path_traversal",
}


@dataclass
class ExtractedFunction:
    name: str
    file_path: str
    line_start: int
    line_end: int
    calls: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ExtractedEntryPoint:
    route: str
    method: str
    handler: str
    file_path: str
    line_start: int
    line_end: int
    framework: str = "unknown"


@dataclass
class ExtractedCallEdge:
    caller: str
    callee: str
    file_path: str
    line: int
    tainted_args: list[str] = field(default_factory=list)


@dataclass
class FileAST:
    file_path: str
    language: str
    entry_points: list[ExtractedEntryPoint] = field(default_factory=list)
    functions: list[ExtractedFunction] = field(default_factory=list)
    call_edges: list[ExtractedCallEdge] = field(default_factory=list)
    sanitizers: list[str] = field(default_factory=list)
    sink_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "entry_points": [ep.__dict__ for ep in self.entry_points],
            "functions": [fn.__dict__ for fn in self.functions],
            "call_edges": [edge.__dict__ for edge in self.call_edges],
            "sanitizers": self.sanitizers,
            "sink_calls": self.sink_calls,
        }


class ASTExtractor:
    """Extracts HTTP entry points, call graphs, and taint-relevant sinks from source."""

    def extract_file(
        self,
        file_path: str,
        source: str,
        language: str = "python",
    ) -> FileAST:
        if language != "python" and not file_path.endswith(".py"):
            return self._extract_via_regex(file_path, source, language)

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            logger.debug("AST parse failed for %s: %s", file_path, exc)
            return self._extract_via_regex(file_path, source, language)

        functions: dict[str, ExtractedFunction] = {}
        call_edges: list[ExtractedCallEdge] = []
        sanitizers: list[str] = []
        sink_calls: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                fn = self._extract_function(node, file_path)
                functions[fn.name] = fn
            elif isinstance(node, ast.Call):
                callee = self._call_name(node.func)
                if callee:
                    if any(s in callee.lower() for s in SANITIZER_NAMES):
                        sanitizers.append(callee)
                    sink_type = self._sink_type(callee)
                    if sink_type:
                        sink_calls.append(
                            {
                                "callee": callee,
                                "sink_type": sink_type,
                                "line": getattr(node, "lineno", 0),
                                "tainted_args": self._tainted_arg_names(node),
                            }
                        )

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                caller = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        callee = self._call_name(child.func)
                        if not callee:
                            continue
                        if caller in functions:
                            if callee not in functions[caller].calls:
                                functions[caller].calls.append(callee)
                        call_edges.append(
                            ExtractedCallEdge(
                                caller=caller,
                                callee=callee,
                                file_path=file_path,
                                line=getattr(child, "lineno", 0),
                                tainted_args=self._tainted_arg_names(child),
                            )
                        )

        entry_points = self._extract_entry_points(tree, file_path, source)
        return FileAST(
            file_path=file_path,
            language=language,
            entry_points=entry_points,
            functions=list(functions.values()),
            call_edges=call_edges,
            sanitizers=sanitizers,
            sink_calls=sink_calls,
        )

    def extract_many(
        self,
        sources: dict[str, str],
        language_map: dict[str, str] | None = None,
    ) -> dict[str, FileAST]:
        language_map = language_map or {}
        result: dict[str, FileAST] = {}
        for file_path, source in sources.items():
            if not source.strip():
                continue
            lang = language_map.get(file_path, self._guess_language(file_path))
            result[file_path] = self.extract_file(file_path, source, lang)
        return result

    def build_sources_from_findings(
        self,
        files: list[str],
        code_findings: list[dict[str, Any]],
        file_contents: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Build minimal parseable source per file from snippets and optional disk content."""
        sources: dict[str, str] = dict(file_contents or {})
        snippets_by_file: dict[str, list[str]] = {}
        for finding in code_findings:
            fp = str(finding.get("file_path") or "")
            snippet = str(finding.get("code_snippet") or "").strip()
            if fp and snippet:
                snippets_by_file.setdefault(fp, []).append(snippet)

        for file_path in files:
            if file_path in sources:
                continue
            snippets = snippets_by_file.get(file_path, [])
            if snippets:
                sources[file_path] = self._wrap_snippets_as_module(file_path, snippets)
                continue
            sources[file_path] = self._synthetic_stub(file_path)

        return sources

    @staticmethod
    def file_ast_key(file_path: str) -> str:
        return hashlib.sha256(file_path.encode()).hexdigest()[:12]

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str) -> ExtractedFunction:
        params = [arg.arg for arg in node.args.args if arg.arg != "self"]
        return ExtractedFunction(
            name=node.name,
            file_path=file_path,
            line_start=getattr(node, "lineno", 1),
            line_end=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
            parameters=params,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def _extract_entry_points(
        self,
        tree: ast.AST,
        file_path: str,
        source: str,
    ) -> list[ExtractedEntryPoint]:
        entry_points: list[ExtractedEntryPoint] = []
        lines = source.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                route_info = self._route_from_decorator(dec, lines)
                if route_info:
                    route, method, framework = route_info
                    entry_points.append(
                        ExtractedEntryPoint(
                            route=route,
                            method=method,
                            handler=node.name,
                            file_path=file_path,
                            line_start=getattr(node, "lineno", 1),
                            line_end=getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                            framework=framework,
                        )
                    )

        for idx, line in enumerate(lines, start=1):
            for pattern, kind in ROUTE_DECORATOR_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if kind == "decorator":
                    method = match.group(2).upper()
                    route = match.group(3)
                    framework = match.group(1)
                else:
                    method = "GET"
                    route = match.group(2)
                    framework = match.group(1)
                handler = self._handler_after_decorator(lines, idx)
                entry_points.append(
                    ExtractedEntryPoint(
                        route=route,
                        method=method,
                        handler=handler or f"handler_{idx}",
                        file_path=file_path,
                        line_start=idx,
                        line_end=idx + 5,
                        framework=framework,
                    )
                )
        return entry_points

    def _route_from_decorator(
        self,
        dec: ast.expr,
        lines: list[str],
    ) -> Optional[tuple[str, str, str]]:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            attr = dec.func.attr
            if attr in {"get", "post", "put", "delete", "patch", "route"}:
                route = ""
                if dec.args and isinstance(dec.args[0], ast.Constant):
                    route = str(dec.args[0].value)
                framework = "fastapi"
                if isinstance(dec.func.value, ast.Name):
                    framework = dec.func.value.id
                return route or "/", attr.upper() if attr != "route" else "GET", framework
        if isinstance(dec, ast.Attribute):
            return None
        line_no = getattr(dec, "lineno", None)
        if line_no and 1 <= line_no <= len(lines):
            for pattern, kind in ROUTE_DECORATOR_PATTERNS:
                match = pattern.search(lines[line_no - 1])
                if match:
                    if kind == "decorator":
                        return match.group(3), match.group(2).upper(), match.group(1)
                    return match.group(2), "GET", match.group(1)
        return None

    @staticmethod
    def _handler_after_decorator(lines: list[str], decor_line: int) -> Optional[str]:
        for line in lines[decor_line: decor_line + 4]:
            match = re.search(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _call_name(node: ast.expr) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    @staticmethod
    def _sink_type(callee: str) -> Optional[str]:
        lower = callee.lower()
        for pattern, sink_type in SINK_CALL_PATTERNS.items():
            if pattern in lower:
                return sink_type
        if "inject" in lower or lower in {"system", "popen"}:
            return "command_injection"
        return None

    @staticmethod
    def _tainted_arg_names(node: ast.Call) -> list[str]:
        names: list[str] = []
        for arg in node.args:
            if isinstance(arg, ast.Name):
                names.append(arg.id)
            elif isinstance(arg, ast.JoinedStr):
                for value in arg.values:
                    if isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name):
                        names.append(value.value.id)
        for _keyword, value in [(kw.arg, kw.value) for kw in node.keywords if kw.arg]:
            if isinstance(value, ast.Name):
                names.append(value.id)
        return names

    def _extract_via_regex(self, file_path: str, source: str, language: str) -> FileAST:
        entry_points: list[ExtractedEntryPoint] = []
        functions: list[ExtractedFunction] = []
        call_edges: list[ExtractedCallEdge] = []
        sanitizers: list[str] = []
        sink_calls: list[dict[str, Any]] = []

        for idx, line in enumerate(source.splitlines(), start=1):
            for pattern, kind in ROUTE_DECORATOR_PATTERNS:
                match = pattern.search(line)
                if match:
                    route = match.group(3 if kind == "decorator" else 2)
                    method = match.group(2).upper() if kind == "decorator" else "GET"
                    entry_points.append(
                        ExtractedEntryPoint(
                            route=route,
                            method=method,
                            handler=self._handler_after_decorator(source.splitlines(), idx) or f"handler_{idx}",
                            file_path=file_path,
                            line_start=idx,
                            line_end=idx + 3,
                            framework=match.group(1),
                        )
                    )
            fn_match = re.search(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if fn_match:
                functions.append(
                    ExtractedFunction(
                        name=fn_match.group(1),
                        file_path=file_path,
                        line_start=idx,
                        line_end=idx + 1,
                    )
                )
            call_match = re.search(r"(\w+)\s*\(", line)
            if call_match:
                callee = call_match.group(1)
                if any(s in callee.lower() for s in SANITIZER_NAMES):
                    sanitizers.append(callee)
                sink_type = self._sink_type(callee)
                if sink_type:
                    sink_calls.append({"callee": callee, "sink_type": sink_type, "line": idx, "tainted_args": []})

        return FileAST(
            file_path=file_path,
            language=language,
            entry_points=entry_points,
            functions=functions,
            call_edges=call_edges,
            sanitizers=sanitizers,
            sink_calls=sink_calls,
        )

    @staticmethod
    def _guess_language(file_path: str) -> str:
        if file_path.endswith(".py"):
            return "python"
        if file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
            return "javascript"
        if file_path.endswith((".go",)):
            return "go"
        return "unknown"

    @staticmethod
    def _wrap_snippets_as_module(file_path: str, snippets: list[str]) -> str:
        body = "\n".join(f"    # snippet\n    {snippet}" for snippet in snippets)
        route_stub = ""
        if "api" in file_path.lower() or "route" in file_path.lower() or "app" in file_path.lower():
            route_stub = "@app.get('/api/data')\nasync def handler():\n"
        return f"{route_stub}def _scr_context():\n{body}\n"

    @staticmethod
    def _synthetic_stub(file_path: str) -> str:
        if "auth" in file_path.lower():
            return "@app.post('/auth/login')\nasync def login():\n    user_input = request.json\n    db.execute(user_input)\n"
        if "api" in file_path.lower():
            return "@app.get('/api/data')\nasync def get_data():\n    return fetch()\n"
        return f"# stub for {file_path}\ndef _scr_stub():\n    pass\n"
