# CR20KB Offline Video Saver — Project Status

Last updated: 2026-08-27

## Classification

- Priority: **P2**.
- State: **active development; Windows portable preview packaged; draft pull request; not deployed; not merged**.
- Canonical branch: `feature/offline-video-saver-mvp`.
- Canonical pull request: `#7` in `cr20kb-commits/cr20kb-calculate`.

## Product decision

The project is **local-first**.

The media worker runs on a user-owned Windows computer, NAS, or home server.
The responsive web interface may be opened from the user's other devices over
LAN or a private VPN. A public VPS is not the primary media-worker deployment
target.

## Windows portable preview

The branch now produces a Windows x64 portable ZIP through GitHub Actions.

- No Docker, administrator rights, or system Python installation is required.
- The ZIP carries an official Python embeddable runtime and the CR20KB web app.
- The first launch downloads yt-dlp, HandBrakeCLI, a shared FFmpeg build, and
  Deno directly from their current official GitHub releases.
- Each downloaded asset is checked against the SHA-256 digest returned by the
  GitHub release API before installation.
- `START_LOCAL.cmd` serves only the current computer.
- `START_FOR_PHONE.cmd` enables private-LAN access with a generated key and
  writes connection details to `PHONE_ACCESS.txt`.
- `UPDATE_TOOLS.cmd` refreshes the external media tools.

The portable launcher and application subprocess reader are designed and
unit-tested for Windows. A Windows runner builds the ZIP, unpacks it, imports
the embedded runtime, starts the FastAPI service, and checks the health endpoint
and web page before uploading the artifact.

## Verified deployment boundary

Live tests on 2026-08-27 used the supplied public playlist and the real
application image.

1. GitHub Actions read playlist metadata and titles successfully.
2. YouTube rejected the first media request with an interactive verification
   challenge.
3. A second GitHub Actions run with the optional PO-token provider running
   correctly received the same rejection.
4. A separate test from the CR20KB Namecheap Ubuntu VPS built the image
   successfully, but YouTube again rejected the media request before any media
   bytes were downloaded.

Conclusion: cloud/data-centre IP reputation is the blocker. It is not a
HandBrake, FastAPI, Docker, queue, or ZIP-streaming failure.

## Verified application components

- Playlist URL validation and canonicalization.
- One-at-a-time job processing.
- Three HandBrake profiles.
- Smaller-source-versus-encoded selection.
- Streaming ZIP without a second full archive on disk.
- Resource limits, access key, TTL cleanup, and loopback binding.
- RU/EN responsive interface.
- Configurable yt-dlp JavaScript runtime (`node` in Docker, `deno` in portable).
- Cross-platform streaming progress reader for HandBrakeCLI.
- Unit tests, JavaScript, shell, PowerShell, Compose validation, Docker build,
  real H.265 transcode, application startup, and health endpoint.
- Windows portable build, embedded-runtime self-test, unpacked server smoke
  test, checksum file, and workflow artifact.

## v0.1 boundaries

- No server-side user account credentials.
- No browser-profile import.
- No protected-media support.
- No claim of reliable anonymous downloads from public cloud IPs.
- No open public multi-user downloader.
- Windows portable preview is currently unsigned.

## Current blocker

A successful live media download and complete HandBrake/ZIP cycle has not yet
been demonstrated from the user's residential Windows connection.

## Next checkpoint

1. Download and extract the Windows portable artifact on the user's home PC.
2. Run `START_LOCAL.cmd` and allow the first-launch tool bootstrap to finish.
3. Process the supplied playlist through the real web UI.
4. Record source size, output size, processing time, CPU load, and any YouTube
   access error.
5. Repeat the launch on the laptop after the desktop checkpoint passes.
6. Only then decide whether to add a signed one-click EXE/service and merge PR
   `#7`.
