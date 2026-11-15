"""Exposure model and the host-side mock of the proposed native ``M`` mode (EXP-01).

Nothing here talks to a camera. It encodes:

* the documented exposure capability of the A402 (S1 p.85) with an explicit
  status on every value (documented / candidate / verified), and
* the navigation state machine proposed in docs/architecture/exposure.md, so
  the UI can be reviewed and tested before any firmware work (spec 5.2).

Shutter steps: the manuals give only the 8 s to 1/1000 s range. The stock
Night-mode menu (EXP-0004) offers AUTO plus 8, 6, 4, 3, 2, 1, 1/2, 1/4 and 1/8 s.
Those values are OBSERVED, meaning they are
selectable in the stock UI, but their timing has not been measured yet. Faster
steps appear only in the specification range (presumably reached by
auto-exposure) and remain CANDIDATES until measured
(docs/test-plans/exposure-baseline.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import StrEnum
from fractions import Fraction

# Shutter steps (seconds), slowest -> fastest, within 8 s .. 1/1000 s.
CANDIDATE_SHUTTERS: tuple[Fraction, ...] = tuple(
    Fraction(x)
    for x in (
        8, 6, 4, 3, 2, 1, "1/2", "1/4", "1/8",
        "1/15", "1/30", "1/60", "1/125", "1/250", "1/500", "1/1000",
    )
)  # fmt: skip
# Values the owner saw in the stock Night-mode +/- menu (EXP-0004). The menu also offers AUTO.
NIGHT_MODE_OBSERVED: frozenset[Fraction] = frozenset(
    Fraction(x) for x in (8, 6, 4, 3, 2, 1, "1/2", "1/4", "1/8")
)
DOCUMENTED_APERTURES: tuple[float, ...] = (3.5, 7.0)
DOCUMENTED_ISOS: tuple[int, ...] = (100, 200, 400)

NORMAL_SLOWEST = Fraction(2)  # outside Night mode (S1 p.85)
NIGHT_SLOWEST = Fraction(8)
FASTEST = Fraction(1, 1000)


class Status(StrEnum):
    CANDIDATE = "candidate"  # plausible, not documented or measured
    DOCUMENTED = "documented"  # stated by an OEM document
    OBSERVED = "observed"  # seen in the stock UI on the reference unit, not yet measured
    VERIFIED = "verified"  # measured on hardware, experiment ID recorded


_ORDER = [Status.CANDIDATE, Status.DOCUMENTED, Status.OBSERVED, Status.VERIFIED]


def _weakest(*statuses: Status) -> Status:
    return min(statuses, key=_ORDER.index)


def format_shutter(t: Fraction) -> str:
    if t >= 1:
        return f'{float(t):g}"'
    return f"1/{round(1 / t)}"


def ev100(shutter: Fraction, aperture: float, iso: int) -> float:
    """Exposure value normalised to ISO 100: log2(N^2 / t) - log2(ISO / 100)."""
    return math.log2(aperture**2 / float(shutter)) - math.log2(iso / 100)


@dataclass(frozen=True)
class Capability:
    shutters: tuple[Fraction, ...] = CANDIDATE_SHUTTERS
    shutter_status: Status = Status.CANDIDATE
    observed_shutters: frozenset[Fraction] = NIGHT_MODE_OBSERVED
    apertures: tuple[float, ...] = DOCUMENTED_APERTURES
    aperture_status: Status = Status.DOCUMENTED
    isos: tuple[int, ...] = DOCUMENTED_ISOS
    iso_status: Status = Status.DOCUMENTED
    # Combinations proven impossible on hardware, with the reason to display.
    forbidden: tuple[tuple[Fraction | None, float | None, int | None, str], ...] = ()

    def validate(self, s: Settings) -> list[str]:
        problems = []
        if s.shutter not in self.shutters:
            problems.append(f"shutter {format_shutter(s.shutter)} is not a supported step")
        if s.aperture not in self.apertures:
            problems.append(f"f/{s.aperture:g} is not an available aperture")
        if s.iso not in self.isos:
            problems.append(f"ISO {s.iso} is not available")
        for fs, fa, fi, why in self.forbidden:
            if (
                (fs is None or fs == s.shutter)
                and (fa is None or fa == s.aperture)
                and (fi is None or fi == s.iso)
            ):
                problems.append(why)
        return problems

    def matrix(self) -> list[dict[str, object]]:
        rows = []
        for t in self.shutters:
            for n in self.apertures:
                for iso in self.isos:
                    s = Settings(t, n, iso)
                    t_status = (
                        Status.OBSERVED if t in self.observed_shutters else self.shutter_status
                    )
                    status = _weakest(t_status, self.aperture_status, self.iso_status)
                    rows.append(
                        {
                            "shutter": format_shutter(t),
                            "shutter_s": float(t),
                            "aperture": n,
                            "iso": iso,
                            "ev100": round(ev100(t, n, iso), 2),
                            "stock_mode_needed": "night" if t > NORMAL_SLOWEST else "any",
                            "stock_user_selectable": t in self.observed_shutters,
                            "shutter_status": t_status.value,
                            "status": status.value,
                            "problems": self.validate(s),
                        }
                    )
        return rows


@dataclass(frozen=True)
class Settings:
    shutter: Fraction = Fraction(1, 60)
    aperture: float = 3.5
    iso: int = 100


DEFAULTS = Settings()


class Row(StrEnum):
    SHUTTER = "shutter"
    APERTURE = "aperture"
    ISO = "iso"


ROWS = (Row.SHUTTER, Row.APERTURE, Row.ISO)


class Key(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    PLUS_MINUS = "plusminus"  # opens / commits the exposure editor (stock Night-mode idiom)
    MENU = "menu"  # cancels editing
    OK = "ok"
    RESET = "reset"  # proposed "reset defaults" command (long-press OK, TBD)
    SHUTTER_HALF = "half"
    SHUTTER_FULL = "full"


@dataclass
class MModeUI:
    """State machine for the proposed M mode overlay.

    Invariant (EXP-01): the camera never changes a user-selected value on its own.
    The meter is advisory only; out-of-range metering changes the indicator, not
    the settings.
    """

    capability: Capability = field(default_factory=Capability)
    committed: Settings = DEFAULTS
    editing: bool = False
    draft: Settings = DEFAULTS
    row: Row = Row.SHUTTER
    message: str = ""
    captures: list[Settings] = field(default_factory=list)

    def press(self, key: Key) -> None:
        self.message = ""
        if key is Key.PLUS_MINUS:
            if self.editing:
                problems = self.capability.validate(self.draft)
                if problems:
                    self.message = "; ".join(problems)
                    return  # stay in the editor, keep the user's values, explain why
                self.committed = self.draft
                self.editing = False
            else:
                self.draft = self.committed
                self.editing = True
            return
        if key is Key.MENU and self.editing:
            self.draft = self.committed
            self.editing = False
            self.message = "cancelled"
            return
        if key is Key.RESET:
            self.committed = self.draft = DEFAULTS
            self.editing = False
            self.message = "defaults restored"
            return
        if self.editing:
            if key in (Key.UP, Key.DOWN):
                i = ROWS.index(self.row) + (1 if key is Key.DOWN else -1)
                self.row = ROWS[i % len(ROWS)]
            elif key in (Key.LEFT, Key.RIGHT):
                self.draft = self._step(self.draft, self.row, -1 if key is Key.LEFT else 1)
            return
        if key is Key.SHUTTER_FULL:
            problems = self.capability.validate(self.committed)
            if problems:
                self.message = "cannot capture: " + "; ".join(problems)
                return
            self.captures.append(self.committed)

    def _step(self, s: Settings, row: Row, direction: int) -> Settings:
        """Move one step; clamp at the ends (no wrap, so 8" never jumps to 1/1000)."""
        if row is Row.SHUTTER:
            seq: tuple[object, ...] = self.capability.shutters
            cur: object = s.shutter
        elif row is Row.APERTURE:
            seq, cur = self.capability.apertures, s.aperture
        else:
            seq, cur = self.capability.isos, s.iso
        # direction +1 means "less exposure" for shutter/aperture, "more gain" for ISO
        i = seq.index(cur) if cur in seq else 0
        j = min(max(i + direction, 0), len(seq) - 1)
        if j == i:
            self.message = "limit reached"
        val = seq[j]
        if row is Row.SHUTTER:
            assert isinstance(val, Fraction)
            return replace(s, shutter=val)
        if row is Row.APERTURE:
            assert isinstance(val, float)
            return replace(s, aperture=val)
        assert isinstance(val, int)
        return replace(s, iso=val)

    def meter(self, scene_ev100: float) -> float:
        """Advisory exposure-index offset in EV: positive = overexposed vs meter."""
        s = self.draft if self.editing else self.committed
        return round(scene_ev100 - ev100(s.shutter, s.aperture, s.iso), 2)

    def render(
        self, *, shots_left: str = "----", battery: str = "[|||]", scene_ev100: float | None = None
    ) -> str:
        """ASCII mock at roughly the stock LCD layout. Not pixel-accurate."""
        s = self.draft if self.editing else self.committed
        cells = {
            Row.SHUTTER: format_shutter(s.shutter),
            Row.APERTURE: f"F{s.aperture:g}",
            Row.ISO: f"ISO{s.iso}",
        }
        parts = []
        for r in ROWS:
            text = cells[r]
            parts.append(f"[{text}]" if self.editing and r is self.row else f" {text} ")
        meter = ""
        if scene_ev100 is not None:
            off = self.meter(scene_ev100)
            ticks = max(-2, min(2, round(off)))
            scale = list("-2.-1.0.+1.+2")
            meter = " meter " + "".join(scale) + f" ({off:+.1f} EV)"
            pos = {-2: 0, -1: 3, 0: 6, 1: 8, 2: 11}[ticks]
            meter += "\n" + " " * (7 + pos) + "^"
        top = f" M   {shots_left:>5}   {battery}"
        bottom = "".join(parts)
        lines = [top, "", bottom]
        if meter:
            lines.append(meter)
        if self.message:
            lines.append(f" ! {self.message}")
        width = max(len(line) for line in lines)
        border = "+" + "-" * (width + 2) + "+"
        return "\n".join([border, *[f"| {line.ljust(width)} |" for line in lines], border])
