# Security

## Supported use

The service accepts only HTTPS YouTube playlist links. It extracts the
validated `list` identifier and rebuilds a canonical YouTube URL before
calling yt-dlp. It does not accept arbitrary fetch URLs, cookies, browser
profiles, Google credentials, or DRM-protected media.

## Recommended deployment

Run the worker on a computer, NAS, or home server you control and reach it over
a trusted LAN or private VPN. This reduces exposure and avoids turning the
service into a public anonymous downloader.

- Set a long random `APP_ACCESS_KEY` before allowing another device to connect.
- Keep `APP_BIND_ADDRESS=127.0.0.1` unless private-network access is required.
- Prefer binding a specific LAN/VPN address over `0.0.0.0`.
- Keep the host firewall enabled and do not forward port `8787` from the public
  internet.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Treat downloaded media as untrusted input.
- Keep yt-dlp, HandBrake, FFmpeg, the base image, Python packages, and optional
  provider image updated.

## Optional PO-token provider

The BgUtils HTTP provider has no reason to be reachable from the public
internet. `docker-compose.pot.yml` exposes it only inside the Compose network.
Do not publish port `4416`, and do not treat the provider as authentication or
as a guaranteed bypass for YouTube IP reputation checks.

## Credentials

Do not add exported browser cookies, Google passwords, session tokens, private
playlist URLs, or downloaded media to the repository, an issue, a CI log, or a
shared server. The application intentionally has no credential-upload feature.

Report vulnerabilities privately to the repository owner. Do not include
access keys or user media in a report.
