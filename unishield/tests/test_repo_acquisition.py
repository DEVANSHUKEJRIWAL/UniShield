"""Tests for repo acquisition and content-based SAST."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from unishield.agents.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from unishield.agents.scr.stages.stage1_acquisition import AcquisitionStage
from unishield.agents.scr.tools.repo_acquirer import walk_repo_files
from unishield.agents.scr.tools.sast_runner import SASTRunner
from unishield.connectors.git_clone import is_commit_sha


class FakeMemory:
    async def save_file_list(self, scan_id: str, files: list[str]) -> None:
        self.files = files


def _input(**kwargs) -> SCRAgentInput:
    defaults = {
        "request_id": "scan-1",
        "client_id": "client-1",
        "workflow_id": "wf-1",
        "triggered_by": TriggerSource.MANUAL,
        "scan_mode": ScanMode.FULL_REPO,
    }
    defaults.update(kwargs)
    return SCRAgentInput(**defaults)


def test_is_commit_sha():
    assert is_commit_sha("a" * 40)
    assert not is_commit_sha("main")


@pytest.mark.asyncio
async def test_acquisition_walks_archive_path(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "login.py").write_text("eval(user_input)\n", encoding="utf-8")
    (src / "notes.txt").write_text("ignored", encoding="utf-8")

    stage = AcquisitionStage(FakeMemory())
    result = await stage.run(
        "scan-1",
        _input(
            archive_path=str(tmp_path),
            include_patterns=["**/*"],
            exclude_patterns=[],
        ),
    )
    assert "src/login.py" in result.files
    assert "src/notes.txt" not in result.files


@pytest.mark.asyncio
async def test_sast_finds_eval_in_cloned_file(tmp_path: Path):
    file_path = tmp_path / "vulnerable.py"
    file_path.write_text("result = eval(request.args.get('x'))\n", encoding="utf-8")

    runner = SASTRunner()
    findings = await runner.run(
        ["vulnerable.py"],
        {"python": "rules/python"},
        archive_path=str(tmp_path),
        language_map={"vulnerable.py": "python"},
    )
    assert findings
    assert any(f["category"] == "code_execution" for f in findings)


def test_walk_repo_respects_exclude_patterns(tmp_path: Path):
    (tmp_path / "keep.py").write_text("x=1", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_keep.py").write_text("x=1", encoding="utf-8")

    files = walk_repo_files(
        str(tmp_path),
        include_patterns=["**/*"],
        exclude_patterns=["**/tests/**"],
        max_files=100,
        max_file_size_kb=500,
    )
    assert "keep.py" in files
    assert "tests/test_keep.py" not in files
