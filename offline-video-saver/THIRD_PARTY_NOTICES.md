# Third-party notices

CR20KB Offline Video Saver is a small orchestration layer. It does not copy,
vendor, statically link, or modify HandBrake or yt-dlp source code.

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

This repository's original wrapper code is MIT licensed. That does not replace
or weaken any third-party license. Anyone publishing a prebuilt container or
binary bundle is responsible for preserving notices, providing corresponding
source where required, and satisfying the exact license obligations of the
versions they distribute.
