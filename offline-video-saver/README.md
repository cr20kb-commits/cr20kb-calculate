# CR20KB Offline Video Saver

A deliberately small self-hosted web interface for downloading a YouTube
playlist you are entitled to save, reducing storage with HandBrakeCLI, and
returning the result as one streaming ZIP.

## Recommended deployment model

Run the application on a computer, NAS, or home server that you control, then
open its private address from a phone, tablet, or another computer on the same
LAN or private VPN.

This keeps the interface cross-device while media requests originate from the
user-owned connection. Anonymous downloads from cloud and data-centre IP
addresses are not reliable: YouTube may require an interactive sign-in or bot
check even for public videos.

Do not deploy a shared Google account, exported browser cookies, or user
credentials with this public service. The project intentionally does not
accept them.

## Windows portable preview

The branch builds a Windows x64 portable ZIP in GitHub Actions. It is intended
for Windows 10 22H2 and Windows 11 and does not require Docker, administrator
rights, or a system Python installation.

1. Download the `CR20KB-VideoSaver-Windows-x64` workflow artifact.
2. Extract the ZIP completely.
3. Double-click `START_LOCAL.cmd`.
4. On first launch, the portable launcher downloads the current official
   Windows releases of yt-dlp, HandBrakeCLI, FFmpeg, and Deno.
5. Every downloaded component is checked against the SHA-256 digest returned
   by the corresponding GitHub release API before it is installed into the
   local `tools` folder.

`START_FOR_PHONE.cmd` binds the service to the private network, generates a
local access key, and writes the current LAN addresses to `PHONE_ACCESS.txt`.
It should only be used on a trusted private LAN or private VPN. It does not add
firewall rules or expose a router port.

The portable ZIP contains the CR20KB application, an official Python
embeddable runtime, and Python web dependencies. It deliberately does not
redistribute HandBrake, FFmpeg, yt-dlp, or Deno binaries; those are obtained
directly from their upstream releases on the user's first run.

## What v0.1 does

1. Open the page on a phone, tablet, or computer.
2. Paste a **public or unlisted YouTube playlist URL**.
3. Select one of three profiles:
   - Compact: 720p H.265
   - Minimum space: 480p H.265
   - Compatible: 720p H.264
4. The worker processes one video at a time.
5. Compact profiles compare the HandBrake result with the downloaded source
   and keep whichever is smaller.
6. Download one ZIP. The ZIP is streamed and is not duplicated on worker disk.

The wrapper invokes `yt-dlp`, `HandBrakeCLI`, and `ffmpeg` as separate
processes. It does not fork or embed HandBrake source code.

## Deliberate v0.1 limits

- No Google account playlist picker.
- No private playlists, cookies, browser-profile import, or DRM bypass.
- One worker to keep CPU and temporary disk usage predictable.
- In-memory queue; completed files remain only for the configured TTL.
- YouTube changes or IP reputation can prevent a download even while playlist
  metadata remains visible.

A later account picker may use Google OAuth only to list playlists. That would
not by itself authenticate yt-dlp media downloads, so it is separate from this
MVP.

## Run with Docker Compose

```bash
cp .env.example .env
# Replace APP_ACCESS_KEY before opening the service to another device.
docker compose up --build -d
```

Open `http://127.0.0.1:8787` on the host computer.

To open the UI from your own phone or tablet, set `APP_BIND_ADDRESS` in `.env`
to the host's LAN or private-VPN address, restart Compose, and open
`http://HOST_ADDRESS:8787`. Keep the host firewall enabled and use a strong
access key.

For HTTPS behind Caddy or another maintained reverse proxy, keep the service
bound to loopback and set `COOKIE_SECURE=true`.

## Test a host before deployment

The rest of the pipeline is deterministic and covered by CI. The unstable part
is whether YouTube accepts media requests from a particular public IP. These
scripts build the real application image, download only a short sample from
the first playlist item, verify that it is non-empty, and delete it.

Windows PowerShell:

```powershell
.\scripts\test-playlist-access.ps1 -PlaylistUrl "PLAYLIST_URL"
```

Linux or NAS shell:

```bash
chmod +x scripts/test-playlist-access.sh
./scripts/test-playlist-access.sh "PLAYLIST_URL"
```

Use the scripts only for material you are entitled to download. They do not
use cookies or credentials.

## Optional PO-token provider

The image includes the `bgutil-ytdlp-pot-provider` plugin, but it is inactive
by default. An optional internal provider can be enabled with:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.pot.yml \
  up --build -d
```

The provider port is not published outside the Compose network. This may help
with some YouTube client requirements, but it is **not** a guaranteed solution
for a cloud IP bot check.

## Verified boundaries

The automated test suite verifies:

- URL and filename validation;
- source-versus-encoded size selection;
- streaming ZIP validity;
- JavaScript, shell, and PowerShell syntax;
- Linux and Windows subprocess progress handling;
- both Docker Compose configurations;
- Docker image construction;
- the yt-dlp wrapper and optional plugin installation;
- a real H.265 HandBrakeCLI transcode inside the image;
- application startup and health checks;
- creation and unpacked smoke testing of the Windows portable ZIP.

A live test on 2026-08-27 confirmed that a GitHub-hosted runner could read a
public playlist and its titles, but YouTube rejected the actual media request
with a sign-in/bot-check challenge. The same result occurred with the optional
BgUtils provider running correctly. A separate test from the CR20KB Namecheap
VPS produced the same rejection before media bytes were downloaded. Therefore
a successful cloud CI build is not represented as proof that anonymous cloud
downloads will work.

## Configuration

| Variable | Default | Meaning |
| --- | ---: | --- |
| `APP_ACCESS_KEY` | empty | Shared access key. Set it before network exposure. |
| `COOKIE_SECURE` | `false` | Secure session cookie; enable behind HTTPS. |
| `APP_BIND_ADDRESS` | `127.0.0.1` | Host address published by Docker Compose. |
| `MAX_PLAYLIST_ITEMS` | `50` | Hard playlist item limit. |
| `MAX_VIDEO_DURATION_SECONDS` | `14400` | Per-video duration limit. |
| `MAX_SOURCE_MEGABYTES` | `4096` | yt-dlp source file limit. |
| `MIN_FREE_GIGABYTES` | `2` | Stop before each item below this free space. |
| `MAX_RETAINED_JOBS` | `6` | Maximum active/queued jobs. |
| `JOB_TTL_HOURS` | `24` | Retention for completed/error jobs. |
| `SCAN_TIMEOUT_SECONDS` | `180` | Playlist metadata timeout. |
| `DOWNLOAD_TIMEOUT_SECONDS` | `7200` | Per-video download timeout. |
| `TRANSCODE_TIMEOUT_SECONDS` | `21600` | Per-video HandBrake timeout. |
| `YTDLP_JS_RUNTIME` | `node` | JavaScript runtime name passed to yt-dlp. |
| `POT_PROVIDER_URL` | empty | Optional internal BgUtils provider URL. |
| `YOUTUBE_PLAYER_CLIENT` | `mweb` | Client selected when the provider is enabled. |

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q
uvicorn app.main:app --reload
```

Local development requires `yt-dlp`, `HandBrakeCLI`, `ffmpeg`, and the selected
JavaScript runtime on `PATH` for real jobs. Unit tests do not download media.

Build the portable Windows ZIP on Windows or a Windows GitHub runner:

```powershell
.\packaging\windows\build-portable.ps1 -OutputDir "$PWD\dist"
```

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
