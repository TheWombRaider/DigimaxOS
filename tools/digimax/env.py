"""``digimax env check``: inventory the host without changing it."""

from __future__ import annotations

import os
import platform
import shutil
import stat
from pathlib import Path
from typing import Any

OPTIONAL_TOOLS = {
    "lsusb": "USB enumeration (usbutils)",
    "udevadm": "device properties",
    "binwalk": "firmware container carving (optional)",
    "analyzeHeadless": "Ghidra headless analysis (optional)",
    "objdump": "binutils disassembly (optional)",
    "strings": "binutils strings (digimax has a built-in equivalent)",
    "7z": "archive inspection of OEM packages (optional)",
    "exiftool": "EXIF cross-check (optional)",
    "fsck.fat": "independent FAT verification (dosfstools)",
    "mkfs.fat": "test-fixture cross-validation only (never run on real media)",
    "gh": "GitHub CLI",
    "git": "version control",
}


def private_workspace() -> Path:
    return Path(os.environ.get("DIGIMAX_PRIVATE", Path.home() / ".local/share/digimaxos-private"))


def check() -> dict[str, Any]:
    ws = private_workspace()
    ws_info: dict[str, Any] = {"path": str(ws), "exists": ws.is_dir()}
    if ws.is_dir():
        mode = stat.S_IMODE(ws.stat().st_mode)
        ws_info["mode"] = oct(mode)
        ws_info["private"] = mode & 0o077 == 0
    problems = []
    if ws_info.get("exists") and not ws_info.get("private"):
        problems.append(f"private workspace {ws} is group/world accessible; run chmod 700")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "usb_sysfs": Path("/sys/bus/usb/devices").is_dir(),
        "tools": {
            name: {"found": shutil.which(name) is not None, "purpose": why}
            for name, why in OPTIONAL_TOOLS.items()
        },
        "private_workspace": ws_info,
        "problems": problems,
        "ok": not problems,
    }
