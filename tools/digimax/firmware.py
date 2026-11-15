"""Offline, read-only analysis of firmware / update / dump files.

Nothing here executes, unpacks-to-disk or modifies its input. ISA "hints" are
statistical heuristics and are always reported with ``confidence: heuristic``;
the spec forbids concluding an ISA from a single clue (section 7, Phase B).
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MAX_INPUT = 256 * 1024 * 1024  # refuse absurd inputs rather than exhausting memory

SIGNATURES: list[tuple[str, bytes]] = [
    ("jpeg", b"\xff\xd8\xff"),
    ("riff", b"RIFF"),
    ("zip", b"PK\x03\x04"),
    ("gzip", b"\x1f\x8b\x08"),
    ("pe/mz", b"MZ"),
    ("elf", b"\x7fELF"),
    ("png", b"\x89PNG\r\n\x1a\n"),
    ("bmp", b"BM"),
    ("cab", b"MSCF"),
    ("lzma", b"\x5d\x00\x00"),
    ("exif", b"Exif\x00\x00"),
]
# Signatures too short to be meaningful anywhere but offset 0.
_OFFSET0_ONLY = {"pe/mz", "bmp", "lzma"}

INTERESTING = re.compile(
    rb"(?i)(v(?:er(?:sion)?)?[ ._]?\d+\.\d+|\b(?:19|20)\d{2}[./-]?\d{2}[./-]?\d{2}\b|"
    rb"[A-Z0-9_]{2,8}\.(?:BIN|TXT|ROM|HEX|FW|IMG|DAT)\b|samsung|sunplus|spca\d+|mega\d+|"
    rb"digimax|kenox|dcim|copyright|\bsd\b|sdhc|mmc|nand|fat(?:12|16|32))"
)


@dataclass
class Region:
    offset: int
    length: int
    entropy: float
    kind: str  # "fill-00", "fill-ff", "low", "code/data", "compressed/encrypted"


@dataclass
class FirmwareReport:
    path: str
    size: int
    sha256: str
    sha1: str
    md5: str
    entropy: float
    fill_ff_ratio: float
    fill_00_ratio: float
    regions: list[Region] = field(default_factory=list)
    signatures: list[dict[str, Any]] = field(default_factory=list)
    strings_ascii: int = 0
    strings_utf16: int = 0
    interesting_strings: list[dict[str, Any]] = field(default_factory=list)
    isa_hints: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def shannon(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _classify(block: bytes, ent: float) -> str:
    if block.count(0xFF) == len(block):
        return "fill-ff"
    if block.count(0) == len(block):
        return "fill-00"
    if ent > 7.6:
        return "compressed/encrypted"
    if ent < 2.0:
        return "low"
    return "code/data"


def regions(data: bytes, block: int = 4096) -> list[Region]:
    out: list[Region] = []
    for off in range(0, len(data), block):
        chunk = data[off : off + block]
        ent = shannon(chunk)
        kind = _classify(chunk, ent)
        if out and out[-1].kind == kind:
            prev = out[-1]
            total = prev.length + len(chunk)
            prev.entropy = round((prev.entropy * prev.length + ent * len(chunk)) / total, 3)
            prev.length = total
        else:
            out.append(Region(off, len(chunk), round(ent, 3), kind))
    return out


def ascii_strings(data: bytes, min_len: int = 5) -> list[tuple[int, str]]:
    return [
        (m.start(), m.group().decode("ascii"))
        for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data)
    ]


def utf16_strings(data: bytes, min_len: int = 5) -> list[tuple[int, str]]:
    pat = rb"(?:[\x20-\x7e]\x00){%d,}" % min_len
    return [(m.start(), m.group().decode("utf-16-le")) for m in re.finditer(pat, data)]


def find_signatures(data: bytes, limit: int = 200) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for name, sig in SIGNATURES:
        if name in _OFFSET0_ONLY:
            if data.startswith(sig):
                hits.append({"offset": 0, "type": name})
            continue
        start = 0
        while len(hits) < limit:
            i = data.find(sig, start)
            if i < 0:
                break
            if name == "riff" and data[i + 8 : i + 12] not in (b"WAVE", b"AVI "):
                start = i + 1
                continue
            hits.append(
                {
                    "offset": i,
                    "type": name
                    if name != "riff"
                    else f"riff/{data[i + 8 : i + 12].decode().strip().lower()}",
                }
            )
            start = i + 1
    return sorted(hits, key=lambda h: int(h["offset"]))


def isa_hints(data: bytes) -> list[dict[str, Any]]:
    """Weak statistical clues only. Every hint must be corroborated (spec 7B)."""
    hints: list[dict[str, Any]] = []
    sample = data[: 1024 * 1024]
    if len(sample) >= 3 and sample[0] == 0x02:
        target = sample[1] << 8 | sample[2]
        hints.append(
            {
                "isa": "8051-family",
                "clue": f"offset 0 is LJMP 0x{target:04X} (8051 reset vector shape)",
                "confidence": "heuristic",
            }
        )
    if len(sample) >= 32:
        words = [int.from_bytes(sample[i : i + 4], "little") for i in range(0, 32, 4)]
        if sum(1 for w in words if w >> 24 == 0xEA or (w & 0xFFFFF000) == 0xE59FF000) >= 6:
            hints.append(
                {
                    "isa": "ARM (A32)",
                    "clue": "first 8 words look like an ARM exception vector table (B / LDR PC)",
                    "confidence": "heuristic",
                }
            )
    if sample:
        c = Counter(sample)
        n = len(sample)
        # LCALL(0x12), RET(0x22), MOVX @DPTR(0xE0/0xF0), MOV DPTR,#(0x90): common 8051 opcodes
        ratio = sum(c[b] for b in (0x12, 0x22, 0xE0, 0xF0, 0x90)) / n
        if ratio > 0.06:
            hints.append(
                {
                    "isa": "8051-family",
                    "clue": f"opcode-frequency ratio {ratio:.3f} for LCALL/RET/MOVX/MOV DPTR",
                    "confidence": "heuristic",
                }
            )
        thumb_push = len(re.findall(rb"[\x00-\xff][\xb4\xb5]", sample[:65536]))
        thumb_pop = len(re.findall(rb"[\x00-\xff][\xbc\xbd]", sample[:65536]))
        if thumb_push > 64 and thumb_pop > 64:
            hints.append(
                {
                    "isa": "ARM Thumb",
                    "clue": "frequent PUSH/POP {..,lr/pc} halfword patterns",
                    "confidence": "heuristic",
                }
            )
    hints.extend(mips_hints(sample))
    return hints


# MIPS32 major opcodes that dominate compiled code: lui, addiu, lw, sw, jal, beq, bne, ori
_MIPS_COMMON = {0x0F, 0x09, 0x23, 0x2B, 0x03, 0x04, 0x05, 0x0D}
_JR_RA = 0x03E00008  # jr $ra
_KSEG_HI = (0x8000, 0x8001, 0x8002, 0x8003, 0xA000, 0xA001, 0xA002, 0xA003, 0xBFC0, 0xAC00,
            0xAC01, 0xAC02, 0xAC03, 0xAC04, 0xAC05)  # fmt: skip


def mips_hints(sample: bytes) -> list[dict[str, Any]]:
    """MIPS32 statistics for both byte orders (relevant to H-013, R3000 reports)."""
    out: list[dict[str, Any]] = []
    n = len(sample) // 4
    if n < 256:
        return out
    for order, name in (("<", "little-endian"), (">", "big-endian")):
        words = struct.unpack(f"{order}{n}I", sample[: n * 4])
        jr_ra = sum(1 for w in words if w == _JR_RA)
        common = sum(1 for w in words if (w >> 26) in _MIPS_COMMON)
        lui_kseg = sum(1 for w in words if (w >> 26) == 0x0F and (w & 0xFFFF) in _KSEG_HI)
        ratio = common / n
        if jr_ra >= 8 and ratio > 0.35:
            out.append(
                {
                    "isa": f"MIPS32 ({name})",
                    "clue": (
                        f"{jr_ra} 'jr $ra' returns, {ratio:.0%} of words use common MIPS opcodes, "
                        f"{lui_kseg} 'lui' loads of KSEG0/KSEG1 upper halves"
                    ),
                    "confidence": "heuristic",
                }
            )
    return out


def load(path: str | Path) -> bytes:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"{p} is not a regular file")
    size = p.stat().st_size
    if size > MAX_INPUT:
        raise ValueError(f"{p} is {size} bytes; refusing inputs above {MAX_INPUT}")
    return p.read_bytes()


def inspect(path: str | Path, *, max_strings: int = 60) -> FirmwareReport:
    data = load(path)
    a_str = ascii_strings(data)
    u_str = utf16_strings(data)
    interesting: list[dict[str, Any]] = []
    for off, s in a_str:
        if INTERESTING.search(s.encode()):
            interesting.append({"offset": off, "encoding": "ascii", "text": s[:120]})
    for off, s in u_str:
        if INTERESTING.search(s.encode()):
            interesting.append({"offset": off, "encoding": "utf-16le", "text": s[:120]})
    n = max(len(data), 1)
    rep = FirmwareReport(
        path=str(path),
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        sha1=hashlib.sha1(data, usedforsecurity=False).hexdigest(),
        md5=hashlib.md5(data, usedforsecurity=False).hexdigest(),
        entropy=round(shannon(data), 4),
        fill_ff_ratio=round(data.count(0xFF) / n, 4),
        fill_00_ratio=round(data.count(0) / n, 4),
        regions=regions(data),
        signatures=find_signatures(data),
        strings_ascii=len(a_str),
        strings_utf16=len(u_str),
        interesting_strings=sorted(interesting, key=lambda d: int(d["offset"]))[:max_strings],
        isa_hints=isa_hints(data),
    )
    rep.notes.append(
        "An update package is not necessarily a complete dump, and a mass-storage image is "
        "not firmware. ISA hints are heuristics, not determinations."
    )
    if len(data) and len(data) & (len(data) - 1) == 0:
        rep.notes.append(f"size is a power of two ({len(data)}): consistent with a raw flash dump")
    return rep


@dataclass
class CompareReport:
    a: str
    b: str
    size_a: int
    size_b: int
    sha256_a: str
    sha256_b: str
    identical: bool
    differing_bytes: int
    identical_ratio: float
    ranges: list[dict[str, int]]
    ranges_truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare(
    a_path: str | Path, b_path: str | Path, *, merge_gap: int = 16, max_ranges: int = 500
) -> CompareReport:
    a, b = load(a_path), load(b_path)
    n = min(len(a), len(b))
    ranges: list[list[int]] = []
    diff = 0
    i = 0
    while i < n:
        if a[i] != b[i]:
            diff += 1
            if ranges and i - (ranges[-1][0] + ranges[-1][1]) <= merge_gap:
                ranges[-1][1] = i - ranges[-1][0] + 1
            else:
                ranges.append([i, 1])
        i += 1
    tail = abs(len(a) - len(b))
    if tail:
        ranges.append([n, tail])
        diff += tail
    total = max(len(a), len(b), 1)
    return CompareReport(
        a=str(a_path),
        b=str(b_path),
        size_a=len(a),
        size_b=len(b),
        sha256_a=hashlib.sha256(a).hexdigest(),
        sha256_b=hashlib.sha256(b).hexdigest(),
        identical=a == b,
        differing_bytes=diff,
        identical_ratio=round(1 - diff / total, 6),
        ranges=[{"offset": o, "length": ln} for o, ln in ranges[:max_ranges]],
        ranges_truncated=len(ranges) > max_ranges,
    )
