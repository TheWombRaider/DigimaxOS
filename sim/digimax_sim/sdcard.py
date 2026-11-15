"""A logical SD/MMC card model for exercising host initialisation and transport code."""

from __future__ import annotations

from dataclasses import dataclass, field

from digimax.sd.host import (
    ADDRESS_ERROR,
    APP_CMD,
    ILLEGAL_COMMAND,
    OUT_OF_RANGE,
    WP_VIOLATION,
    Response,
)
from digimax.sd.registers import (
    csd_v2_c_size_for_capacity,
    encode_csd_v1,
    encode_csd_v2,
    encode_ocr,
)

SECTOR = 512


@dataclass
class SparseMedia:
    """Sparse sector store: unwritten sectors read back as 0xFF (erased flash)."""

    capacity_sectors: int
    sectors: dict[int, bytes] = field(default_factory=dict)

    def read(self, lba: int) -> bytes:
        return self.sectors.get(lba, b"\xff" * SECTOR)

    def write(self, lba: int, data: bytes) -> None:
        assert len(data) == SECTOR
        self.sectors[lba] = bytes(data)


def _csd_v1_for(capacity_sectors: int) -> tuple[int, int]:
    """Pick (encoded CSD, exact capacity sectors) for a v1.0 card near the request."""
    total = capacity_sectors * SECTOR
    for read_bl_len in (9, 10, 11):
        for mult in range(7, -1, -1):
            unit = (1 << (mult + 2)) * (1 << read_bl_len)
            c_size = total // unit - 1
            if 0 <= c_size < 4096:
                exact = (c_size + 1) * unit // SECTOR
                return encode_csd_v1(
                    c_size=c_size, c_size_mult=mult, read_bl_len=read_bl_len
                ), exact
    raise ValueError("capacity not representable in CSD v1.0")


class SimulatedCard:
    """Logical card. ``kind`` is one of "sdsc-v1", "sdsc-v2", "sdhc", "mmc"."""

    def __init__(
        self,
        kind: str,
        capacity_bytes: int,
        *,
        busy_polls: int = 3,
        write_protected: bool = False,
    ) -> None:
        if kind not in ("sdsc-v1", "sdsc-v2", "sdhc", "mmc"):
            raise ValueError(kind)
        self.kind = kind
        self.busy_polls = busy_polls
        self.write_protected = write_protected
        self.present = True
        requested = capacity_bytes // SECTOR
        if kind == "sdhc":
            c_size = csd_v2_c_size_for_capacity(capacity_bytes)
            self.csd = encode_csd_v2(c_size=c_size)
            exact = (c_size + 1) * 1024
        else:
            self.csd, exact = _csd_v1_for(requested)
            if kind == "mmc":
                # MMC: CSD_STRUCTURE=2 ("version 1.2"); shares v1 capacity fields.
                self.csd = (self.csd & ~(0b11 << 126)) | (0b10 << 126)
        self.media = SparseMedia(exact)
        self.rca = 0x1234
        self.reset()
        self.log: list[tuple[int, int]] = []

    # -- state ------------------------------------------------------------
    def reset(self) -> None:
        self.state = "idle"
        self.got_cmd8 = False
        self.app = False
        self.polls = 0
        self.selected = False
        self.block_len = SECTOR

    def remove(self) -> None:
        self.present = False

    @property
    def high_capacity(self) -> bool:
        return self.kind == "sdhc"

    def _ocr(self, ready: bool) -> int:
        return encode_ocr(powered_up=ready, ccs=self.high_capacity)

    # -- bus ----------------------------------------------------------------
    def command(self, index: int, argument: int, *, data: bytes | None = None) -> Response | None:
        if not self.present:
            return None
        self.log.append((index, argument))
        app, self.app = self.app, False

        if index == 0:
            self.reset()
            return None
        if self.kind == "mmc":
            return self._mmc(index, argument, data)

        if app and index == 41:
            return self._acmd41(argument)
        if index == 8:
            if self.kind == "sdsc-v1":
                return None  # v1.x cards do not respond to CMD8
            self.got_cmd8 = True
            return Response(value=argument & 0xFFF)
        if index == 55:
            self.app = True
            return Response(status=APP_CMD)
        return self._common(index, argument, data)

    def _acmd41(self, argument: int) -> Response:
        hcs = bool(argument & (1 << 30))
        if self.high_capacity and (not self.got_cmd8 or not hcs):
            # Per S5: a high capacity card never completes initialisation for a
            # host that did not announce HCS (after CMD8).
            return Response(value=self._ocr(False))
        self.polls += 1
        ready = self.polls > self.busy_polls
        if ready:
            self.state = "ready"
        return Response(value=self._ocr(ready))

    def _mmc(self, index: int, argument: int, data: bytes | None) -> Response | None:
        if index in (8, 55, 41):
            return None  # MMC does not implement SD-specific commands
        if index == 1:
            self.polls += 1
            ready = self.polls > self.busy_polls
            if ready:
                self.state = "ready"
            return Response(value=encode_ocr(powered_up=ready, ccs=False))
        if index == 3:
            self.rca = argument >> 16
            self.state = "stby"
            return Response(status=0)
        return self._common(index, argument, data)

    def _common(self, index: int, argument: int, data: bytes | None) -> Response | None:
        if index == 2:
            if self.state != "ready":
                return Response(status=ILLEGAL_COMMAND)
            self.state = "ident"
            return Response(value=0x1D41_4453_4449_4D58_1000_0000_0101_A301)
        if index == 3:
            self.state = "stby"
            return Response(value=(self.rca << 16))
        if index == 9:
            if argument >> 16 != self.rca:
                return None
            return Response(value=self.csd)
        if index == 7:
            self.selected = argument >> 16 == self.rca
            return Response(status=0)
        if index == 16:
            if self.high_capacity:
                return Response(status=0)  # ignored for block-length on SDHC
            self.block_len = argument
            return Response(status=0)
        if index in (17, 24):
            if not self.selected:
                return Response(status=ILLEGAL_COMMAND)
            lba_or_err = self._lba(argument)
            if isinstance(lba_or_err, Response):
                return lba_or_err
            if index == 17:
                return Response(status=0, data=self.media.read(lba_or_err))
            if self.write_protected:
                return Response(status=WP_VIOLATION)
            assert data is not None
            self.media.write(lba_or_err, data)
            return Response(status=0)
        return Response(status=ILLEGAL_COMMAND)

    def _lba(self, argument: int) -> int | Response:
        if self.high_capacity:
            lba = argument
        else:
            if argument % SECTOR:
                return Response(status=ADDRESS_ERROR)
            lba = argument // SECTOR
        if lba >= self.media.capacity_sectors:
            return Response(status=OUT_OF_RANGE)
        return lba
