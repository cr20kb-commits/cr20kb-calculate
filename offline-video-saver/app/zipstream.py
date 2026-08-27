from __future__ import annotations

import io
import queue
import threading
import zipfile
from collections.abc import Iterator
from pathlib import Path


class _QueueWriter(io.RawIOBase):
    def __init__(
        self,
        chunks: "queue.Queue[bytes | BaseException | None]",
        cancelled: threading.Event,
    ) -> None:
        super().__init__()
        self._chunks = chunks
        self._cancelled = cancelled
        self._position = 0

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._position

    def seek(self, *_args: object, **_kwargs: object) -> int:
        raise OSError("stream is not seekable")

    def write(self, data: bytes | bytearray) -> int:
        chunk = bytes(data)
        if not chunk:
            return 0
        while not self._cancelled.is_set():
            try:
                self._chunks.put(chunk, timeout=0.25)
                self._position += len(chunk)
                return len(chunk)
            except queue.Full:
                continue
        raise BrokenPipeError("ZIP consumer disconnected")

    def flush(self) -> None:
        return None


def stream_zip(files: list[Path]) -> Iterator[bytes]:
    """Create a ZIP stream without writing a second archive to disk."""

    chunks: "queue.Queue[bytes | BaseException | None]" = queue.Queue(maxsize=8)
    cancelled = threading.Event()

    def publish(item: bytes | BaseException | None) -> None:
        while not cancelled.is_set():
            try:
                chunks.put(item, timeout=0.25)
                return
            except queue.Full:
                continue

    def producer() -> None:
        writer = _QueueWriter(chunks, cancelled)
        try:
            with zipfile.ZipFile(
                writer,
                mode="w",
                compression=zipfile.ZIP_STORED,
                allowZip64=True,
            ) as archive:
                for file_path in files:
                    archive.write(file_path, arcname=file_path.name)
        except BrokenPipeError:
            return
        except BaseException as exc:
            publish(exc)
        finally:
            publish(None)

    threading.Thread(target=producer, name="zip-stream", daemon=True).start()

    try:
        while True:
            item = chunks.get()
            if item is None:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        cancelled.set()
