"""CRC and register test vectors (synthetic unless stated; see docs/evidence/sources.yaml S5)."""

import pytest
from digimax.sd.crc import command_frame, crc7, crc16_ccitt
from digimax.sd.registers import (
    csd_v2_c_size_for_capacity,
    decode_csd,
    decode_ocr,
    encode_csd_v1,
    encode_csd_v2,
    encode_ocr,
)
from hypothesis import given
from hypothesis import strategies as st

# Command tokens whose CRC bytes are widely documented (SPI-mode bring-up uses them verbatim).
KNOWN_FRAMES = [
    (0, 0x0000_0000, "400000000095"),  # CMD0 GO_IDLE_STATE
    (8, 0x0000_01AA, "48000001aa87"),  # CMD8 SEND_IF_COND, 2.7-3.6 V, check pattern 0xAA
    (55, 0x0000_0000, "770000000065"),  # CMD55 APP_CMD
    (41, 0x4000_0000, "694000000077"),  # ACMD41 with HCS
    (58, 0x0000_0000, "7a00000000fd"),  # CMD58 READ_OCR
    (17, 0x0000_0000, "510000000055"),  # CMD17 READ_SINGLE_BLOCK at 0
]


@pytest.mark.parametrize(("index", "arg", "expected"), KNOWN_FRAMES)
def test_known_command_frames(index: int, arg: int, expected: str) -> None:
    assert command_frame(index, arg).hex() == expected


def test_crc16_of_erased_block() -> None:
    # The SD physical layer spec's CRC16 example: 512 bytes of 0xFF -> 0x7FA1.
    assert crc16_ccitt(b"\xff" * 512) == 0x7FA1


def test_command_frame_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        command_frame(64, 0)
    with pytest.raises(ValueError):
        command_frame(17, 1 << 32)


@given(st.integers(0, 63), st.integers(0, 0xFFFF_FFFF))
def test_frame_structure(index: int, arg: int) -> None:
    f = command_frame(index, arg)
    assert len(f) == 6
    assert f[0] >> 6 == 0b01 and f[0] & 0x3F == index
    assert int.from_bytes(f[1:5], "big") == arg
    assert f[5] & 1 == 1
    assert f[5] >> 1 == crc7(f[:5])


# --------------------------------------------------------------------- OCR
def test_ocr_busy_has_no_ccs() -> None:
    o = decode_ocr(0x40FF_8000)  # CCS bit set but still busy: CCS is not valid yet
    assert not o.powered_up and o.ccs is None


def test_ocr_sdhc_ready() -> None:
    o = decode_ocr(0xC0FF_8000)
    assert o.powered_up and o.ccs is True
    assert o.voltage_windows[0] == "2.7-2.8" and o.voltage_windows[-1] == "3.5-3.6"


def test_ocr_roundtrip() -> None:
    assert decode_ocr(encode_ocr(powered_up=True, ccs=False)).ccs is False
    assert decode_ocr(encode_ocr(powered_up=True, ccs=True)).ccs is True


# --------------------------------------------------------------------- CSD
def test_csd_v1_2gb_card() -> None:
    # 2 GB SDSC typically uses READ_BL_LEN=10 (1024-byte blocks) and C_SIZE_MULT=7.
    raw = encode_csd_v1(c_size=3771, c_size_mult=7, read_bl_len=10)
    c = decode_csd(raw)
    assert c.version == "1.0" and c.capacity_class == "SDSC"
    assert c.capacity_bytes == 3772 * 512 * 1024
    assert not c.block_addressed
    assert c.crc_valid and not c.warnings
    assert c.tran_speed_kbit == 25_000


def test_csd_v1_512mb_card() -> None:
    raw = encode_csd_v1(c_size=3847, c_size_mult=7, read_bl_len=9)
    c = decode_csd(raw)
    assert c.capacity_bytes == 3848 * 512 * 512  # 1,008,730,112 / 2


def test_csd_v1_4gb_nonstandard_is_flagged() -> None:
    c = decode_csd(encode_csd_v1(c_size=4095, c_size_mult=7, read_bl_len=11))
    assert c.capacity_bytes == 4 * 1024**3
    assert any("non-standard" in w for w in c.warnings)


@pytest.mark.parametrize("gb", [4, 8, 16, 32])
def test_csd_v2_sdhc_capacities(gb: int) -> None:
    cap = gb * 1000**3
    c = decode_csd(encode_csd_v2(c_size=csd_v2_c_size_for_capacity(cap)))
    assert c.version == "2.0" and c.block_addressed
    assert cap - 512 * 1024 < c.capacity_bytes <= cap
    assert c.crc_valid and not c.warnings


def test_csd_frequently_published_sdhc_example() -> None:
    # A CSD of this shape (8 GB-class SDHC) circulates widely in embedded forums and driver
    # docs; its provenance is not authoritative, so we assert only internally checkable fields.
    c = decode_csd("400E00325B5900003B377F800A4040AF")
    assert c.structure == 1
    assert c.c_size == 0x3B37
    assert c.capacity_bytes == (0x3B37 + 1) * 512 * 1024
    assert c.read_bl_len == 9 and c.tran_speed_kbit == 25_000


def test_csd_crc_mismatch_warns() -> None:
    raw = encode_csd_v2(c_size=15159) ^ (1 << 2)  # flip a CRC bit
    assert not decode_csd(raw).crc_valid


def test_csd_reserved_structure_rejected() -> None:
    with pytest.raises(ValueError):
        decode_csd((3 << 126) | 1)


def test_csd_parses_hex_with_separators() -> None:
    raw = encode_csd_v2(c_size=100)
    h = f"{raw:032x}"
    spaced = " ".join(h[i : i + 2] for i in range(0, 32, 2))
    assert decode_csd(spaced).c_size == 100


@given(st.integers(0, (1 << 22) - 1))
def test_csd_v2_c_size_roundtrip(c_size: int) -> None:
    assert decode_csd(encode_csd_v2(c_size=c_size)).c_size == c_size


@given(st.integers(0, 4095), st.integers(0, 7), st.sampled_from([9, 10, 11]))
def test_csd_v1_capacity_formula(c_size: int, mult: int, bl: int) -> None:
    c = decode_csd(encode_csd_v1(c_size=c_size, c_size_mult=mult, read_bl_len=bl))
    assert c.capacity_bytes == (c_size + 1) * 2 ** (mult + 2) * 2**bl
