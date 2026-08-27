# CR20KB Offline Video Saver

A deliberately small self-hosted web interface for downloading a YouTube
playlist you are entitled to save, reducing storage with HandBrakeCLI, and
returning the result as one streaming ZIP.

## What v0.1 does

1. Open the page on a phone, tablet, or computer.
2. Paste a **public or unlisted YouTube playlist URL**.
3. Select one of three profiles:
   - Compact: 720p H.265
   - Minimum space: 480p H.265
   - Compatible: 720p H.264
4. The server processes one video at a time.
5. Compact profiles compare the HandBrake result with the downloaded source
   and keep whichever is smaller.
6. Download one ZIP. The ZIP is streamed and is not duplicated on server disk.

The wrapper invokes `yt-dlp`, `HandBrakeCLI`, and `ffmpeg` as separate
processes. It does not fork or embed HandBrake source code.

## Deliberate v0.1 limits

- No Google login or account playlist picker.
- No private playlists, cookies, browser-profile import, or DRM bypass.
- One worker to keep CPU and temporary disk usage predictable.
- In-memory queue; completed files remain only for the configured TTL.
- YouTube changes can break downloads until yt-dlp is updated.

A true “choose from my YouTube account” picker belongs in a later OAuth-based
version because it requires a Google Cloud project, redirect URI, consent
screen, token storage policy, and privacy review. For v0.1, sharing/copying the
playlist link is the simpler and safer cross-device flow.

## Run with Docker Compose

```bash
cp .env.example .env
# Replace APP_ACCESS_KEY and keep COOKIE_SECURE=false for plain local HTTP.
docker compose up --build -d
```

Open `http://127.0.0.1:8787`.

For a public deployment, leave the Compose port on loopback and put Caddy or
another maintained HTTPS reverse proxy in front of it. Set
`COOKIE_SECURE=true` when HTTPS is enabled.

## Configuration

| Variable | Default | Meaning |
| --- | ---: | --- |
| `APP_ACCESS_KEY` | empty | Shared access key. Set it before network exposure. |
| `COOKIE_SECURE` | `false` | Secure session cookie; enable behind HTTPS. |
| `MAX_PLAYLIST_ITEMS` | `50` | Hard playlist item limit. |
| `MAX_VIDEO_DURATION_SECONDS` | `14400` | Per-video duration limit. |
| `MAX_SOURCE_MEGABYTES` | `4096` | yt-dlp source file limit. |
| `MIN_FREE_GIGABYTES` | `2` | Stop before each item below this free space. |
| `MAX_RETAINED_JOBS` | `6` | Maximum active/queued jobs. |
| `JOB_TTL_HOURS` | `24` | Retention for completed/error jobs. |
| `SCAN_TIMEOUT_SECONDS` | `180` | Playlist metadata timeout. |
| `DOWNLOAD_TIMEOUT_SECONDS` | `7200` | Per-video download timeout. |
| `TRANSCODE_TIMEOUT_SECONDS` | `21600` | Per-video HandBrake timeout. |

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload
```

Local development requires `yt-dlp`, `HandBrakeCLI`, and `ffmpeg` on `PATH`
for real jobs. Unit tests do not download media.

## Storage behavior

Only one source video and one temporary encoded result are normally present
during processing. After comparison, the losing copy is deleted. Final media
is retained until TTL cleanup or manual deletion. ZIP creation uses
`ZIP_STORED` because video is already compressed and streams directly to the
client without creating a second full archive.

## Legal and licensing

Use the software only for material you own, created, or are otherwise entitled
to download. Site terms and copyright law may impose additional restrictions.

Original wrapper code is MIT licensed. Runtime dependencies keep their own
licenses; see `THIRD_PARTY_NOTICES.md`. This is technical project structure,
not legal advice.
