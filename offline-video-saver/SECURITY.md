# Security

## Supported use

The service accepts only HTTPS YouTube playlist links. It extracts the
validated `list` identifier and rebuilds a canonical YouTube URL before
calling yt-dlp. It does not accept arbitrary fetch URLs, cookies, browser
profiles, Google credentials, or DRM-protected media.

## Deployment

- Set a long random `APP_ACCESS_KEY`.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Keep the Compose port bound to `127.0.0.1` and expose it through a maintained
  reverse proxy such as Caddy.
- Do not expose the service without authentication or resource limits.
- Keep yt-dlp, HandBrake, FFmpeg, the base image, and Python packages updated.
- Treat downloaded media as untrusted input.

Report vulnerabilities privately to the repository owner. Do not include
private playlist links, access keys, cookies, or downloaded media in an issue.
