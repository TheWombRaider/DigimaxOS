"""Minimal, privacy-preserving EXIF reader (stdlib only, ADR 0001).

Extracts camera identity and *exposure* tags from a JPEG's APP1/Exif segment.
By design it never returns GPS, owner/artist, maker-note, user-comment or
date/time fields, so its output can go into public test reports without
leaking personal data. Use it for exposure-baseline analysis (issue #7).
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Any, BinaryIO

# tag id -> (name, ifd) ; only these are ever decoded
IFD0_TAGS = {0x010F: "make", 0x0110: "model", 0x0131: "software", 0x0112: "orientation"}
EXIF_TAGS = {
    0x829A: "exposure_time",
    0x829D: "f_number",
    0x8822: "exposure_program",
    0x8827: "iso",
    0x9000: "exif_version",
    0x9204: "exposure_bias",
    0x9207: "metering_mode",
    0x9208: "light_source",
    0x9209: "flash",
    0x920A: "focal_length",
    0xA002: "pixel_x",
    0xA003: "pixel_y",
    0xA402: "exposure_mode",
    0xA403: "white_balance",
    0xA406: "scene_capture_type",
    0x9201: "shutter_speed_value",
    0x9202: "aperture_value",
    0x9205: "max_aperture_value",
}
EXIF_IFD_POINTER = 0x8769

_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}

EXPOSURE_PROGRAMS = {
    0: "not defined", 1: "manual", 2: "normal program", 3: "aperture priority",
    4: "shutter priority", 5: "creative", 6: "action", 7: "portrait", 8: "landscape",
}  # fmt: skip


class ExifError(ValueError):
    pass


@dataclass
class ExifSummary:
    tags: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _app1(f: BinaryIO, limit: int = 256 * 1024) -> bytes:
    head = f.read(2)
    if head != b"\xff\xd8":
        raise ExifError("not a JPEG (no SOI marker)")
    read = 2
    while read < limit:
        marker = f.read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            break
        if marker[1] in (0xD9, 0xDA):  # EOI / start of scan: no more metadata
            break
        (length,) = struct.unpack(">H", f.read(2))
        payload = f.read(length - 2)
        read += 2 + length
        if marker[1] == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return payload[6:]
    raise ExifError("no Exif APP1 segment")


def _value(tiff: bytes, endian: str, typ: int, count: int, raw: bytes) -> Any:
    size = _TYPE_SIZE.get(typ)
    if size is None:
        return None
    total = size * count
    if total > 4:
        (offset,) = struct.unpack(endian + "I", raw)
        if offset + total > len(tiff):
            raise ExifError("tag value points outside the TIFF block")
        data = tiff[offset : offset + total]
    else:
        data = raw[:total]
    if typ == 2:
        return data.split(b"\x00", 1)[0].decode("ascii", "replace").strip()
    if typ == 7:
        return data.decode("ascii", "replace") if count == 4 else data.hex()
    if typ in (5, 10):
        fmt = endian + ("II" if typ == 5 else "ii")
        vals = []
        for i in range(count):
            num, den = struct.unpack_from(fmt, data, i * 8)
            vals.append(Fraction(num, den) if den else None)
        return vals[0] if count == 1 else vals
    fmt = {1: "B", 3: "H", 4: "I", 9: "i"}[typ]
    vals = list(struct.unpack(endian + fmt * count, data))
    return vals[0] if count == 1 else vals


def _ifd(
    tiff: bytes, endian: str, offset: int, wanted: dict[int, str]
) -> tuple[dict[str, Any], int | None]:
    if offset + 2 > len(tiff):
        raise ExifError("IFD offset outside the TIFF block")
    (n,) = struct.unpack_from(endian + "H", tiff, offset)
    if n > 512:
        raise ExifError(f"implausible IFD entry count {n}")
    out: dict[str, Any] = {}
    exif_ptr = None
    for i in range(n):
        base = offset + 2 + 12 * i
        if base + 12 > len(tiff):
            raise ExifError("IFD truncated")
        tag, typ, count = struct.unpack_from(endian + "HHI", tiff, base)
        raw = tiff[base + 8 : base + 12]
        if tag == EXIF_IFD_POINTER:
            (exif_ptr,) = struct.unpack(endian + "I", raw)
        elif tag in wanted and count < 4096:
            out[wanted[tag]] = _value(tiff, endian, typ, count, raw)
    return out, exif_ptr


def read_exif(f: BinaryIO) -> ExifSummary:
    tiff = _app1(f)
    if tiff[:2] == b"II":
        endian = "<"
    elif tiff[:2] == b"MM":
        endian = ">"
    else:
        raise ExifError("bad TIFF byte order")
    if struct.unpack_from(endian + "H", tiff, 2)[0] != 42:
        raise ExifError("bad TIFF magic")
    (ifd0,) = struct.unpack_from(endian + "I", tiff, 4)
    summary = ExifSummary()
    tags, exif_ptr = _ifd(tiff, endian, ifd0, IFD0_TAGS)
    summary.tags.update(tags)
    if exif_ptr:
        etags, _ = _ifd(tiff, endian, exif_ptr, EXIF_TAGS)
        summary.tags.update(etags)
    else:
        summary.warnings.append("no Exif sub-IFD")
    t = summary.tags
    if isinstance(t.get("exposure_program"), int):
        t["exposure_program_name"] = EXPOSURE_PROGRAMS.get(t["exposure_program"], "reserved")
    if isinstance(t.get("flash"), int):
        t["flash_fired"] = bool(t["flash"] & 1)
    return summary


def build_test_jpeg(
    tags: dict[int, tuple[int, Any]],
    ifd0: dict[int, tuple[int, Any]] | None = None,
    big_endian: bool = False,
) -> bytes:
    """Construct a tiny synthetic JPEG with an Exif block (for tests; no image data)."""
    e = ">" if big_endian else "<"

    def encode(
        entries: dict[int, tuple[int, Any]], start: int, extra_ptr: int | None
    ) -> tuple[bytes, bytes]:
        items = sorted(entries.items())
        n = len(items) + (1 if extra_ptr is not None else 0)
        table = struct.pack(e + "H", n)
        heap = b""
        heap_off = start + 2 + 12 * n + 4
        rows = []
        for tag, (typ, val) in items:
            if typ == 2:
                data = val.encode() + b"\x00"
                count = len(data)
            elif typ in (5, 10):
                fr = Fraction(val)
                data = struct.pack(e + ("II" if typ == 5 else "ii"), fr.numerator, fr.denominator)
                count = 1
            elif typ == 7:
                data = val
                count = len(data)
            else:
                data = struct.pack(e + {3: "H", 4: "I"}[typ], val)
                count = 1
            if len(data) <= 4:
                rows.append(struct.pack(e + "HHI", tag, typ, count) + data.ljust(4, b"\x00"))
            else:
                rows.append(struct.pack(e + "HHII", tag, typ, count, heap_off + len(heap)))
                heap += data + (b"\x00" if len(data) % 2 else b"")
        if extra_ptr is not None:
            rows.append(struct.pack(e + "HHII", EXIF_IFD_POINTER, 4, 1, extra_ptr))
            rows.sort(key=lambda r: struct.unpack_from(e + "H", r)[0])
        return table + b"".join(rows) + b"\x00\x00\x00\x00", heap

    header = (b"MM" if big_endian else b"II") + struct.pack(e + "HI", 42, 8)
    ifd0_entries = ifd0 or {}
    # first pass to learn IFD0 size, then place the Exif IFD right after it
    probe, probe_heap = encode(ifd0_entries, 8, 0)
    exif_off = 8 + len(probe) + len(probe_heap)
    ifd0_bytes, ifd0_heap = encode(ifd0_entries, 8, exif_off)
    exif_bytes, exif_heap = encode(tags, exif_off, None)
    tiff = header + ifd0_bytes + ifd0_heap + exif_bytes + exif_heap
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"
