"""Builds structured prompts for each SCR stage."""

from __future__ import annotations

import json
from typing import Optional

from unishield.agents.scr.schemas.input_schema import SCRAgentInput
from unishield.agents.scr.schemas.output_schema import CodeFinding


class SCRPromptBuilder:
    """Builds prompt strings sent to the OpenClaw SCR agent for each stage."""

    def build_acquisition_prompt(self, input: SCRAgentInput) -> str:
        return json.dumps(
            {
                "stage": "acquisition",
                "scan_mode": input.scan_mode,
                "repo_url": input.repo_url,
                "file_paths": input.file_paths,
                "include_patterns": input.include_patterns,
                "exclude_patterns": input.exclude_patterns,
                "crown_jewels": input.crown_jewels,
                "max_files": input.max_files,
            }
        )

    def build_detection_prompt(self, files: list[str]) -> str:
        return json.dumps({"stage": "detection", "files": files[:50]})

    def build_analysis_prompt(
        self,
        files: list[str],
        batch_id: str,
        language_map: dict,
        ioc_list: list[str],
        active_ttps: list[str],
        crown_jewels: list[str],
        output_schema_reminder: str = "",
        stage_instructions: Optional[dict] = None,
    ) -> str:
        return json.dumps(
            {
                "stage": "analysis",
                "batch_id": batch_id,
                "files": files,
                "language_map": language_map,
                "ioc_list": ioc_list,
                "active_ttps": active_ttps,
                "crown_jewels": crown_jewels,
                "stage_instructions": stage_instructions or {},
                "output_schema_reminder": output_schema_reminder[:2000],
            }
        )

    def build_ai_analysis_prompt(
        self,
        finding: CodeFinding | dict,
        context_lines: str,
        call_chain: list[str],
        framework: str,
        incident_context: Optional[str],
    ) -> str:
        payload = finding if isinstance(finding, dict) else finding.model_dump()
        return json.dumps(
            {
                "stage": "ai_analysis",
                "finding": payload,
                "context_lines": context_lines,
                "call_chain": call_chain,
                "framework": framework,
                "incident_context": incident_context,
            }
        )

    def build_threat_intel_prompt(
        self,
        findings_summary: list[dict],
        ioc_list: list[str],
        active_ttps: list[str],
        crown_jewels: list[str],
    ) -> str:
        return json.dumps(
            {
                "stage": "threat_intel",
                "findings_summary": findings_summary,
                "ioc_list": ioc_list,
                "active_ttps": active_ttps,
                "crown_jewels": crown_jewels,
            }
        )

    def build_ranking_prompt(
        self,
        all_findings: list[dict],
        sbom_summary: dict,
        compliance_gaps: dict,
    ) -> str:
        return json.dumps(
            {
                "stage": "ranking",
                "all_findings": all_findings,
                "sbom_summary": sbom_summary,
                "compliance_gaps": compliance_gaps,
            }
        )

    def build_output_prompt(
        self,
        ranked_findings: list[dict],
        scan_stats: dict,
        client_id: str,
    ) -> str:
        return json.dumps(
            {
                "stage": "output",
                "ranked_findings": ranked_findings,
                "scan_stats": scan_stats,
                "client_id": client_id,
            }
        )
