from __future__ import annotations

import hashlib
import hmac
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROFILES, Settings
from .domain import InputError, safe_filename
from .worker import JobManager
from .zipstream import stream_zip

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
settings = Settings.from_env()
manager = JobManager(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    manager.start_cleanup()
    yield
    manager.stop()


app = FastAPI(
    title="CR20KB Offline Video Saver",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


class SessionRequest(BaseModel):
    key: str = Field(default="", max_length=512)


class JobRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    profile: str = Field(default="compact", max_length=32)
    rights_confirmed: bool = False


def _session_token() -> str:
    if not settings.access_key:
        return ""
    return hmac.new(
        settings.access_key.encode("utf-8"),
        b"cr20kb-offline-video-saver-session-v1",
        hashlib.sha256,
    ).hexdigest()


def _authorized(cookie: str | None, header: str | None) -> bool:
    if not settings.access_key:
        return True
    cookie_ok = bool(cookie) and hmac.compare_digest(cookie, _session_token())
    header_ok = bool(header) and hmac.compare_digest(header, settings.access_key)
    return cookie_ok or header_ok


def require_access(
    ovs_access: str | None = Cookie(default=None),
    x_access_key: str | None = Header(default=None),
) -> None:
    if not _authorized(ovs_access, x_access_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="access_denied")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    )
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


@app.exception_handler(InputError)
async def input_error_handler(_request: Request, exc: InputError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def health() -> Response:
    missing = manager.missing_tools()
    payload = {"ok": not missing, "missing_tools": missing}
    return JSONResponse(status_code=200 if not missing else 503, content=payload)


@app.get("/api/config")
def api_config() -> dict[str, object]:
    missing = manager.missing_tools()
    return {
        "auth_required": bool(settings.access_key),
        "ready": not missing,
        "missing_tools": missing,
        "max_playlist_items": settings.max_playlist_items,
        "default_profile": "compact",
        "profiles": [profile.public_dict() for profile in PROFILES.values()],
    }


@app.post("/api/session")
def create_session(payload: SessionRequest, response: Response) -> dict[str, bool]:
    if settings.access_key and not hmac.compare_digest(payload.key, settings.access_key):
        raise HTTPException(status_code=401, detail="access_denied")
    if settings.access_key:
        response.set_cookie(
            "ovs_access",
            _session_token(),
            max_age=30 * 24 * 3600,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="strict",
            path="/",
        )
    return {"ok": True}


@app.delete("/api/session")
def delete_session(response: Response) -> dict[str, bool]:
    response.delete_cookie(
        "ovs_access",
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return {"ok": True}


@app.post("/api/jobs", dependencies=[Depends(require_access)])
def create_job(payload: JobRequest) -> dict[str, object]:
    if not payload.rights_confirmed:
        raise HTTPException(status_code=422, detail="rights_confirmation_required")
    missing = manager.missing_tools()
    if missing:
        raise HTTPException(status_code=503, detail={"missing_tools": missing})
    return manager.create(payload.url, payload.profile).public_dict()


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_access)])
def get_job(job_id: str) -> dict[str, object]:
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job.public_dict()


@app.delete("/api/jobs/{job_id}", dependencies=[Depends(require_access)])
def delete_job(job_id: str) -> dict[str, bool]:
    if not manager.delete(job_id):
        raise HTTPException(status_code=409, detail="job_not_finished_or_missing")
    return {"ok": True}


@app.get("/api/jobs/{job_id}/download", dependencies=[Depends(require_access)])
def download_job(job_id: str) -> StreamingResponse:
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    if job.status != "ready":
        raise HTTPException(status_code=409, detail="job_not_ready")

    files = manager.output_files(job_id)
    if not files:
        raise HTTPException(status_code=404, detail="job_files_missing")

    title = safe_filename(job.title or "playlist", "playlist", 100)
    encoded_name = quote(f"{title}.zip")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="playlist.zip"; filename*=UTF-8\'\'{encoded_name}'
        ),
        "Cache-Control": "private, no-store",
    }
    return StreamingResponse(stream_zip(files), media_type="application/zip", headers=headers)
