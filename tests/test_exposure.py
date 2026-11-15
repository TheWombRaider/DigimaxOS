from fractions import Fraction

import pytest
from digimax.exposure import (
    DEFAULTS,
    Capability,
    Key,
    MModeUI,
    Row,
    Settings,
    ev100,
    format_shutter,
)


def test_ev_reference_points() -> None:
    # f/1, 1 s, ISO 100 is EV 0 by definition; check doubling rules.
    assert ev100(Fraction(1), 1.0, 100) == 0
    assert ev100(Fraction(1, 2), 1.0, 100) == pytest.approx(1)
    assert ev100(Fraction(1), 1.0, 200) == pytest.approx(-1)
    # f/7 vs f/3.5 is exactly two stops
    assert ev100(Fraction(1, 60), 7.0, 100) - ev100(Fraction(1, 60), 3.5, 100) == pytest.approx(2)


def test_matrix_covers_documented_space() -> None:
    rows = Capability().matrix()
    assert {r["iso"] for r in rows} == {100, 200, 400}
    assert {r["aperture"] for r in rows} == {3.5, 7.0}
    assert max(r["shutter_s"] for r in rows) == 8
    assert min(r["shutter_s"] for r in rows) == 0.001
    by_shutter = {r["shutter"]: r for r in rows}
    # EXP-0004: stock Night-mode menu values are observed (not yet timed); fast steps are candidates
    for seen in ('8"', '6"', '4"', '3"', '2"', '1"', "1/2", "1/8"):
        assert by_shutter[seen]["shutter_status"] == "observed"
        assert by_shutter[seen]["stock_user_selectable"] is True
    for cand in ("1/4", "1/15", "1/60", "1/1000"):
        assert by_shutter[cand]["shutter_status"] == "candidate"
    # overall status is the weakest of shutter / aperture / ISO
    assert {r["status"] for r in rows} == {"candidate", "documented"}
    assert {r["stock_mode_needed"] for r in rows if r["shutter_s"] > 2} == {"night"}


def test_format_shutter() -> None:
    assert format_shutter(Fraction(1, 1000)) == "1/1000"
    assert format_shutter(Fraction(8)) == '8"'
    assert format_shutter(Fraction(3)) == '3"'


def _ui() -> MModeUI:
    return MModeUI()


def test_edit_commit_cycle() -> None:
    ui = _ui()
    ui.press(Key.PLUS_MINUS)
    assert ui.editing and ui.row is Row.SHUTTER
    ui.press(Key.RIGHT)  # faster shutter
    ui.press(Key.DOWN)
    ui.press(Key.RIGHT)  # f/3.5 -> f/7
    ui.press(Key.DOWN)
    ui.press(Key.RIGHT)
    ui.press(Key.RIGHT)  # ISO 100 -> 400
    ui.press(Key.PLUS_MINUS)
    assert not ui.editing
    assert ui.committed == Settings(Fraction(1, 125), 7.0, 400)


def test_cancel_reverts_draft() -> None:
    ui = _ui()
    ui.press(Key.PLUS_MINUS)
    ui.press(Key.LEFT)
    ui.press(Key.MENU)
    assert ui.committed == DEFAULTS and not ui.editing and ui.message == "cancelled"


def test_steps_clamp_without_wrapping() -> None:
    ui = _ui()
    ui.press(Key.PLUS_MINUS)
    for _ in range(50):
        ui.press(Key.RIGHT)
    assert ui.draft.shutter == Fraction(1, 1000)
    assert ui.message == "limit reached"
    for _ in range(50):
        ui.press(Key.LEFT)
    assert ui.draft.shutter == Fraction(8)


def test_meter_is_advisory_and_never_changes_settings() -> None:
    ui = _ui()
    before = ui.committed
    for scene in (-5.0, 0.0, 7.0, 15.0, 20.0):
        ui.meter(scene)
        ui.render(scene_ev100=scene)
        ui.press(Key.SHUTTER_FULL)
    assert ui.committed == before
    assert ui.captures == [before] * 5


def test_invalid_combination_is_explained_not_silently_fixed() -> None:
    cap = Capability(forbidden=((Fraction(8), None, 400, "8 s at ISO 400 is not supported"),))
    ui = MModeUI(capability=cap)
    ui.press(Key.PLUS_MINUS)
    for _ in range(20):
        ui.press(Key.LEFT)  # 8 s
    ui.press(Key.DOWN)
    ui.press(Key.DOWN)
    ui.press(Key.RIGHT)
    ui.press(Key.RIGHT)  # ISO 400
    ui.press(Key.PLUS_MINUS)  # try to commit
    assert ui.editing, "editor must stay open"
    assert "not supported" in ui.message
    assert ui.draft == Settings(Fraction(8), 3.5, 400), "user's values must be kept"
    assert ui.committed == DEFAULTS


def test_reset_defaults() -> None:
    ui = _ui()
    ui.press(Key.PLUS_MINUS)
    ui.press(Key.LEFT)
    ui.press(Key.PLUS_MINUS)
    ui.press(Key.RESET)
    assert ui.committed == DEFAULTS


def test_render_mock_contains_fields() -> None:
    ui = _ui()
    ui.press(Key.PLUS_MINUS)
    screen = ui.render(scene_ev100=10)
    assert " M " in screen and "[1/60]" in screen and "F3.5" in screen and "ISO100" in screen
    assert "EV" in screen
