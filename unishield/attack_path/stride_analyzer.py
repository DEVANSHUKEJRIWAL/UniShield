"""STRIDE threat categorization for attack paths."""

from __future__ import annotations

from unishield.schemas.attack_path_schemas import AttackPath, NodeType, STRIDECategory


class STRIDEAnalyzer:
    """Maps attack paths to STRIDE categories."""

    SINK_TO_STRIDE: dict[str, list[STRIDECategory]] = {
        "sql_query": [STRIDECategory.TAMPERING, STRIDECategory.INFO_DISCLOSURE],
        "sql_injection": [STRIDECategory.TAMPERING, STRIDECategory.INFO_DISCLOSURE],
        "injection": [STRIDECategory.TAMPERING, STRIDECategory.INFO_DISCLOSURE],
        "shell_exec": [STRIDECategory.ELEVATION, STRIDECategory.TAMPERING],
        "command_injection": [STRIDECategory.ELEVATION, STRIDECategory.TAMPERING],
        "file_write": [STRIDECategory.TAMPERING],
        "file_read": [STRIDECategory.INFO_DISCLOSURE],
        "http_response": [STRIDECategory.INFO_DISCLOSURE, STRIDECategory.TAMPERING],
        "log_write": [STRIDECategory.REPUDIATION, STRIDECategory.INFO_DISCLOSURE],
        "eval_exec": [STRIDECategory.ELEVATION, STRIDECategory.TAMPERING],
        "deserialization": [STRIDECategory.ELEVATION, STRIDECategory.TAMPERING],
        "code_execution": [STRIDECategory.ELEVATION, STRIDECategory.TAMPERING],
        "external_http": [STRIDECategory.TAMPERING],
        "auth_bypass": [STRIDECategory.SPOOFING, STRIDECategory.ELEVATION],
        "payment_transfer": [STRIDECategory.TAMPERING, STRIDECategory.REPUDIATION],
        "swift_message": [
            STRIDECategory.TAMPERING,
            STRIDECategory.REPUDIATION,
            STRIDECategory.INFO_DISCLOSURE,
        ],
    }

    def analyze(self, path: AttackPath) -> list[STRIDECategory]:
        sink_type = str(path.sink.metadata.get("sink_type", "")).lower()
        categories = set(self.SINK_TO_STRIDE.get(sink_type, []))
        if not path.has_sanitizer:
            categories.add(STRIDECategory.TAMPERING)
        if path.reaches_crown_jewel:
            categories.add(STRIDECategory.INFO_DISCLOSURE)
            categories.add(STRIDECategory.ELEVATION)
        if any(n.node_type == NodeType.ENTRY_POINT and "auth" in n.name.lower() for n in path.nodes):
            categories.add(STRIDECategory.SPOOFING)
        return sorted(categories, key=lambda c: c.value)

    def analyze_all(self, paths: list[AttackPath]) -> list[AttackPath]:
        for path in paths:
            path.stride_threats = self.analyze(path)
        return paths
