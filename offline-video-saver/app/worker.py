from __future__ import annotations

import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from .config import PROFILES, EncodeProfile, Settings
from .domain import (
    InputError,
    Job,
    PlaylistEntry,
    ToolError,
    canonical_playlist_url,
    safe_filename,
    unique_destination,
    valid_job_id,
    valid_video_id,
)

_PERCENT_RE = re.compile(r"(?P<percent>\d{1,3}(?:\.\d+)?)\s*%")


class JobManager:
    """Single-worker queue that keeps peak disk use predictable."""

    ACTIVE = {"queued", "scanning", "running"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-job")
        self._stop_cleanup = threading.Event()
        self.jobs_dir = settings.data_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def start_cleanup(self) -> None:
        self._cleanup_once()
        threading.Thread(target=self._cleanup_loop, name="job-cleanup", daemon=True).start()

    def stop(self) -> None:
        self._stop_cleanup.set()
        self._executor.shutdown(wait=False, cancel_futures=False)

    def create(self, raw_url: str, profile_id: str) -> Job:
        canonical_url, playlist_id = canonical_playlist_url(raw_url)
        try:
            profile = PROFILES[profile_id]
        except KeyError as exc:
            raise InputError("profile_invalid") from exc

        with self._lock:
            retained = sum(1 for job in self._jobs.values() if job.status in self.ACTIVE)
            if retained >= self.settings.max_retained_jobs:
                raise InputError("queue_full")

            job = Job(
                id=secrets.token_urlsafe(18),
                playlist_url=canonical_url,
                playlist_id=playlist_id,
                profile=profile,
            )
            self._jobs[job.id] = job

        self._persist(job)
        self._executor.submit(self._process, job.id)
        return job

    def get(self, job_id: str) -> Job | None:
        if not valid_job_id(job_id):
            return None
        with self._lock:
            return self._jobs.get(job_id)

    def output_files(self, job_id: str) -> list[Path]:
        job = self.get(job_id)
        if not job or job.status != "ready":
            return []
        output_dir = self.jobs_dir / job_id / "output"
        if not output_dir.is_dir():
            return []
        return sorted(path for path in output_dir.iterdir() if path.is_file())

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in self.ACTIVE:
                return False
            self._jobs.pop(job_id, None)
        shutil.rmtree(self.jobs_dir / job_id, ignore_errors=True)
        return True

    def missing_tools(self) -> list[str]:
        missing: list[str] = []
        for label, command in (
            ("yt-dlp", self.settings.ytdlp_bin),
            ("HandBrakeCLI", self.settings.handbrake_bin),
            ("ffmpeg", self.settings.ffmpeg_bin),
        ):
            if shutil.which(command) is None:
                missing.append(label)

        js_runtime = self.settings.ytdlp_js_runtime.split(":", 1)[0].strip()
        if js_runtime and shutil.which(js_runtime) is None:
            missing.append(f"JavaScript runtime ({js_runtime})")
        return missing

    def _update(self, job: Job, **values: object) -> None:
        with self._lock:
            for name, value in values.items():
                setattr(job, name, value)
            job.touch()
            self._persist(job)

    def _persist(self, job: Job) -> None:
        directory = self.jobs_dir / job.id
        directory.mkdir(parents=True, exist_ok=True)
        temp = directory / "job.json.tmp"
        target = directory / "job.json"
        temp.write_text(json.dumps(job.public_dict(), ensure_ascii=False, indent=2), "utf-8")
        temp.replace(target)

    def _append_warning(self, job: Job, message: str) -> None:
        with self._lock:
            job.warnings.append(message[:500])
            job.touch()
            self._persist(job)

    def _process(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return

        root = self.jobs_dir / job.id
        work_dir = root / "work"
        output_dir = root / "output"
        work_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            missing = self.missing_tools()
            if missing:
                raise ToolError(f"missing_tools:{','.join(missing)}")

            self._update(job, status="scanning", stage="scanning", progress=0.01)
            title, entries, truncated = self._scan_playlist(job.playlist_url)
            if not entries:
                raise ToolError("playlist_empty_or_unavailable")

            self._update(
                job,
                title=safe_filename(title, "YouTube playlist", 100),
                total_items=len(entries),
                truncated=truncated,
                status="running",
                stage="downloading",
                progress=0.02,
            )

            for index, entry in enumerate(entries, start=1):
                self._ensure_free_space()
                self._update(
                    job,
                    current_item=index,
                    current_title=entry.title,
                    stage="downloading",
                    progress=max(0.02, (index - 1) / len(entries)),
                )
                try:
                    source = self._download_entry(job, entry, index, work_dir)
                    source_size = source.stat().st_size
                    self._update(job, input_bytes=job.input_bytes + source_size, stage="encoding")
                    last_report = [0.0, 0.0]

                    def report_encode_progress(value: float) -> None:
                        now_mono = time.monotonic()
                        if (
                            value >= 1.0
                            or value - last_report[0] >= 0.01
                            or now_mono - last_report[1] >= 1.0
                        ):
                            last_report[:] = [value, now_mono]
                            self._update(
                                job,
                                progress=min(
                                    0.995,
                                    ((index - 1) + 0.25 + (0.70 * value))
                                    / len(entries),
                                ),
                            )

                    final = self._encode_or_keep_smaller(
                        source=source,
                        output_dir=output_dir,
                        index=index,
                        entry=entry,
                        profile=job.profile,
                        on_progress=report_encode_progress,
                        on_warning=lambda message: self._append_warning(
                            job, f"{index}: {entry.title}: {message}"
                        ),
                    )
                    final_size = final.stat().st_size
                    self._update(
                        job,
                        output_bytes=job.output_bytes + final_size,
                        completed_items=job.completed_items + 1,
                        progress=index / len(entries),
                    )
                except Exception as exc:
                    self._append_warning(job, f"{index}: {entry.title}: {self._short_error(exc)}")
                    self._update(
                        job,
                        failed_items=job.failed_items + 1,
                        progress=index / len(entries),
                    )
                finally:
                    for leftover in work_dir.iterdir():
                        if leftover.is_file():
                            leftover.unlink(missing_ok=True)

            if job.completed_items == 0:
                raise ToolError("all_items_failed")

            self._update(
                job,
                status="ready",
                stage="ready",
                current_title="",
                progress=1.0,
                finished_at=datetime.now(UTC),
            )
        except Exception as exc:
            self._update(
                job,
                status="error",
                stage="error",
                error=self._short_error(exc),
                finished_at=datetime.now(UTC),
            )

    def _scan_playlist(self, url: str) -> tuple[str, list[PlaylistEntry], bool]:
        limit = self.settings.max_playlist_items
        command = [
            self.settings.ytdlp_bin,
            "--ignore-config",
            "--flat-playlist",
            "--dump-single-json",
            "--no-warnings",
            "--no-progress",
            "--playlist-end",
            str(limit + 1),
            "--js-runtimes",
            self.settings.ytdlp_js_runtime,
            url,
        ]
        result = self._run(command, timeout=self.settings.scan_timeout_seconds)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ToolError("playlist_metadata_invalid") from exc

        raw_entries = payload.get("entries") or []
        entries: list[PlaylistEntry] = []
        for raw in raw_entries:
            video_id = str(raw.get("id") or "").strip()
            if not valid_video_id(video_id):
                continue
            duration_raw = raw.get("duration")
            duration = int(duration_raw) if isinstance(duration_raw, (int, float)) else None
            if duration and duration > self.settings.max_video_duration_seconds:
                continue
            title = safe_filename(str(raw.get("title") or video_id), video_id, 120)
            entries.append(PlaylistEntry(video_id=video_id, title=title, duration=duration))

        truncated = len(raw_entries) > limit
        return str(payload.get("title") or "YouTube playlist"), entries[:limit], truncated

    def _download_entry(self, job: Job, entry: PlaylistEntry, index: int, work_dir: Path) -> Path:
        template = f"{index:03d} - %(title).100B [%(id)s].%(ext)s"
        max_size = f"{self.settings.max_source_megabytes}M"
        max_height = job.profile.max_height
        command = [
            self.settings.ytdlp_bin,
            "--ignore-config",
            "--no-playlist",
            "--no-warnings",
            "--no-progress",
            "--windows-filenames",
            "--continue",
            "--retries",
            "5",
            "--fragment-retries",
            "5",
            "--socket-timeout",
            "20",
            "--concurrent-fragments",
            "4",
            "--js-runtimes",
            self.settings.ytdlp_js_runtime,
            "--match-filters",
            f"!is_live & duration <=? {self.settings.max_video_duration_seconds}",
            "--max-filesize",
            max_size,
            "--format",
            f"bv*[height<=?{max_height}]+ba/b[height<=?{max_height}]",
            "--format-sort",
            f"res:{max_height},fps",
            "--merge-output-format",
            "mkv",
            "--paths",
            str(work_dir),
            "--output",
            template,
            "--print",
            "after_move:filepath",
            f"https://www.youtube.com/watch?v={entry.video_id}",
        ]
        result = self._run(command, timeout=self.settings.download_timeout_seconds)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise ToolError("download_path_missing")

        source = Path(lines[-1]).resolve()
        base = work_dir.resolve()
        if not source.is_relative_to(base) or not source.is_file():
            raise ToolError("download_path_unsafe")
        return source

    def _encode_or_keep_smaller(
        self,
        *,
        source: Path,
        output_dir: Path,
        index: int,
        entry: PlaylistEntry,
        profile: EncodeProfile,
        on_progress: Callable[[float], None],
        on_warning: Callable[[str], None] = lambda _message: None,
    ) -> Path:
        stem = safe_filename(f"{index:03d} - {entry.title}", f"video-{index:03d}", 140)
        encoded_temp = output_dir / f".{stem}.{secrets.token_hex(4)}.part.mp4"
        encoded_final = unique_destination(output_dir, stem, ".mp4")

        command = [
            self.settings.handbrake_bin,
            "--input",
            str(source),
            "--output",
            str(encoded_temp),
            "--format",
            "av_mp4",
            "--encoder",
            profile.encoder,
            "--encoder-preset",
            profile.encoder_preset,
            "--quality",
            str(profile.quality),
            "--maxWidth",
            str(profile.max_width),
            "--maxHeight",
            str(profile.max_height),
            "--keep-display-aspect",
            "--modulus",
            "2",
            "--rate",
            "30",
            "--pfr",
            "--audio",
            "1",
            "--aencoder",
            "av_aac",
            "--ab",
            str(profile.audio_kbps),
            "--mixdown",
            "stereo",
            "--optimize",
            "--no-markers",
        ]

        try:
            self._run_streaming(
                command,
                timeout=self.settings.transcode_timeout_seconds,
                on_progress=on_progress,
            )
        except Exception as exc:
            encoded_temp.unlink(missing_ok=True)
            on_warning(f"handbrake_failed_kept_source:{self._short_error(exc)}")
            return self._move_source(source, output_dir, stem)

        if not encoded_temp.is_file() or encoded_temp.stat().st_size == 0:
            encoded_temp.unlink(missing_ok=True)
            on_warning("handbrake_empty_output_kept_source")
            return self._move_source(source, output_dir, stem)

        source_size = source.stat().st_size
        encoded_size = encoded_temp.stat().st_size
        if profile.prefer_smaller_source and encoded_size >= int(source_size * 0.98):
            encoded_temp.unlink(missing_ok=True)
            return self._move_source(source, output_dir, stem)

        encoded_temp.replace(encoded_final)
        source.unlink(missing_ok=True)
        return encoded_final

    @staticmethod
    def _move_source(source: Path, output_dir: Path, stem: str) -> Path:
        suffix = source.suffix.lower() if source.suffix else ".mkv"
        destination = unique_destination(output_dir, stem, suffix)
        shutil.move(str(source), destination)
        return destination

    def _ensure_free_space(self) -> None:
        required = self.settings.min_free_gigabytes * 1024**3
        if shutil.disk_usage(self.settings.data_dir).free < required:
            raise ToolError("insufficient_free_space")

    @staticmethod
    def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("LC_ALL", "C.UTF-8")
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError("tool_timeout") from exc
        if result.returncode != 0:
            tail = (result.stderr or result.stdout)[-1200:].strip()
            raise ToolError(f"tool_failed:{tail or result.returncode}")
        return result

    @staticmethod
    def _run_streaming(
        command: list[str], timeout: int, on_progress: Callable[[float], None]
    ) -> None:
        """Run a CLI while reading progress from a pipe on Linux and Windows."""

        env = os.environ.copy()
        env.setdefault("LC_ALL", "C.UTF-8")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=0,
            env=env,
        )
        assert process.stdout is not None

        chunks: "queue.Queue[bytes | BaseException | None]" = queue.Queue()

        def read_output() -> None:
            try:
                while True:
                    chunk = process.stdout.read(65_536)
                    if not chunk:
                        break
                    chunks.put(chunk)
            except BaseException as exc:
                chunks.put(exc)
            finally:
                chunks.put(None)

        reader = threading.Thread(
            target=read_output,
            name="tool-output-reader",
            daemon=True,
        )
        reader.start()

        started = time.monotonic()
        tail: list[str] = []
        buffer = ""

        def consume(text: str) -> None:
            nonlocal buffer, tail
            buffer += text
            parts = re.split(r"[\r\n]+", buffer)
            buffer = parts.pop()
            for line in parts:
                if not line:
                    continue
                tail.append(line)
                tail = tail[-20:]
                match = _PERCENT_RE.search(line)
                if match:
                    on_progress(min(100.0, float(match.group("percent"))) / 100.0)

        try:
            stream_finished = False
            while not stream_finished:
                elapsed = time.monotonic() - started
                if elapsed > timeout:
                    raise ToolError("tool_timeout")

                try:
                    item = chunks.get(timeout=min(0.25, max(0.01, timeout - elapsed)))
                except queue.Empty:
                    continue

                if item is None:
                    stream_finished = True
                elif isinstance(item, BaseException):
                    raise ToolError(f"tool_output_failed:{item}") from item
                else:
                    consume(item.decode("utf-8", errors="replace"))

            if buffer.strip():
                tail.append(buffer.strip())
                match = _PERCENT_RE.search(buffer)
                if match:
                    on_progress(min(100.0, float(match.group("percent"))) / 100.0)

            remaining = max(0.1, timeout - (time.monotonic() - started))
            try:
                return_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise ToolError("tool_timeout") from exc
        finally:
            if process.poll() is None:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            process.stdout.close()
            reader.join(timeout=2)

        if return_code != 0:
            raise ToolError(f"tool_failed:{' | '.join(tail)[-1200:]}")

    @staticmethod
    def _short_error(exc: Exception) -> str:
        text = str(exc).replace("\n", " ").strip()
        return text[:500] or exc.__class__.__name__

    def _cleanup_loop(self) -> None:
        while not self._stop_cleanup.wait(600):
            self._cleanup_once()

    def _cleanup_once(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=self.settings.job_ttl_hours)
        stale: list[str] = []
        with self._lock:
            for job_id, job in self._jobs.items():
                if job.status in {"ready", "error"} and job.updated_at < cutoff:
                    stale.append(job_id)
        for job_id in stale:
            self.delete(job_id)

        cutoff_timestamp = cutoff.timestamp()
        known = set(self._jobs)
        for directory in self.jobs_dir.iterdir():
            if not directory.is_dir() or directory.name in known:
                continue
            marker = directory / "job.json"
            try:
                modified = marker.stat().st_mtime if marker.exists() else directory.stat().st_mtime
            except OSError:
                continue
            if modified < cutoff_timestamp:
                shutil.rmtree(directory, ignore_errors=True)
