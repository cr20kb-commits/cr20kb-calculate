from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

LAUNCHER_PATH = Path(__file__).parents[1] / "packaging" / "windows" / "launcher.py"
SPEC = importlib.util.spec_from_file_location("cr20kb_windows_launcher", LAUNCHER_PATH)
assert SPEC and SPEC.loader
launcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = launcher
SPEC.loader.exec_module(launcher)


def test_selects_highest_stable_shared_ffmpeg_asset():
    assets = [
        {"name": "ffmpeg-master-latest-win64-gpl-shared.zip"},
        {"name": "ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip"},
        {"name": "ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip"},
    ]
    selected = launcher._select_asset(launcher.TOOL_SPECS[2], assets)
    assert selected["name"] == "ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip"


def test_rejects_zip_path_traversal(tmp_path: Path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "bad")
    with pytest.raises(RuntimeError, match="Unsafe ZIP path"):
        launcher._safe_extract_zip(archive, tmp_path / "output")


def test_accepts_github_sha256_digest():
    digest = "a" * 64
    assert launcher._expected_sha256({"name": "tool.zip", "digest": f"sha256:{digest}"}) == digest


def test_rejects_missing_digest():
    with pytest.raises(RuntimeError, match="SHA-256"):
        launcher._expected_sha256({"name": "tool.zip"})
