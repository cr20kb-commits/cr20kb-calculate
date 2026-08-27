from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class EncodeProfile:
    id: str
    label_ru: str
    label_en: str
    description_ru: str
    description_en: str
    max_width: int
    max_height: int
    encoder: str
    encoder_preset: str
    quality: float
    audio_kbps: int
    prefer_smaller_source: bool = True

    def public_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in (
            "max_width",
            "max_height",
            "encoder",
            "encoder_preset",
            "quality",
            "audio_kbps",
            "prefer_smaller_source",
        ):
            data.pop(key, None)
        return data


PROFILES: dict[str, EncodeProfile] = {
    "compact": EncodeProfile(
        id="compact",
        label_ru="Компактно · 720p H.265",
        label_en="Compact · 720p H.265",
        description_ru="Баланс читаемости, размера и времени обработки.",
        description_en="Balanced readability, file size, and processing time.",
        max_width=1280,
        max_height=720,
        encoder="x265",
        encoder_preset="medium",
        quality=29.0,
        audio_kbps=80,
    ),
    "tiny": EncodeProfile(
        id="tiny",
        label_ru="Минимум места · 480p H.265",
        label_en="Minimum space · 480p H.265",
        description_ru="Для лекций, инструкций и просмотра на телефоне.",
        description_en="For lectures, tutorials, and phone viewing.",
        max_width=854,
        max_height=480,
        encoder="x265",
        encoder_preset="medium",
        quality=31.0,
        audio_kbps=64,
    ),
    "compatible": EncodeProfile(
        id="compatible",
        label_ru="Совместимо · 720p H.264",
        label_en="Compatible · 720p H.264",
        description_ru="Чуть больше файл, зато открывается почти везде.",
        description_en="A little larger, but plays almost everywhere.",
        max_width=1280,
        max_height=720,
        encoder="x264",
        encoder_preset="medium",
        quality=25.0,
        audio_kbps=96,
        prefer_smaller_source=False,
    ),
}


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    max_playlist_items: int
    max_video_duration_seconds: int
    max_source_megabytes: int
    min_free_gigabytes: int
    max_retained_jobs: int
    job_ttl_hours: int
    scan_timeout_seconds: int
    download_timeout_seconds: int
    transcode_timeout_seconds: int
    access_key: str
    cookie_secure: bool
    ytdlp_bin: str
    handbrake_bin: str
    ffmpeg_bin: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "./data")).expanduser(),
            max_playlist_items=_env_int("MAX_PLAYLIST_ITEMS", 50, 1, 500),
            max_video_duration_seconds=_env_int(
                "MAX_VIDEO_DURATION_SECONDS", 14_400, 60, 86_400
            ),
            max_source_megabytes=_env_int("MAX_SOURCE_MEGABYTES", 4096, 50, 100_000),
            min_free_gigabytes=_env_int("MIN_FREE_GIGABYTES", 2, 0, 10_000),
            max_retained_jobs=_env_int("MAX_RETAINED_JOBS", 6, 1, 100),
            job_ttl_hours=_env_int("JOB_TTL_HOURS", 24, 1, 720),
            scan_timeout_seconds=_env_int("SCAN_TIMEOUT_SECONDS", 180, 30, 3600),
            download_timeout_seconds=_env_int(
                "DOWNLOAD_TIMEOUT_SECONDS", 7200, 60, 86_400
            ),
            transcode_timeout_seconds=_env_int(
                "TRANSCODE_TIMEOUT_SECONDS", 21_600, 60, 172_800
            ),
            access_key=os.getenv("APP_ACCESS_KEY", "").strip(),
            cookie_secure=_env_bool("COOKIE_SECURE", False),
            ytdlp_bin=os.getenv("YTDLP_BIN", "yt-dlp"),
            handbrake_bin=os.getenv("HANDBRAKE_BIN", "HandBrakeCLI"),
            ffmpeg_bin=os.getenv("FFMPEG_BIN", "ffmpeg"),
        )
