"""EXIF reader tests on synthetic JPEGs only (no real photos in the repository)."""

import io
from fractions import Fraction

import pytest
from digimax.exif import ExifError, build_test_jpeg, read_exif

A402_LIKE = {
    0x829A: (5, Fraction(1000, 18467)),  # continuous AE exposure time seen on the unit (EXP-0006)
    0x829D: (5, Fraction(7, 2)),
    0x8822: (3, 2),
    0x8827: (3, 200),
    0x9000: (7, b"0220"),
    0x9204: (10, Fraction(0)),
    0x9207: (3, 2),
    0x9209: (3, 1),
    0x920A: (5, Fraction(146, 25)),
    0xA002: (4, 2272),
    0xA003: (4, 1704),
    0x9003: (2, "2005:05:25 12:00:00"),  # DateTimeOriginal: must NOT be returned
    0x9286: (7, b"ASCII\x00\x00\x00secret"),  # UserComment: must NOT be returned
}
IFD0 = {
    0x010F: (2, "Samsung Techwin co., Ltd."),
    0x0110: (2, "Digimax A402"),
    0x0131: (2, "M4051S-0525"),
    0x013B: (2, "Some Owner"),  # Artist: must NOT be returned
}


@pytest.mark.parametrize("big_endian", [False, True])
def test_reads_identity_and_exposure(big_endian: bool) -> None:
    jpg = build_test_jpeg(A402_LIKE, IFD0, big_endian=big_endian)
    t = read_exif(io.BytesIO(jpg)).tags
    assert t["make"] == "Samsung Techwin co., Ltd."
    assert t["model"] == "Digimax A402"
    assert t["software"] == "M4051S-0525"
    assert t["exposure_time"] == Fraction(1000, 18467)
    assert t["f_number"] == Fraction(7, 2)
    assert t["iso"] == 200
    assert t["exposure_program_name"] == "normal program"
    assert t["flash_fired"] is True
    assert t["exif_version"] == "0220"
    assert (t["pixel_x"], t["pixel_y"]) == (2272, 1704)


def test_private_fields_are_never_returned() -> None:
    t = read_exif(io.BytesIO(build_test_jpeg(A402_LIKE, IFD0))).tags
    text = repr(t)
    for forbidden in ("2005:05:25", "secret", "Some Owner"):
        assert forbidden not in text
    assert not {"artist", "date_time_original", "user_comment", "gps"} & set(t)


def test_not_a_jpeg() -> None:
    with pytest.raises(ExifError, match="not a JPEG"):
        read_exif(io.BytesIO(b"GIF89a"))


def test_jpeg_without_exif() -> None:
    with pytest.raises(ExifError, match="no Exif"):
        read_exif(io.BytesIO(b"\xff\xd8\xff\xd9"))


def test_corrupt_offsets_fail_cleanly() -> None:
    jpg = bytearray(build_test_jpeg(A402_LIKE, IFD0))
    tiff = jpg.index(b"II*\x00")
    jpg[tiff + 4 : tiff + 8] = (0x7FFFFFF0).to_bytes(4, "little")  # IFD0 offset far out of range
    with pytest.raises(ExifError):
        read_exif(io.BytesIO(bytes(jpg)))
