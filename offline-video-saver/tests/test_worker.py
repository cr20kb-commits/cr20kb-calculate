from pathlib import Path
import sys

from app.config import EncodeProfile, Settings
from app.domain import PlaylistEntry
from app.worker import JobManager


def settings(tmp_path: Path, *, js_runtime: str = "node") -> Settings:
    return Settings(
        data_dir=tmp_path,
        max_playlist_items=5,
        max_video_duration_seconds=3600,
        max_source_megabytes=500,
        min_free_gigabytes=0,
        max_retained_jobs=2,
        job_ttl_hours=1,
        scan_timeout_seconds=30,
        download_timeout_seconds=30,
        transcode_timeout_seconds=30,
        access_key="",
        cookie_secure=False,
        ytdlp_bin="yt-dlp",
        ytdlp_js_runtime=js_runtime,
        handbrake_bin="HandBrakeCLI",
        ffmpeg_bin="ffmpeg",
    )


def profile(prefer_smaller_source: bool = True) -> EncodeProfile:
    return EncodeProfile(
        id="test",
        label_ru="test",
        label_en="test",
        description_ru="test",
        description_en="test",
        max_width=1280,
        max_height=720,
        encoder="x265",
        encoder_preset="medium",
        quality=29,
        audio_kbps=80,
        prefer_smaller_source=prefer_smaller_source,
    )


def test_keep_source_when_handbrake_result_is_not_smaller(tmp_path: Path, monkeypatch):
    manager = JobManager(settings(tmp_path))
    source = tmp_path / "source.webm"
    source.write_bytes(b"s" * 100)
    output = tmp_path / "output"
    output.mkdir()

    def fake_run(command, timeout, on_progress):
        target = Path(command[command.index("--output") + 1])
        target.write_bytes(b"e" * 99)
        on_progress(1.0)

    monkeypatch.setattr(manager, "_run_streaming", fake_run)
    final = manager._encode_or_keep_smaller(
        source=source,
        output_dir=output,
        index=1,
        entry=PlaylistEntry("abc12345", "Title"),
        profile=profile(True),
        on_progress=lambda _value: None,
    )
    assert final.suffix == ".webm"
    assert final.stat().st_size == 100
    manager.stop()


def test_keep_encoded_when_it_is_smaller(tmp_path: Path, monkeypatch):
    manager = JobManager(settings(tmp_path))
    source = tmp_path / "source.mkv"
    source.write_bytes(b"s" * 100)
    output = tmp_path / "output"
    output.mkdir()

    def fake_run(command, timeout, on_progress):
        target = Path(command[command.index("--output") + 1])
        target.write_bytes(b"e" * 50)

    monkeypatch.setattr(manager, "_run_streaming", fake_run)
    final = manager._encode_or_keep_smaller(
        source=source,
        output_dir=output,
        index=1,
        entry=PlaylistEntry("abc12345", "Title"),
        profile=profile(True),
        on_progress=lambda _value: None,
    )
    assert final.suffix == ".mp4"
    assert final.stat().st_size == 50
    assert not source.exists()
    manager.stop()


def test_handbrake_failure_falls_back_to_source(tmp_path: Path, monkeypatch):
    manager = JobManager(settings(tmp_path))
    source = tmp_path / "source.mkv"
    source.write_bytes(b"source")
    output = tmp_path / "output"
    output.mkdir()
    warnings = []

    def fail(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "_run_streaming", fail)
    final = manager._encode_or_keep_smaller(
        source=source,
        output_dir=output,
        index=1,
        entry=PlaylistEntry("abc12345", "Title"),
        profile=profile(True),
        on_progress=lambda _value: None,
        on_warning=warnings.append,
    )
    assert final.read_bytes() == b"source"
    assert warnings and "handbrake_failed_kept_source" in warnings[0]
    manager.stop()


def test_run_streaming_handles_carriage_return_progress(tmp_path: Path):
    manager = JobManager(settings(tmp_path))
    progress: list[float] = []
    script = (
        "import sys,time; "
        "[(sys.stdout.write(f'Encoding: {value} %\\r'), sys.stdout.flush(), time.sleep(0.02)) "
        "for value in (12.5, 50.0, 100.0)]"
    )
    manager._run_streaming(
        [sys.executable, "-c", script],
        timeout=10,
        on_progress=progress.append,
    )
    assert progress
    assert progress[-1] == 1.0
    manager.stop()


def test_scan_uses_configured_js_runtime(tmp_path: Path, monkeypatch):
    manager = JobManager(settings(tmp_path, js_runtime="deno"))
    captured: list[str] = []

    class Result:
        stdout = '{"title":"Playlist","entries":[]}'

    def fake_run(command, timeout):
        captured.extend(command)
        return Result()

    monkeypatch.setattr(manager, "_run", fake_run)
    manager._scan_playlist("https://www.youtube.com/playlist?list=PL1234567890")
    index = captured.index("--js-runtimes")
    assert captured[index + 1] == "deno"
    manager.stop()
