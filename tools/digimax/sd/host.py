"""Reference SD/MMC host initialisation and block transport (native SD bus mode).

This is an executable *specification* of how DigimaxOS firmware should bring
up a card and convert logical sectors to card addresses. It runs against any
object implementing :class:`CardBus` - in practice the simulator in
``sim/digimax_sim``. It is not camera code; the A402's actual host controller
(native SD vs SPI, register map, DMA) is still unknown (see issue tracker).

Sequence implemented (S5, "Card Initialization and Identification Process"):

  CMD0 -> CMD8(0x1AA) -> [CMD55+ACMD41(HCS)]* -> CMD2 -> CMD3 -> CMD9 -> CMD7
          (no CMD8 reply => v1.x card or MMC; ACMD41 rejected => MMC via CMD1)
          -> CMD16(512) for byte-addressed cards only
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .addressing import SECTOR, AddressError, Addressing, Geometry, command_argument
from .registers import CSD, OCR, _bits, decode_csd, decode_ocr

CMD8_CHECK = 0x1AA
DEFAULT_VOLTAGE_WINDOW = 0x00FF_8000  # 2.7-3.6 V
HCS = 1 << 30

# R1 card status bits
OUT_OF_RANGE = 1 << 31
ADDRESS_ERROR = 1 << 30
BLOCK_LEN_ERROR = 1 << 29
WP_VIOLATION = 1 << 26
COM_CRC_ERROR = 1 << 23
ILLEGAL_COMMAND = 1 << 22
CARD_ERROR = 1 << 20
APP_CMD = 1 << 5
R1_ERROR_MASK = (
    OUT_OF_RANGE
    | ADDRESS_ERROR
    | BLOCK_LEN_ERROR
    | WP_VIOLATION
    | COM_CRC_ERROR
    | ILLEGAL_COMMAND
    | CARD_ERROR
)


@dataclass(frozen=True)
class Response:
    status: int = 0  # R1 card status (or 0 for R2/R3)
    value: int | None = None  # R2: 128-bit CID/CSD, R3: OCR, R6: RCA<<16|status, R7: echo
    data: bytes | None = None  # data block for read commands


class CardBus(Protocol):
    def command(self, index: int, argument: int, *, data: bytes | None = None) -> Response | None:
        """Issue one command. ``None`` means no response (timeout / no card)."""
        ...


class CardKind(StrEnum):
    SDSC_V1 = "SDSC (v1.x)"
    SDSC_V2 = "SDSC (v2.0+)"
    SDHC = "SDHC/SDXC"
    MMC = "MMC"


class InitError(RuntimeError):
    pass


@dataclass(frozen=True)
class HostPolicy:
    """Capabilities of the *host* firmware. ``legacy()`` models an SDSC-only host."""

    send_cmd8: bool = True
    request_high_capacity: bool = True
    max_ready_polls: int = 1000
    allow_mmc: bool = True

    @classmethod
    def legacy(cls) -> HostPolicy:
        return cls(send_cmd8=False, request_high_capacity=False)


@dataclass(frozen=True)
class CardInfo:
    kind: CardKind
    rca: int
    ocr: OCR
    csd: CSD | None
    capacity_sectors: int
    geometry: Geometry
    notes: tuple[str, ...]


def _expect(resp: Response | None, what: str) -> Response:
    if resp is None:
        raise InitError(f"no response to {what} (card removed or not powered?)")
    if resp.status & R1_ERROR_MASK:
        raise InitError(f"{what} failed with card status 0x{resp.status:08X}")
    return resp


def _mmc_capacity_bytes(csd_value: int) -> int:
    # MMC CSD shares the SD v1.0 C_SIZE/C_SIZE_MULT/READ_BL_LEN bit positions.
    c_size = _bits(csd_value, 73, 62)
    mult = _bits(csd_value, 49, 47)
    bl = _bits(csd_value, 83, 80)
    return (c_size + 1) * (1 << (mult + 2)) * (1 << bl)


def initialize(bus: CardBus, policy: HostPolicy | None = None) -> CardInfo:
    policy = policy or HostPolicy()
    notes: list[str] = []

    bus.command(0, 0)  # GO_IDLE_STATE: no response expected

    v2 = False
    if policy.send_cmd8:
        r7 = bus.command(8, CMD8_CHECK)
        if r7 is not None and not (r7.status & ILLEGAL_COMMAND):
            if r7.value is None or (r7.value & 0xFFF) != CMD8_CHECK:
                raise InitError("CMD8 echo mismatch: unusable card or unsupported voltage")
            v2 = True
        else:
            notes.append("no valid CMD8 response: v1.x SD card or MMC")

    acmd41_arg = DEFAULT_VOLTAGE_WINDOW | (HCS if (v2 and policy.request_high_capacity) else 0)
    ocr: OCR | None = None
    is_mmc = False
    for _ in range(policy.max_ready_polls):
        r55 = bus.command(55, 0)
        if r55 is None or r55.status & ILLEGAL_COMMAND:
            is_mmc = True
            break
        r3 = bus.command(41, acmd41_arg)
        if r3 is None or r3.value is None:
            is_mmc = True
            break
        candidate = decode_ocr(r3.value)
        if candidate.powered_up:
            ocr = candidate
            break
    else:
        raise InitError(
            "card never left busy state during ACMD41 "
            f"(HCS={'1' if acmd41_arg & HCS else '0'}). A high-capacity card stays busy "
            "forever when the host does not send CMD8/HCS - the classic SDSC-only host failure."
        )

    if is_mmc:
        if not policy.allow_mmc:
            raise InitError("card rejected ACMD41 and MMC support is disabled")
        for _ in range(policy.max_ready_polls):
            r3 = bus.command(1, DEFAULT_VOLTAGE_WINDOW)
            if r3 is None or r3.value is None:
                raise InitError("no response to CMD1: neither SD nor MMC")
            candidate = decode_ocr(r3.value)
            if candidate.powered_up:
                ocr = candidate
                break
        else:
            raise InitError("MMC never left busy state during CMD1")

    assert ocr is not None
    _expect(bus.command(2, 0), "CMD2 (ALL_SEND_CID)")
    if is_mmc:
        rca = 1
        _expect(bus.command(3, rca << 16), "CMD3 (SET_RELATIVE_ADDR)")
    else:
        r6 = _expect(bus.command(3, 0), "CMD3 (SEND_RELATIVE_ADDR)")
        assert r6.value is not None
        rca = r6.value >> 16
    r2 = _expect(bus.command(9, rca << 16), "CMD9 (SEND_CSD)")
    assert r2.value is not None
    _expect(bus.command(7, rca << 16), "CMD7 (SELECT_CARD)")

    csd: CSD | None
    if is_mmc:
        kind = CardKind.MMC
        csd = None
        capacity = _mmc_capacity_bytes(r2.value)
        addressing = Addressing.BYTE
        notes.append("MMC capacity from CSD; >2 GB MMC needs EXT_CSD (not implemented)")
    else:
        csd = decode_csd(r2.value)
        capacity = csd.capacity_bytes
        if ocr.ccs:
            kind = CardKind.SDHC
            addressing = Addressing.BLOCK
            if not csd.block_addressed:
                raise InitError("OCR.CCS=1 but CSD is v1.0: inconsistent card")
        else:
            kind = CardKind.SDSC_V2 if v2 else CardKind.SDSC_V1
            addressing = Addressing.BYTE
            if csd.block_addressed:
                raise InitError("CSD v2.0 reported but OCR.CCS=0: inconsistent card")
        notes.extend(csd.warnings)

    if addressing is Addressing.BYTE:
        _expect(bus.command(16, SECTOR), "CMD16 (SET_BLOCKLEN 512)")

    geometry = Geometry(capacity // SECTOR, addressing)
    return CardInfo(kind, rca, ocr, csd, geometry.capacity_sectors, geometry, tuple(notes))


class BlockTransport:
    """Sector-level read/write over an initialised card. All range checks happen here."""

    def __init__(self, bus: CardBus, info: CardInfo) -> None:
        self.bus = bus
        self.info = info

    def read(self, lba: int) -> bytes:
        arg = command_argument(self.info.geometry, lba)
        resp = _expect(self.bus.command(17, arg), f"CMD17 read LBA {lba}")
        if resp.data is None or len(resp.data) != SECTOR:
            raise InitError(f"short read at LBA {lba}")
        return resp.data

    def write(self, lba: int, data: bytes) -> None:
        if len(data) != SECTOR:
            raise AddressError(f"write must be exactly {SECTOR} bytes")
        arg = command_argument(self.info.geometry, lba)
        _expect(self.bus.command(24, arg, data=data), f"CMD24 write LBA {lba}")
