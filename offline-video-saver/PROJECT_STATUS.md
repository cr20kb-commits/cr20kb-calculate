# CR20KB Offline Video Saver — Project Status

Last updated: 2026-08-27

## Classification

- Priority: **P2**.
- State: **pivoted to Cliply-based architecture; waiting for the CR20KB GitHub fork; previous custom downloader paused**.
- Previous custom branch: `feature/offline-video-saver-mvp`.
- Previous custom pull request: `#7` in `cr20kb-commits/cr20kb-calculate`.

## Product decision

The project remains **local-first**, but the download engine is no longer a CR20KB custom implementation.

A live residential-Windows test on 2026-08-27 confirmed that **Cliply 0.3.6** successfully downloads YouTube media from the supplied playlist on the user's home PC. Therefore CR20KB should not duplicate Cliply's mature local yt-dlp/FFmpeg engine.

The CR20KB value proposition is now a post-download **Compact Mode** layered on top of a working Cliply base:

`download -> compact transcode -> verify -> compare sizes -> keep smaller file`

## Validation result

The supplied playlist was tested in two local Windows implementations:

1. The CR20KB portable preview started correctly, downloaded its dependencies, opened the UI, and read the playlist, but its own Windows wrapper rejected downloaded paths with `download_path_unsafe`. This is a CR20KB implementation defect, not a YouTube residential-IP block.
2. Cliply 0.3.6 was installed on the same home PC and successfully downloaded the media. The observed source-size estimates for a 1:57:27 video were approximately:
   - 1080p: 2.67 GB
   - 720p: 1.46 GB
   - 480p: 816 MB
   - 360p: 427 MB

Conclusion: the remaining product problem is **storage size**, not reliable downloading.

## Cliply base

Cliply is an active GPL-3.0 Electron application using yt-dlp, FFmpeg and Deno. Relevant architecture already present upstream:

- `src/main/services/ytdlp-engine.js` owns yt-dlp process execution, machine-readable output markers, progress, error classification, cookies and PO-token escalation.
- `src/main/services/download-runner.js` owns the lifecycle from download start to `settleCompleted()` and exposes the final `filePath` and `fileSize`.
- `src/main/ipc-handlers.js` connects the runner to the renderer and terminal download events.

The clean CR20KB insertion point is **after `handle.promise` resolves and before the runner emits the final completed state**. A dedicated compact-transcoder service should receive the downloaded `filePath`, transcode to a temporary output, validate it, compare sizes, atomically keep the smaller file, then return the final path to `settleCompleted()`.

## Compact Mode MVP

Required user-facing modes:

- **Original** — no re-encode.
- **Compact 1080p H.265** — preserves Full HD when available; initial target software x265/HEVC around CRF/RF 28 with approximately 96 kbps AAC audio.
- **Compact 720p H.265** — default balance; initial target software x265/HEVC around CRF/RF 29 with approximately 80 kbps AAC audio.
- **Minimum size 480p H.265** — initial target software x265/HEVC around CRF/RF 31 with approximately 64 kbps AAC audio.

Optional later mode:

- **AV1 archival** — potentially smaller files, but too slow for the default UX unless hardware and encoding time are explicitly accepted.

Because Cliply already bundles FFmpeg, the first implementation should use its existing FFmpeg binary with `libx265` instead of adding HandBrakeCLI as another large runtime dependency. HandBrake-specific presets are not required to achieve the storage goal.

The 1080p mode is not allowed to upscale lower-resolution input. All compact modes preserve aspect ratio and cap, rather than force, their target height.

## Safety and data handling

Compact processing rules:

1. Never overwrite the source in place.
2. Write to a temporary sibling file.
3. Require a successful encoder exit code and a non-empty playable output.
4. Compare source and encoded sizes.
5. Replace the source only when the encoded file is meaningfully smaller (recommended threshold: at least 5%).
6. Otherwise delete the temporary encoded file and keep the original.
7. Use an atomic rename/move when finalizing.
8. Preserve a clear progress stage such as `compressing` rather than pretending the download itself is still running.
9. Preserve the original automatically when the source codec is already more efficient or the new encode does not meet the size threshold.

## Expected storage range

For the validated 1:57:27 source, reasonable first engineering estimates are:

- Compact 1080p H.265: roughly **1.1–1.8 GB** depending on motion and source codec.
- Compact 720p H.265: roughly **0.6–0.9 GB**.
- Minimum-size 480p H.265: roughly **0.25–0.45 GB**.

These are estimates, not guarantees. If the YouTube source is already efficient AV1/VP9, the compact result may not be smaller; the keep-smaller rule must retain the original in that case.

## Licensing

Cliply's public repository is GPL-3.0. Any public CR20KB derivative based on Cliply must preserve GPL-3.0 obligations and source availability. Do not copy Cliply code into the existing MIT wrapper as if it were MIT-licensed.

## Previous CR20KB custom implementation

The custom FastAPI/portable implementation remains useful only as a source of ideas and tests:

- compact profiles;
- keep-smaller logic;
- one-at-a-time processing;
- streaming ZIP;
- Windows portable packaging experiments.

It is **not** the preferred downloader base going forward. PR #7 must not be merged as the product implementation.

## Next checkpoint

1. User creates the GitHub fork `cr20kb-commits/Cliply` because the connected GitHub tool can modify existing repositories but cannot create a new repository/fork.
2. Create branch `feature/cr20kb-compact-mode-mvp` in the fork.
3. Add a `compact-transcoder` service using Cliply's existing FFmpeg binary.
4. Insert post-processing between successful yt-dlp completion and `settleCompleted()`.
5. Add UI selector: Original / Compact 1080p / Compact 720p / Minimum size 480p.
6. Add unit tests and a Windows synthetic-media smoke test.
7. Build an unsigned Windows preview artifact.
8. User tests when convenient: first one short video, then the validated 1:57:27 video.
9. Record source size, output size, elapsed encode time, CPU load and playback verification before enabling playlist-wide compact processing by default.
