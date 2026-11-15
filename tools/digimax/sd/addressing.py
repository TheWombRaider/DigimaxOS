"""Logical-sector to card-address conversion, plus address-unique test patterns.

Design rule (spec section 4.2): every storage operation in DigimaxOS is
expressed in logical 512-byte sectors (LBA). Conversion to the card's own
addressing unit happens in exactly one place, at the transport boundary:

  * SDSC / MMC (byte addressed): argument = LBA * 512, must fit 32 bits
  * SDHC / SDXC (block addressed, OCR.CCS = 1): argument = LBA

Any request that would overflow or exceed the card is rejected *before* I/O.
A transport must never silently wrap an address: wrapping is exactly the
failure mode ("aliasing") that makes a too-large card appear to work while it
overwrites its own beginning.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from enum import StrEnum

SECTOR = 512
U32_MAX = 0xFFFF_FFFF


class Addressing(StrEnum):
    BYTE = "byte"  # SDSC, MMC (<= 2 GB standard)
    BLOCK = "block"  # SDHC, SDXC


class AddressError(ValueError):
    """Raised for a request that must not be sent to the card."""


@dataclass(frozen=True)
class Geometry:
    capacity_sectors: int
    addressing: Addressing

    def __post_init__(self) -> None:
        if self.capacity_sectors <= 0:
            raise ValueError("capacity must be positive")
        if self.addressing is Addressing.BYTE and self.capacity_sectors * SECTOR - 1 > U32_MAX:
            raise ValueError(
                "byte-addressed card larger than 4 GiB cannot be addressed with a 32-bit argument"
            )
        if self.addressing is Addressing.BLOCK and self.capacity_sectors - 1 > U32_MAX:
            raise ValueError("block-addressed card larger than 2 TiB needs SDUC addressing")


def check_range(geom: Geometry, lba: int, count: int = 1) -> None:
    if count < 1:
        raise AddressError(f"sector count must be >= 1, got {count}")
    if lba < 0:
        raise AddressError(f"negative LBA {lba}")
    if lba + count > geom.capacity_sectors:
        raise AddressError(
            f"range [{lba}, {lba + count}) exceeds card capacity of {geom.capacity_sectors} sectors"
        )


def command_argument(geom: Geometry, lba: int, count: int = 1) -> int:
    """Return the 32-bit CMD17/18/24/25 argument for a validated LBA range."""
    check_range(geom, lba, count)
    arg = lba if geom.addressing is Addressing.BLOCK else lba * SECTOR
    if arg > U32_MAX:  # unreachable thanks to Geometry, kept as defence in depth
        raise AddressError(f"argument {arg:#x} does not fit in 32 bits")
    return arg


def legacy_wrapping_argument(lba: int) -> int:
    """Model of a *buggy* SDSC-only transport: byte address truncated to 32 bits.

    Used only by tests and documentation to demonstrate aliasing. Never use it
    for real I/O.
    """
    return (lba * SECTOR) & U32_MAX


# ---------------------------------------------------------------------------
# Address-unique sector patterns (SD-02 acceptance: "sector patterns unique to
# their address, no wrap or aliasing, read-back checksums").
# ---------------------------------------------------------------------------

_MAGIC = b"DGMXPAT1"
_HEADER = struct.Struct(">8sQQ")  # magic, lba, seed


def pattern_for_sector(lba: int, seed: int) -> bytes:
    """512 bytes that encode their own LBA and are cryptographically tied to it."""
    if lba < 0 or seed < 0:
        raise ValueError("lba and seed must be non-negative")
    header = _HEADER.pack(_MAGIC, lba, seed)
    body = bytearray()
    counter = 0
    while len(header) + len(body) < SECTOR - 32:
        body += hashlib.sha256(header + counter.to_bytes(4, "big")).digest()
        counter += 1
    payload = (header + bytes(body))[: SECTOR - 32]
    digest = hashlib.sha256(payload).digest()
    return payload + digest


@dataclass(frozen=True)
class PatternCheck:
    lba: int
    ok: bool
    embedded_lba: int | None
    reason: str


def verify_sector(lba: int, data: bytes, seed: int) -> PatternCheck:
    if len(data) != SECTOR:
        return PatternCheck(lba, False, None, f"length {len(data)} != {SECTOR}")
    magic, embedded_lba, embedded_seed = _HEADER.unpack_from(data)
    if magic != _MAGIC:
        if data == b"\x00" * SECTOR:
            return PatternCheck(lba, False, None, "sector is all zeros (never written or erased)")
        if data == b"\xff" * SECTOR:
            return PatternCheck(lba, False, None, "sector is all 0xFF (never written or erased)")
        return PatternCheck(lba, False, None, "no pattern header (foreign data)")
    if hashlib.sha256(data[: SECTOR - 32]).digest() != data[SECTOR - 32 :]:
        return PatternCheck(lba, False, embedded_lba, "pattern corrupted (checksum mismatch)")
    if embedded_seed != seed:
        return PatternCheck(lba, False, embedded_lba, "pattern from a different test run (seed)")
    if embedded_lba != lba:
        return PatternCheck(
            lba,
            False,
            embedded_lba,
            f"ALIASING: sector {lba} holds the pattern written for sector {embedded_lba}",
        )
    return PatternCheck(lba, True, embedded_lba, "ok")


def boundary_probe_lbas(capacity_sectors: int) -> list[int]:
    """Sample LBAs that matter for capacity bugs: edges, power-of-two boundaries, last sector.

    Sampling is NOT full coverage; reports must say which one was used (spec 4.3).
    """
    points: set[int] = {0, 1, capacity_sectors - 1, capacity_sectors - 2}
    boundary_bytes = [
        512 * 1024**2,
        1024**3,
        2 * 1024**3,
        4 * 1024**3,
        8 * 1024**3,
        16 * 1024**3,
        32 * 1024**3,
    ]
    for b in boundary_bytes:
        s = b // SECTOR
        for p in (s - 1, s, s + 1):
            if 0 <= p < capacity_sectors:
                points.add(p)
    # power-of-two sector indices (catches 16/24/32-bit truncation of LBA math)
    bit = 1
    while bit < capacity_sectors:
        for p in (bit - 1, bit):
            if 0 <= p < capacity_sectors:
                points.add(p)
        bit <<= 1
    return sorted(p for p in points if 0 <= p < capacity_sectors)
