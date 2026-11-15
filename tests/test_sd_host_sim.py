"""Host init/transport reference model against the simulated card (no hardware claims)."""

import pytest
from digimax.sd.addressing import AddressError, Addressing, pattern_for_sector, verify_sector
from digimax.sd.host import BlockTransport, CardKind, HostPolicy, InitError, initialize
from digimax_sim.sdcard import SimulatedCard

GB = 1000**3
MB = 1000**2


@pytest.mark.parametrize(
    ("kind", "cap", "expected_kind", "addressing"),
    [
        ("sdsc-v1", 512 * MB, CardKind.SDSC_V1, Addressing.BYTE),
        ("sdsc-v2", 1 * GB, CardKind.SDSC_V2, Addressing.BYTE),
        ("sdsc-v2", 2 * GB, CardKind.SDSC_V2, Addressing.BYTE),
        ("sdhc", 4 * GB, CardKind.SDHC, Addressing.BLOCK),
        ("sdhc", 32 * GB, CardKind.SDHC, Addressing.BLOCK),
        ("mmc", 128 * MB, CardKind.MMC, Addressing.BYTE),
    ],
)
def test_modern_host_initialises_every_class(kind, cap, expected_kind, addressing) -> None:
    card = SimulatedCard(kind, cap)
    info = initialize(card)
    assert info.kind is expected_kind
    assert info.geometry.addressing is addressing
    assert info.capacity_sectors == card.media.capacity_sectors
    if addressing is Addressing.BYTE:
        assert (16, 512) in card.log  # CMD16 only for byte-addressed cards
    else:
        assert all(cmd != 16 for cmd, _ in card.log)


def test_legacy_host_cannot_initialise_sdhc() -> None:
    """Models the hypothesis that stock A402 firmware is SDSC-only (unverified, issue SD-02)."""
    card = SimulatedCard("sdhc", 8 * GB)
    with pytest.raises(InitError, match="never left busy"):
        initialize(card, HostPolicy.legacy())


def test_legacy_host_still_handles_sdsc() -> None:
    info = initialize(SimulatedCard("sdsc-v2", 2 * GB), HostPolicy.legacy())
    assert info.kind is CardKind.SDSC_V1  # no CMD8 sent, so host sees it as v1-style
    assert info.geometry.addressing is Addressing.BYTE


def test_removed_card_reports_no_response() -> None:
    card = SimulatedCard("sdhc", 4 * GB)
    card.remove()
    with pytest.raises(InitError):
        initialize(card)


def test_permanently_busy_card_times_out() -> None:
    card = SimulatedCard("sdsc-v2", 1 * GB, busy_polls=10_000)
    with pytest.raises(InitError, match="busy"):
        initialize(card, HostPolicy(max_ready_polls=50))


def test_mmc_disabled_policy() -> None:
    with pytest.raises(InitError, match="MMC"):
        initialize(SimulatedCard("mmc", 64 * MB), HostPolicy(allow_mmc=False))


@pytest.mark.parametrize(("kind", "cap"), [("sdsc-v2", 2 * GB), ("sdhc", 32 * GB)])
def test_full_range_patterns_have_no_aliasing(kind, cap) -> None:
    card = SimulatedCard(kind, cap)
    t = BlockTransport(card, initialize(card))
    n = t.info.capacity_sectors
    probes = [0, 1, n // 2, (4 * 1024**3 // 512) % n, n - 2, n - 1]
    for lba in probes:
        t.write(lba, pattern_for_sector(lba, seed=99))
    for lba in probes:
        assert verify_sector(lba, t.read(lba), 99).ok


def test_out_of_range_is_rejected_before_any_bus_traffic() -> None:
    card = SimulatedCard("sdhc", 4 * GB)
    t = BlockTransport(card, initialize(card))
    before = len(card.log)
    with pytest.raises(AddressError):
        t.read(t.info.capacity_sectors)
    with pytest.raises(AddressError):
        t.write(t.info.capacity_sectors + 10, b"\x00" * 512)
    assert len(card.log) == before


def test_write_protect_surfaces_as_error() -> None:
    card = SimulatedCard("sdsc-v2", 256 * MB, write_protected=True)
    t = BlockTransport(card, initialize(card))
    with pytest.raises(InitError, match="CMD24"):
        t.write(0, b"\x00" * 512)


def test_card_pulled_mid_session() -> None:
    card = SimulatedCard("sdhc", 4 * GB)
    t = BlockTransport(card, initialize(card))
    card.remove()
    with pytest.raises(InitError, match="no response"):
        t.read(0)


def test_unwritten_sectors_read_as_erased() -> None:
    card = SimulatedCard("sdhc", 16 * GB)
    t = BlockTransport(card, initialize(card))
    assert t.read(1_000_000) == b"\xff" * 512
