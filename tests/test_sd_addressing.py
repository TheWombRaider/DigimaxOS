import pytest
from digimax.sd.addressing import (
    SECTOR,
    AddressError,
    Addressing,
    Geometry,
    boundary_probe_lbas,
    command_argument,
    legacy_wrapping_argument,
    pattern_for_sector,
    verify_sector,
)
from hypothesis import given
from hypothesis import strategies as st

GB = 1000**3
SDHC_32G = Geometry(62_333_952, Addressing.BLOCK)  # typical 32 GB card sector count
SDSC_2G = Geometry(3_862_528, Addressing.BYTE)


def test_byte_addressing_multiplies() -> None:
    assert command_argument(SDSC_2G, 0) == 0
    assert command_argument(SDSC_2G, 1) == 512
    assert command_argument(SDSC_2G, SDSC_2G.capacity_sectors - 1) == (3_862_528 - 1) * 512


def test_block_addressing_is_identity() -> None:
    assert command_argument(SDHC_32G, 12_345_678) == 12_345_678


def test_last_sector_ok_and_one_past_rejected() -> None:
    last = SDHC_32G.capacity_sectors - 1
    assert command_argument(SDHC_32G, last) == last
    with pytest.raises(AddressError):
        command_argument(SDHC_32G, last + 1)
    with pytest.raises(AddressError):
        command_argument(SDHC_32G, last, count=2)


def test_negative_and_zero_count_rejected() -> None:
    with pytest.raises(AddressError):
        command_argument(SDHC_32G, -1)
    with pytest.raises(AddressError):
        command_argument(SDHC_32G, 0, count=0)


def test_byte_addressed_geometry_above_4gib_impossible() -> None:
    with pytest.raises(ValueError):
        Geometry(8 * 1024**3 // SECTOR, Addressing.BYTE)


def test_legacy_wrap_demonstrates_aliasing() -> None:
    """Why an SDSC-only transport must never be pointed at an SDHC card.

    At 4 GiB a 32-bit byte address wraps to 0: a write to LBA 8388608 would land on
    the MBR. Our transport rejects instead (see test_block_addressing_is_identity).
    """
    lba = 4 * 1024**3 // SECTOR
    assert legacy_wrapping_argument(lba) == 0
    assert legacy_wrapping_argument(lba + 1) == 512


@given(st.integers(0, SDHC_32G.capacity_sectors - 1))
def test_block_property(lba: int) -> None:
    assert command_argument(SDHC_32G, lba) == lba


@given(st.integers(0, SDSC_2G.capacity_sectors - 1))
def test_byte_property_never_exceeds_u32(lba: int) -> None:
    arg = command_argument(SDSC_2G, lba)
    assert arg == lba * 512 <= 0xFFFF_FFFF


# ------------------------------------------------------------- patterns
def test_pattern_roundtrip() -> None:
    p = pattern_for_sector(123, seed=7)
    assert len(p) == SECTOR
    assert verify_sector(123, p, 7).ok


def test_pattern_detects_aliasing() -> None:
    p = pattern_for_sector(0, seed=7)
    r = verify_sector(8_388_608, p, 7)
    assert not r.ok and r.embedded_lba == 0 and "ALIASING" in r.reason


def test_pattern_detects_corruption_erased_and_stale_seed() -> None:
    p = bytearray(pattern_for_sector(5, seed=1))
    p[100] ^= 1
    assert "corrupted" in verify_sector(5, bytes(p), 1).reason
    assert "0xFF" in verify_sector(5, b"\xff" * SECTOR, 1).reason
    assert "zeros" in verify_sector(5, b"\x00" * SECTOR, 1).reason
    assert "seed" in verify_sector(5, pattern_for_sector(5, 2), 1).reason


@given(st.integers(0, 2**40), st.integers(0, 2**40))
def test_patterns_unique_per_address(a: int, b: int) -> None:
    if a != b:
        assert pattern_for_sector(a, 1) != pattern_for_sector(b, 1)


def test_boundary_probes_cover_edges() -> None:
    n = SDHC_32G.capacity_sectors
    lbas = boundary_probe_lbas(n)
    assert lbas[0] == 0 and lbas[-1] == n - 1
    assert 4 * 1024**3 // SECTOR in lbas  # 4 GiB wrap point
    assert 2 * 1024**3 // SECTOR in lbas
    assert all(0 <= x < n for x in lbas)
    assert lbas == sorted(set(lbas))
