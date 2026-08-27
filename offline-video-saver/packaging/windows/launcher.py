from __future__ import annotations

import argparse
import atexit
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
import webbrowser
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

APP_NAME = "CR20KB Offline Video Saver"
USER_AGENT = "CR20KB-Offline-Video-Saver/0.1 WindowsPortable"
DEFAULT_PORT = 8787
MAX_PORT = 8797
RUNTIME_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = RUNTIME_DIR.parent
TOOLS_DIR = PACKAGE_ROOT / "tools"
DATA_DIR = PACKAGE_ROOT / "data"
CONFIG_DIR = PACKAGE_ROOT / "config"
LOGS_DIR = PACKAGE_ROOT / "logs"
MANIFEST_PATH = TOOLS_DIR / "manifest.json"
LOCK_PATH = CONFIG_DIR / "server.lock"
SERVER_INFO_PATH = CONFIG_DIR / "server.json"
LAN_INFO_PATH = PACKAGE_ROOT / "PHONE_ACCESS.txt"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    key: str
    repository: str
    executable_name: str
    archive_kind: str


TOOL_SPECS = (
    ToolSpec("yt-dlp", "yt-dlp/yt-dlp", "yt-dlp.exe", "file"),
    ToolSpec("handbrake", "HandBrake/HandBrake", "HandBrakeCLI.exe", "zip"),
    ToolSpec("ffmpeg", "BtbN/FFmpeg-Builds", "ffmpeg.exe", "zip"),
    ToolSpec("deno", "denoland/deno", "deno.exe", "zip"),
)


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def _ensure_directories() -> None:
    for directory in (TOOLS_DIR, DATA_DIR, CONFIG_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def _github_json(url: str, timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining", "unknown")
        raise RuntimeError(
            f"GitHub API returned HTTP {exc.code}; rate-limit remaining: {remaining}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach GitHub API: {exc.reason}") from exc


def _release_assets(repository: str) -> tuple[str, list[dict[str, Any]]]:
    release = _github_json(f"https://api.github.com/repos/{repository}/releases/latest")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError(f"Latest release for {repository} has no asset list")
    return str(release.get("tag_name") or "unknown"), [
        asset for asset in assets if isinstance(asset, dict)
    ]


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _select_asset(spec: ToolSpec, assets: list[dict[str, Any]]) -> dict[str, Any]:
    if spec.key == "yt-dlp":
        candidates = [asset for asset in assets if asset.get("name") == "yt-dlp.exe"]
    elif spec.key == "deno":
        candidates = [
            asset
            for asset in assets
            if asset.get("name") == "deno-x86_64-pc-windows-msvc.zip"
        ]
    elif spec.key == "handbrake":
        candidates = [
            asset
            for asset in assets
            if re.fullmatch(
                r"HandBrakeCLI-[0-9.]+-win-x86_64\.zip",
                str(asset.get("name") or ""),
            )
        ]
        candidates.sort(
            key=lambda asset: _version_tuple(
                re.search(r"HandBrakeCLI-([0-9.]+)-", str(asset["name"])).group(1)
            ),
            reverse=True,
        )
    elif spec.key == "ffmpeg":
        stable: list[tuple[tuple[int, ...], dict[str, Any]]] = []
        for asset in assets:
            name = str(asset.get("name") or "")
            match = re.fullmatch(
                r"ffmpeg-n(?P<version>[0-9.]+)-latest-win64-gpl-shared-(?P=version)\.zip",
                name,
            )
            if match:
                stable.append((_version_tuple(match.group("version")), asset))
        stable.sort(key=lambda pair: pair[0], reverse=True)
        candidates = [pair[1] for pair in stable]
        if not candidates:
            candidates = [
                asset
                for asset in assets
                if asset.get("name") == "ffmpeg-master-latest-win64-gpl-shared.zip"
            ]
    else:
        raise RuntimeError(f"Unknown tool spec: {spec.key}")

    if not candidates:
        raise RuntimeError(f"No supported Windows x64 asset found for {spec.repository}")
    return candidates[0]


def _expected_sha256(asset: dict[str, Any]) -> str:
    digest = str(asset.get("digest") or "")
    if not digest.startswith("sha256:"):
        raise RuntimeError(
            f"GitHub did not provide a SHA-256 digest for {asset.get('name', 'asset')}"
        )
    value = digest.removeprefix("sha256:").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeError(f"Invalid SHA-256 digest for {asset.get('name', 'asset')}")
    return value


def _download(url: str, destination: Path, expected_sha256: str) -> None:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT},
    )
    hasher = hashlib.sha256()
    downloaded = 0
    last_percent = -1
    try:
        with urllib.request.urlopen(request, timeout=120) as response, destination.open(
            "wb"
        ) as target:
            length_raw = response.headers.get("Content-Length")
            total = int(length_raw) if length_raw and length_raw.isdigit() else 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                target.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                if total:
                    percent = min(100, int(downloaded * 100 / total))
                    if percent >= last_percent + 5 or percent == 100:
                        print(
                            f"\r  {percent:3d}% · {downloaded / 1024**2:,.1f} MB",
                            end="",
                            flush=True,
                        )
                        last_percent = percent
                elif downloaded // (10 * 1024**2) != (downloaded - len(chunk)) // (
                    10 * 1024**2
                ):
                    print(
                        f"\r  {downloaded / 1024**2:,.1f} MB",
                        end="",
                        flush=True,
                    )
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Download failed: {exc.reason}") from exc
    finally:
        print()

    actual = hasher.hexdigest()
    if actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch: expected {expected_sha256}, downloaded {actual}"
        )


def _safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            candidate = (destination / member.filename).resolve()
            if not candidate.is_relative_to(root):
                raise RuntimeError(f"Unsafe ZIP path: {member.filename}")
        archive.extractall(destination)


def _find_executable(root: Path, executable_name: str) -> Path:
    matches = [
        path
        for path in root.rglob(executable_name)
        if path.is_file() and path.name.lower() == executable_name.lower()
    ]
    if not matches:
        raise RuntimeError(f"{executable_name} was not found after extraction")
    matches.sort(key=lambda path: (len(path.parts), str(path).lower()))
    return matches[0]


def _read_manifest() -> dict[str, Any]:
    try:
        payload = json.loads(MANIFEST_PATH.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": 1, "tools": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("tools"), dict):
        return {"schema": 1, "tools": {}}
    return payload


def _write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(MANIFEST_PATH)


def _manifest_executable(entry: Any) -> Path | None:
    if not isinstance(entry, dict):
        return None
    relative = entry.get("executable")
    if not isinstance(relative, str) or not relative:
        return None
    candidate = (PACKAGE_ROOT / relative).resolve()
    if not candidate.is_relative_to(PACKAGE_ROOT.resolve()) or not candidate.is_file():
        return None
    return candidate


def _install_tool(spec: ToolSpec, manifest: dict[str, Any]) -> Path:
    print(f"\n[{spec.key}] Looking up the current official release...")
    release_tag, assets = _release_assets(spec.repository)
    asset = _select_asset(spec, assets)
    asset_name = str(asset.get("name") or "")
    asset_url = str(asset.get("browser_download_url") or "")
    expected_sha256 = _expected_sha256(asset)
    if not asset_url.startswith("https://github.com/"):
        raise RuntimeError(f"Unexpected download URL for {asset_name}")

    temporary_root = TOOLS_DIR / f".install-{spec.key}-{uuid.uuid4().hex}"
    content_root = temporary_root / "content"
    archive_path = temporary_root / asset_name
    target_root = TOOLS_DIR / spec.key
    backup_root = TOOLS_DIR / f".backup-{spec.key}-{uuid.uuid4().hex}"
    temporary_root.mkdir(parents=True, exist_ok=False)

    try:
        print(f"Downloading {asset_name} ({release_tag})")
        _download(asset_url, archive_path, expected_sha256)

        if spec.archive_kind == "zip":
            _safe_extract_zip(archive_path, content_root)
        else:
            content_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(archive_path), str(content_root / asset_name))

        executable = _find_executable(content_root, spec.executable_name)
        executable_relative_inside = executable.relative_to(content_root)

        if target_root.exists():
            target_root.rename(backup_root)
        try:
            shutil.move(str(content_root), str(target_root))
        except BaseException:
            if backup_root.exists() and not target_root.exists():
                backup_root.rename(target_root)
            raise
        shutil.rmtree(backup_root, ignore_errors=True)

        installed_executable = target_root / executable_relative_inside
        relative_to_package = installed_executable.relative_to(PACKAGE_ROOT)
        manifest.setdefault("tools", {})[spec.key] = {
            "repository": spec.repository,
            "release": release_tag,
            "asset": asset_name,
            "sha256": expected_sha256,
            "executable": relative_to_package.as_posix(),
            "installed_at": datetime.now(UTC).isoformat(),
        }
        _write_manifest(manifest)
        print(f"Installed: {installed_executable}")
        return installed_executable
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
        shutil.rmtree(backup_root, ignore_errors=True)


def _ensure_tools(update: bool = False) -> dict[str, Path]:
    manifest = _read_manifest()
    installed: dict[str, Path] = {}
    for spec in TOOL_SPECS:
        existing = _manifest_executable(manifest.get("tools", {}).get(spec.key))
        if existing is not None and not update:
            installed[spec.key] = existing
            continue
        installed[spec.key] = _install_tool(spec, manifest)

    missing = [spec.key for spec in TOOL_SPECS if spec.key not in installed]
    if missing:
        raise RuntimeError(f"Tool installation incomplete: {', '.join(missing)}")
    return installed


def _health_ok(url: str) -> bool:
    try:
        request = urllib.request.Request(
            f"{url.rstrip('/')}/healthz", headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.load(response)
        return bool(payload.get("ok"))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_server_info() -> dict[str, Any]:
    try:
        payload = json.loads(SERVER_INFO_PATH.read_text("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _existing_server_url() -> str | None:
    info = _read_server_info()
    url = info.get("local_url")
    if isinstance(url, str) and _health_ok(url):
        return url
    return None


def _acquire_lock() -> int | None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            descriptor = os.open(
                LOCK_PATH,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            return descriptor
        except FileExistsError:
            existing_url = _existing_server_url()
            if existing_url:
                print(f"{APP_NAME} is already running: {existing_url}")
                webbrowser.open(existing_url)
                return None

            try:
                pid = int(LOCK_PATH.read_text("ascii").strip())
            except (OSError, ValueError):
                pid = 0
            if _pid_exists(pid):
                print("Another launcher instance is preparing or starting the service.")
                print("Wait for its window instead of starting a second copy.")
                return None
            LOCK_PATH.unlink(missing_ok=True)
            if attempt:
                break
    raise RuntimeError("Cannot acquire the portable launcher lock")


def _release_lock(descriptor: int | None) -> None:
    if descriptor is not None:
        try:
            os.close(descriptor)
        except OSError:
            pass
    LOCK_PATH.unlink(missing_ok=True)
    SERVER_INFO_PATH.unlink(missing_ok=True)


def _choose_port(bind_host: str, requested: int | None) -> int:
    candidates = [requested] if requested else list(range(DEFAULT_PORT, MAX_PORT + 1))
    for port in candidates:
        if port is None or not 1 <= port <= 65_535:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((bind_host, port))
            except OSError:
                continue
        return port
    raise RuntimeError("No free port found in the 8787-8797 range")


def _lan_addresses() -> list[str]:
    candidates: set[str] = set()
    try:
        candidates.update(
            result[4][0]
            for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
        )
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            candidates.add(probe.getsockname()[0])
    except OSError:
        pass

    addresses: list[str] = []
    for value in candidates:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.version != 4 or address.is_loopback or address.is_link_local:
            continue
        if address.is_private:
            addresses.append(str(address))
    return sorted(set(addresses), key=lambda value: tuple(int(part) for part in value.split(".")))


def _access_key() -> str:
    path = CONFIG_DIR / "access-key.txt"
    try:
        value = path.read_text("utf-8").strip()
    except OSError:
        value = ""
    if len(value) < 20:
        value = secrets.token_urlsafe(24)
        path.write_text(value + "\n", encoding="utf-8")
    return value


def _write_lan_info(port: int, key: str, addresses: list[str]) -> None:
    lines = [
        "CR20KB Offline Video Saver — access from phone/tablet",
        "",
        "Use only on your private Wi-Fi or private VPN. Do not forward this port.",
        "",
    ]
    if addresses:
        lines.extend(f"http://{address}:{port}" for address in addresses)
    else:
        lines.append("LAN address was not detected automatically. Run ipconfig.")
    lines.extend(["", f"Access key: {key}", ""])
    LAN_INFO_PATH.write_text("\n".join(lines), encoding="utf-8")


def _configure_application(tools: dict[str, Path], mode: str) -> tuple[str, str]:
    executable_dirs = []
    for path in tools.values():
        directory = str(path.parent)
        if directory not in executable_dirs:
            executable_dirs.append(directory)
    os.environ["PATH"] = os.pathsep.join(executable_dirs + [os.environ.get("PATH", "")])
    os.environ.update(
        {
            "DATA_DIR": str(DATA_DIR),
            "YTDLP_BIN": str(tools["yt-dlp"]),
            "YTDLP_JS_RUNTIME": "deno",
            "HANDBRAKE_BIN": str(tools["handbrake"]),
            "FFMPEG_BIN": str(tools["ffmpeg"]),
            "COOKIE_SECURE": "false",
            "PYTHONUTF8": "1",
        }
    )
    if mode == "lan":
        key = _access_key()
        os.environ["APP_ACCESS_KEY"] = key
        return "0.0.0.0", key
    os.environ["APP_ACCESS_KEY"] = ""
    return "127.0.0.1", ""


def _open_browser_when_ready(url: str) -> None:
    for _attempt in range(120):
        if _health_ok(url):
            webbrowser.open(url)
            return
        time.sleep(0.5)
    print(f"The service did not become ready automatically. Try opening {url}")


def _write_server_info(mode: str, port: int, local_url: str) -> None:
    payload = {
        "pid": os.getpid(),
        "mode": mode,
        "port": port,
        "local_url": local_url,
        "started_at": datetime.now(UTC).isoformat(),
    }
    SERVER_INFO_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _self_test() -> int:
    required = [
        RUNTIME_DIR / "app" / "main.py",
        RUNTIME_DIR / "app" / "static" / "index.html",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Portable package is incomplete: {', '.join(missing)}")

    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401

    fake_assets = [
        {"name": "ffmpeg-master-latest-win64-gpl-shared.zip"},
        {"name": "ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip"},
        {"name": "ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip"},
    ]
    selected = _select_asset(
        ToolSpec("ffmpeg", "BtbN/FFmpeg-Builds", "ffmpeg.exe", "zip"),
        fake_assets,
    )
    if selected.get("name") != "ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip":
        raise RuntimeError("FFmpeg asset selection self-test failed")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        archive = root / "safe.zip"
        extracted = root / "out"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("bin/tool.exe", b"test")
        _safe_extract_zip(archive, extracted)
        if not (extracted / "bin" / "tool.exe").is_file():
            raise RuntimeError("ZIP extraction self-test failed")

    print("Portable launcher self-test: OK")
    return 0


def _write_error_log(exc: BaseException) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = LOGS_DIR / f"launcher-{timestamp}.log"
    path.write_text(
        f"{APP_NAME}\n{datetime.now(UTC).isoformat()}\n\n"
        + "".join(traceback.format_exception(exc)),
        encoding="utf-8",
    )
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--mode", choices=("local", "lan"), default="local")
    parser.add_argument("--port", type=int)
    parser.add_argument("--update-tools", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    _configure_console()
    _ensure_directories()
    args = _parse_args()

    if args.self_test:
        return _self_test()

    lock_descriptor = _acquire_lock()
    if lock_descriptor is None:
        return 0
    atexit.register(_release_lock, lock_descriptor)

    try:
        if args.update_tools:
            print("Updating portable media tools from their official releases...")
            _ensure_tools(update=True)
            print("\nTools updated successfully.")
            return 0

        print(APP_NAME)
        print("First launch downloads verified tools into this portable folder.")
        tools = _ensure_tools(update=False)
        bind_host, key = _configure_application(tools, args.mode)
        port = _choose_port(bind_host, args.port)
        local_url = f"http://127.0.0.1:{port}"
        _write_server_info(args.mode, port, local_url)

        if args.mode == "lan":
            addresses = _lan_addresses()
            _write_lan_info(port, key, addresses)
            print("\nPhone/tablet mode is enabled for the private network.")
            if addresses:
                for address in addresses:
                    print(f"  http://{address}:{port}")
            else:
                print("  LAN address was not detected automatically; run ipconfig.")
            print(f"  Access key: {key}")
            print(f"  Saved to: {LAN_INFO_PATH}")
            print("  Allow Python only on Private networks if Windows Firewall asks.")
            print("  Do not forward this port on the router.")
        else:
            print(f"\nLocal address: {local_url}")

        print("Keep this window open. Press Ctrl+C here to stop the service.\n")
        if not args.no_browser:
            threading.Thread(
                target=_open_browser_when_ready,
                args=(local_url,),
                name="browser-opener",
                daemon=True,
            ).start()

        os.chdir(RUNTIME_DIR)
        import uvicorn

        uvicorn.run(
            "app.main:app",
            host=bind_host,
            port=port,
            log_level="info",
            access_log=False,
        )
        return 0
    finally:
        _release_lock(lock_descriptor)
        try:
            atexit.unregister(_release_lock)
        except Exception:
            pass


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\nService stopped.")
        exit_code = 0
    except Exception as error:
        try:
            _ensure_directories()
            log_path = _write_error_log(error)
        except Exception:
            log_path = Path("launcher-error.log")
        print(f"\nERROR: {error}", file=sys.stderr)
        print(f"Diagnostic log: {log_path}", file=sys.stderr)
        exit_code = 1
    raise SystemExit(exit_code)
