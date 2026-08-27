from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import EncodeProfile

_PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,100}$")
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,40}$")
_WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class InputError(ValueError):
    """A user-correctable validation error."""


class ToolError(RuntimeError):
    """An external CLI tool failed."""


def canonical_playlist_url(raw_url: str) -> tuple[str, str]:
    """Return a canonical YouTube playlist URL containing only the list id.

    Keeping only the validated playlist id prevents the worker from becoming
    a general-purpose URL fetcher.
    """

    value = raw_url.strip()
    if not value or len(value) > 2048:
        raise InputError("playlist_url_invalid")

    parsed = urlparse(value)
    if parsed.scheme.lower() != "https":
        raise InputError("playlist_url_https_required")
    if parsed.username or parsed.password or parsed.port:
        raise InputError("playlist_url_invalid")

    host = (parsed.hostname or "").rstrip(".").lower()
    allowed = {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
    if host not in allowed:
        raise InputError("playlist_url_youtube_only")

    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    if not _PLAYLIST_ID_RE.fullmatch(playlist_id):
        raise InputError("playlist_id_missing")

    return f"https://www.youtube.com/playlist?list={playlist_id}", playlist_id


def valid_video_id(value: str) -> bool:
    return bool(_VIDEO_ID_RE.fullmatch(value))


def valid_job_id(value: str) -> bool:
    return bool(_JOB_ID_RE.fullmatch(value))


def safe_filename(value: str, fallback: str = "video", max_length: int = 120) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "C")
    normalized = re.sub(r'[<>:"/\\|?*]+', " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")
    if not normalized:
        normalized = fallback
    if normalized.upper() in _WINDOWS_RESERVED:
        normalized = f"_{normalized}"
    return normalized[:max_length].rstrip(" .") or fallback


def unique_destination(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem} ({index}){suffix}"
        index += 1
    return candidate


@dataclass(slots=True)
class PlaylistEntry:
    video_id: str
    title: str
    duration: int | None = None


@dataclass(slots=True)
class Job:
    id: str
    playlist_url: str
    playlist_id: str
    profile: EncodeProfile
    status: str = "queued"
    stage: str = "queued"
    title: str = ""
    current_title: str = ""
    current_item: int = 0
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    progress: float = 0.0
    input_bytes: int = 0
    output_bytes: int = 0
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    @property
    def saved_bytes(self) -> int:
        return max(0, self.input_bytes - self.output_bytes)

    def public_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "stage": self.stage,
            "title": self.title,
            "current_title": self.current_title,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "progress": round(self.progress, 4),
            "input_bytes": self.input_bytes,
            "output_bytes": self.output_bytes,
            "saved_bytes": self.saved_bytes,
            "truncated": self.truncated,
            "warnings": self.warnings[-10:],
            "error": self.error,
            "profile": self.profile.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
