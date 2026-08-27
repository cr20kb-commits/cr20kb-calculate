from pathlib import Path

import pytest

from app.domain import InputError, canonical_playlist_url, safe_filename, unique_destination, valid_job_id


def test_playlist_url_is_canonicalized():
    url, playlist_id = canonical_playlist_url(
        "https://m.youtube.com/watch?v=abc&list=PL1234567890_abc&utm_source=x"
    )
    assert url == "https://www.youtube.com/playlist?list=PL1234567890_abc"
    assert playlist_id == "PL1234567890_abc"


@pytest.mark.parametrize(
    "value",
    [
        "http://www.youtube.com/playlist?list=PL1234567890",
        "https://example.com/playlist?list=PL1234567890",
        "https://user@youtube.com/playlist?list=PL1234567890",
        "https://youtube.com/playlist",
        "not a url",
    ],
)
def test_playlist_url_rejects_unsafe_values(value):
    with pytest.raises(InputError):
        canonical_playlist_url(value)


def test_safe_filename_removes_cross_platform_trouble():
    assert safe_filename(' CON:<bad>/name?. ') == "CON bad name"
    assert safe_filename("CON") == "_CON"
    assert safe_filename("\x00\x01") == "video"


def test_unique_destination_adds_suffix(tmp_path: Path):
    (tmp_path / "video.mp4").write_bytes(b"x")
    assert unique_destination(tmp_path, "video", ".mp4").name == "video (2).mp4"


def test_job_id_validation():
    assert valid_job_id("Abcdefghijklmnopqrstu_12")
    assert not valid_job_id("../../etc/passwd")
