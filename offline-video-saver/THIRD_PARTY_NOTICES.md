# Third-party notices

CR20KB Offline Video Saver is a small orchestration layer. It does not copy,
vendor, statically link, or modify HandBrake or yt-dlp source code.

## Docker deployment

Runtime components are installed independently by the container build or the
optional Compose overlay:

- **HandBrakeCLI / HandBrake** — GPL-2.0; copyright and license belong to the
  HandBrake contributors.
- **yt-dlp** — the core project is released under The Unlicense. Some optional
  dependencies and generated executables have their own licenses; consult the
  yt-dlp repository and installed packages.
- **BgUtils yt-dlp POT provider** — GPL-3.0. The Python plugin is installed as
  a package in the application image; the optional HTTP provider is pulled as
  a separate container only when `docker-compose.pot.yml` is enabled.
- **FFmpeg** — LGPL/GPL depending on the build and enabled components.
- **FastAPI, Uvicorn and Python dependencies** — their respective licenses.

## Windows portable preview

The portable ZIP includes:

- the official CPython embeddable runtime under the Python Software Foundation
  License;
- FastAPI, Uvicorn, and their Python dependencies under their respective
  licenses;
- the original CR20KB wrapper code under MIT.

The portable ZIP deliberately does **not** contain HandBrake, FFmpeg, yt-dlp,
or Deno binaries. On first launch the bootstrap downloads them directly from
their upstream GitHub release assets, verifies GitHub-provided SHA-256 digests,
and stores them in the user's local `tools` directory. Those downloaded
components retain their own licenses and notices:

- HandBrakeCLI / HandBrake — GPL-2.0;
- FFmpeg build — LGPL/GPL depending on the selected upstream build;
- yt-dlp executable — project and bundled-component licenses published by
  yt-dlp;
- Deno — MIT plus the licenses of bundled components.

This repository's MIT license does not replace or weaken any third-party
license. Anyone redistributing a pre-populated package, container, or binary
bundle is responsible for preserving notices, providing corresponding source
where required, and satisfying the exact obligations of the versions they
distribute.
