import io
import zipfile
from pathlib import Path

from app.zipstream import stream_zip


def test_stream_zip_is_valid_and_keeps_names(tmp_path: Path):
    first = tmp_path / "one.mp4"
    second = tmp_path / "два.webm"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    payload = b"".join(stream_zip([first, second]))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == ["one.mp4", "два.webm"]
        assert archive.read("one.mp4") == b"first"
        assert archive.read("два.webm") == b"second"
