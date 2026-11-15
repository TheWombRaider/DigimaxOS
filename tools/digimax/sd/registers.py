"""Decoding (and, for fixtures, encoding) of SD card OCR and CSD registers.

Bit positions follow the SD Simplified Physical Layer Specification (S5):
  * CSD_STRUCTURE 0 -> CSD Version 1.0 (Standard Capacity, SDSC)
  * CSD_STRUCTURE 1 -> CSD Version 2.0 (High/Extended Capacity, SDHC/SDXC)
  * CSD_STRUCTURE 2 -> CSD Version 3.0 (Ultra Capacity, SDUC)

The 128-bit register is handled as a Python int whose bit 0 is the
always-one end bit, exactly as numbered in the specification.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .crc import crc7

SECTOR = 512


def _bits(value: int, hi: int, lo: int) -> int:
    return (value >> lo) & ((1 << (hi - lo + 1)) - 1)


def _set(value: int, hi: int, lo: int, field: int) -> int:
    width = hi - lo + 1
    if field < 0 or field >= (1 << width):
        raise ValueError(f"field value {field} does not fit bits [{hi}:{lo}]")
    mask = ((1 << width) - 1) << lo
    return (value & ~mask) | (field << lo)


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

_VOLTAGE_BITS = {
    15: "2.7-2.8",
    16: "2.8-2.9",
    17: "2.9-3.0",
    18: "3.0-3.1",
    19: "3.1-3.2",
    20: "3.2-3.3",
    21: "3.3-3.4",
    22: "3.4-3.5",
    23: "3.5-3.6",
}


@dataclass(frozen=True)
class OCR:
    raw: int
    powered_up: bool  # bit 31: card power-up status (0 = busy)
    ccs: bool | None  # bit 30: Card Capacity Status; only valid when powered_up
    uhs2: bool  # bit 29
    over_2tb: bool  # bit 27 (SDUC)
    s18a: bool  # bit 24: switching to 1.8V accepted
    voltage_windows: tuple[str, ...]

    @property
    def high_capacity(self) -> bool | None:
        return self.ccs

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["raw"] = f"0x{self.raw:08X}"
        return d


def decode_ocr(raw: int) -> OCR:
    if not 0 <= raw <= 0xFFFF_FFFF:
        raise ValueError("OCR must be a 32-bit value")
    powered = bool(raw >> 31 & 1)
    return OCR(
        raw=raw,
        powered_up=powered,
        ccs=bool(raw >> 30 & 1) if powered else None,
        uhs2=bool(raw >> 29 & 1),
        over_2tb=bool(raw >> 27 & 1),
        s18a=bool(raw >> 24 & 1),
        voltage_windows=tuple(v for b, v in _VOLTAGE_BITS.items() if raw >> b & 1),
    )


def encode_ocr(
    *, powered_up: bool, ccs: bool, voltage_mask: int = 0x00FF_8000, s18a: bool = False
) -> int:
    raw = voltage_mask & 0x00FF_8000
    raw |= int(powered_up) << 31
    raw |= int(ccs and powered_up) << 30
    raw |= int(s18a) << 24
    return raw


# ---------------------------------------------------------------------------
# CSD
# ---------------------------------------------------------------------------

_TAAC_UNIT_NS = [1, 10, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000]
_TIME_MULT_X10 = [0, 10, 12, 13, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80]
_RATE_UNIT_KBIT = [100, 1_000, 10_000, 100_000]


@dataclass(frozen=True)
class CSD:
    raw_hex: str
    structure: int
    version: str
    capacity_class: str  # "SDSC", "SDHC/SDXC", "SDUC"
    taac_ns: float | None
    nsac_clocks: int
    tran_speed_kbit: int | None
    ccc: int
    read_bl_len: int
    read_bl_partial: bool
    write_blk_misalign: bool
    read_blk_misalign: bool
    dsr_imp: bool
    c_size: int
    c_size_mult: int | None
    erase_blk_en: bool
    sector_size: int
    wp_grp_size: int
    wp_grp_enable: bool
    r2w_factor: int
    write_bl_len: int
    write_bl_partial: bool
    file_format_grp: int
    copy: bool
    perm_write_protect: bool
    tmp_write_protect: bool
    file_format: int
    crc: int
    crc_valid: bool
    capacity_bytes: int
    warnings: tuple[str, ...]

    @property
    def capacity_sectors(self) -> int:
        return self.capacity_bytes // SECTOR

    @property
    def block_addressed(self) -> bool:
        """True when the card is addressed in 512-byte blocks (CSD v2/v3)."""
        return self.structure in (1, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["capacity_sectors"] = self.capacity_sectors
        d["block_addressed"] = self.block_addressed
        d["ccc"] = f"0x{self.ccc:03X}"
        return d


def _parse_hex_register(text: str, nbytes: int) -> int:
    cleaned = "".join(text.split()).replace(":", "").replace("-", "")
    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]
    if len(cleaned) != nbytes * 2:
        raise ValueError(f"expected {nbytes * 2} hex digits, got {len(cleaned)}")
    return int(cleaned, 16)


def decode_csd(register: int | str | bytes) -> CSD:
    if isinstance(register, str):
        value = _parse_hex_register(register, 16)
    elif isinstance(register, bytes):
        if len(register) != 16:
            raise ValueError("CSD must be 16 bytes")
        value = int.from_bytes(register, "big")
    else:
        value = register
    if not 0 <= value < (1 << 128):
        raise ValueError("CSD must be a 128-bit value")

    warnings: list[str] = []
    structure = _bits(value, 127, 126)
    body = value.to_bytes(16, "big")
    crc = _bits(value, 7, 1)
    crc_valid = crc7(body[:15]) == crc
    if not crc_valid:
        warnings.append("CRC7 mismatch (register may be corrupt or hand-edited)")
    if not value & 1:
        warnings.append("end bit is 0 (should always be 1)")

    taac = _bits(value, 119, 112)
    tran = _bits(value, 103, 96)
    read_bl_len = _bits(value, 83, 80)
    c_size_mult: int | None
    if structure == 0:
        version, cap_class = "1.0", "SDSC"
        c_size = _bits(value, 73, 62)
        c_size_mult = _bits(value, 49, 47)
        if read_bl_len not in (9, 10, 11):
            warnings.append(f"READ_BL_LEN={read_bl_len} outside 9..11 permitted for SDSC")
        capacity = (c_size + 1) * (1 << (c_size_mult + 2)) * (1 << read_bl_len)
        if capacity > 2 * 1024**3:
            warnings.append(
                "capacity above 2 GB on CSD v1.0: non-standard '4 GB SDSC' card; "
                "not a recommended solution (spec section 4.1)"
            )
        taac_ns: float | None = (
            _TAAC_UNIT_NS[taac & 7] * _TIME_MULT_X10[(taac >> 3) & 0xF] / 10
            if (taac >> 3) & 0xF
            else None
        )
    elif structure == 1:
        version, cap_class = "2.0", "SDHC/SDXC"
        c_size = _bits(value, 69, 48)
        c_size_mult = None
        capacity = (c_size + 1) * 512 * 1024
        if read_bl_len != 9:
            warnings.append(f"READ_BL_LEN={read_bl_len}; CSD v2.0 fixes it at 9 (512 bytes)")
        if taac != 0x0E:
            warnings.append(f"TAAC=0x{taac:02X}; CSD v2.0 fixes it at 0x0E")
        taac_ns = None  # fixed value, not used by hosts for v2
    elif structure == 2:
        version, cap_class = "3.0", "SDUC"
        c_size = _bits(value, 75, 48)
        c_size_mult = None
        capacity = (c_size + 1) * 512 * 1024
        taac_ns = None
    else:
        raise ValueError("CSD_STRUCTURE=3 is reserved")

    tran_mult = _TIME_MULT_X10[(tran >> 3) & 0xF]
    tran_unit = tran & 7
    tran_kbit = (
        _RATE_UNIT_KBIT[tran_unit] * tran_mult // 10 if tran_unit < 4 and tran_mult else None
    )
    if tran_kbit is None:
        warnings.append(f"TRAN_SPEED=0x{tran:02X} uses a reserved encoding")

    return CSD(
        raw_hex=f"{value:032X}",
        structure=structure,
        version=version,
        capacity_class=cap_class,
        taac_ns=taac_ns,
        nsac_clocks=_bits(value, 111, 104) * 100,
        tran_speed_kbit=tran_kbit,
        ccc=_bits(value, 95, 84),
        read_bl_len=read_bl_len,
        read_bl_partial=bool(_bits(value, 79, 79)),
        write_blk_misalign=bool(_bits(value, 78, 78)),
        read_blk_misalign=bool(_bits(value, 77, 77)),
        dsr_imp=bool(_bits(value, 76, 76)),
        c_size=c_size,
        c_size_mult=c_size_mult,
        erase_blk_en=bool(_bits(value, 46, 46)),
        sector_size=_bits(value, 45, 39) + 1,
        wp_grp_size=_bits(value, 38, 32) + 1,
        wp_grp_enable=bool(_bits(value, 31, 31)),
        r2w_factor=1 << _bits(value, 28, 26),
        write_bl_len=_bits(value, 25, 22),
        write_bl_partial=bool(_bits(value, 21, 21)),
        file_format_grp=_bits(value, 15, 15),
        copy=bool(_bits(value, 14, 14)),
        perm_write_protect=bool(_bits(value, 13, 13)),
        tmp_write_protect=bool(_bits(value, 12, 12)),
        file_format=_bits(value, 11, 10),
        crc=crc,
        crc_valid=crc_valid,
        capacity_bytes=capacity,
        warnings=tuple(warnings),
    )


def _finish(value: int) -> int:
    body = value.to_bytes(16, "big")[:15]
    value = _set(value, 7, 1, crc7(body))
    return value | 1


def encode_csd_v1(
    *, c_size: int, c_size_mult: int, read_bl_len: int = 9, tran_speed: int = 0x32
) -> int:
    """Build a CSD v1.0 register (for fixtures and the simulator)."""
    v = 0
    v = _set(v, 127, 126, 0)
    v = _set(v, 119, 112, 0x26)  # TAAC 1.5 ms
    v = _set(v, 111, 104, 0x00)
    v = _set(v, 103, 96, tran_speed)
    v = _set(v, 95, 84, 0x5B5)  # CCC classes 0,2,4,5,7,8,10
    v = _set(v, 83, 80, read_bl_len)
    v = _set(v, 73, 62, c_size)
    v = _set(v, 61, 59, 0b110)
    v = _set(v, 58, 56, 0b110)
    v = _set(v, 55, 53, 0b110)
    v = _set(v, 52, 50, 0b110)
    v = _set(v, 49, 47, c_size_mult)
    v = _set(v, 46, 46, 1)
    v = _set(v, 45, 39, 0x7F)
    v = _set(v, 28, 26, 0b100)
    v = _set(v, 25, 22, read_bl_len)
    return _finish(v)


def encode_csd_v2(*, c_size: int, tran_speed: int = 0x32) -> int:
    """Build a CSD v2.0 register (SDHC/SDXC)."""
    v = 0
    v = _set(v, 127, 126, 1)
    v = _set(v, 119, 112, 0x0E)
    v = _set(v, 111, 104, 0x00)
    v = _set(v, 103, 96, tran_speed)
    v = _set(v, 95, 84, 0x5B5)
    v = _set(v, 83, 80, 9)
    v = _set(v, 69, 48, c_size)
    v = _set(v, 46, 46, 1)
    v = _set(v, 45, 39, 0x7F)
    v = _set(v, 28, 26, 0b010)
    v = _set(v, 25, 22, 9)
    return _finish(v)


def csd_v2_c_size_for_capacity(capacity_bytes: int) -> int:
    """C_SIZE for an SDHC/SDXC card of (at least) the given capacity."""
    units = capacity_bytes // (512 * 1024)
    if units < 1:
        raise ValueError("capacity too small for CSD v2.0")
    return units - 1
