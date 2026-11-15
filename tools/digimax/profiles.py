"""Load device profiles from ``profiles/<id>/profile.toml``."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any


def profiles_dir() -> Path:
    env = os.environ.get("DIGIMAX_PROFILES")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "profiles"


def load_profile(profile_id: str) -> dict[str, Any]:
    if not profile_id.isalnum():
        raise ValueError(f"invalid profile id {profile_id!r}")
    path = profiles_dir() / profile_id / "profile.toml"
    if not path.is_file():
        raise FileNotFoundError(f"no profile {profile_id!r} at {path}")
    with path.open("rb") as f:
        return tomllib.load(f)


def all_profiles() -> list[dict[str, Any]]:
    d = profiles_dir()
    if not d.is_dir():
        return []
    return [load_profile(p.name) for p in sorted(d.iterdir()) if (p / "profile.toml").is_file()]


def match_usb(vendor_id: int, product_id: int) -> list[dict[str, Any]]:
    """Return profiles whose *verified* USB identity matches. Documented-only does not match."""
    out = []
    for prof in all_profiles():
        for mode, ident in prof.get("usb", {}).items():
            if (
                ident.get("status") == "verified"
                and ident.get("vendor_id") == vendor_id
                and ident.get("product_id") == product_id
            ):
                out.append({"profile": prof["id"], "name": prof["name"], "usb_mode": mode})
    return out
