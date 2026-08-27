# CR20KB Offline Video Saver — Project Status

Last updated: 2026-08-27

## Classification

- Priority: **P2**.
- State: **active development; draft pull request; not deployed; not merged**.
- Canonical branch: `feature/offline-video-saver-mvp`.
- Canonical pull request: `#7` in `cr20kb-commits/cr20kb-calculate`.

## Product decision

The project is **local-first**.

The media worker runs on a user-owned Windows computer, NAS, or home server.
The responsive web interface may be opened from the user's other devices over
LAN or a private VPN. A public VPS is not the primary media-worker deployment
target.

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
- Unit tests, JavaScript, shell, PowerShell, Compose validation, Docker build,
  real H.265 transcode, application startup, and health endpoint.

## v0.1 boundaries

- No server-side user account credentials.
- No browser-profile import.
- No protected-media support.
- No claim of reliable anonymous downloads from public cloud IPs.
- No open public multi-user downloader.

## Current blocker

A successful live media download has not yet been demonstrated from a
user-owned residential connection.

## Next checkpoint

Run the included Windows PowerShell access diagnostic on the user's main
computer. It downloads only a short fragment of the first playlist item and
removes the temporary sample and Docker image.

After a successful residential-IP diagnostic:

1. run the full web application locally;
2. complete one real playlist end-to-end through the UI;
3. measure source size, output size, processing time, and CPU load;
4. decide whether to package a one-click Windows launcher/service;
5. only then review PR `#7` for merge.
