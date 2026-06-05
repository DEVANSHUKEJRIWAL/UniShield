"""Tests for repo acquisition and content-based SAST."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.scr.schemas.input_schema import SCRAgentInput, ScanMode, TriggerSource
from backend.scr.stages.stage1_acquisition import AcquisitionStage
from backend.scr.tools.repo_acquirer import (
    acquire_repo_files,
    download_github_tarball,
    walk_repo_files,
)
from backend.scr.tools.sast_runner import SASTRunner
from backend.connectors.git_clone import is_commit_sha


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


@pytest.mark.asyncio
async def test_acquisition_logs_when_repo_credentials_missing():
    result = await acquire_repo_files(
        _input(repo_url="https://github.com/o/r", repo_ref="main", repo_auth_token=None)
    )
    assert result.files == []


@pytest.mark.asyncio
async def test_download_github_tarball_extracts_files(tmp_path: Path, monkeypatch):
    import tarfile

    archive_path = tmp_path / "repo.tar.gz"
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("eval(x)\n", encoding="utf-8")

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(source, arcname="owner-repo-deadbeef")

    class FakeResponse:
        content = archive_path.read_bytes()

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, headers=None):
            return FakeResponse()

    monkeypatch.setattr(
        "backend.scr.tools.repo_acquirer.httpx.AsyncClient",
        lambda **kwargs: FakeClient(),
    )

    target = tmp_path / "extract"
    target.mkdir()
    root = await download_github_tarball(
        "https://github.com/owner/repo",
        "token",
        "main",
        str(target),
    )
    files = walk_repo_files(
        root,
        include_patterns=["**/*"],
        exclude_patterns=[],
        max_files=100,
        max_file_size_kb=500,
    )
    assert any(path.endswith("app.py") for path in files)


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
