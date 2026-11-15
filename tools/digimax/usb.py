"""Read-only USB discovery.

Linux: reads descriptor attributes from sysfs (no libusb, no control transfers,
no vendor requests - spec section 6 forbids blind vendor-request fuzzing).
Other hosts: import the JSON written by ``scripts/windows/Get-DigimaxInfo.ps1``.

Serial numbers are redacted by default because they identify a specific unit.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .profiles import match_usb

SYSFS_USB = Path("/sys/bus/usb/devices")
INTERESTING_VENDORS = {0x0839: "Samsung Techwin", 0x04FC: "Sunplus"}


@dataclass
class UsbDevice:
    source: str
    bus_path: str
    vendor_id: int
    product_id: int
    bcd_device: int | None
    manufacturer: str | None
    product: str | None
    serial: str | None
    speed_mbps: str | None
    interfaces: list[dict[str, int]] = field(default_factory=list)
    block_devices: list[str] = field(default_factory=list)
    profile_matches: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, show_serial: bool = False) -> dict[str, Any]:
        d = asdict(self)
        d["vendor_id"] = f"{self.vendor_id:04x}"
        d["product_id"] = f"{self.product_id:04x}"
        d["bcd_device"] = None if self.bcd_device is None else f"{self.bcd_device:04x}"
        if not show_serial and self.serial:
            d["serial"] = "<redacted>"
        return d


def _read(p: Path) -> str | None:
    try:
        return p.read_text().strip()
    except OSError:
        return None


def _hex(p: Path) -> int | None:
    v = _read(p)
    try:
        return int(v, 16) if v else None
    except ValueError:
        return None


def scan_sysfs(root: Path = SYSFS_USB, *, all_devices: bool = False) -> list[UsbDevice]:
    found: list[UsbDevice] = []
    if not root.is_dir():
        return found
    for dev in sorted(root.iterdir()):
        vid, pid = _hex(dev / "idVendor"), _hex(dev / "idProduct")
        if vid is None or pid is None:
            continue
        matches = match_usb(vid, pid)
        if not all_devices and not matches and vid not in INTERESTING_VENDORS:
            continue
        ifaces: list[dict[str, int]] = []
        blocks: list[str] = []
        for sub in sorted(dev.glob(f"{dev.name}:*")):
            cls = _hex(sub / "bInterfaceClass")
            if cls is not None:
                ifaces.append(
                    {
                        "class": cls,
                        "subclass": _hex(sub / "bInterfaceSubClass") or 0,
                        "protocol": _hex(sub / "bInterfaceProtocol") or 0,
                    }
                )
            blocks.extend(sorted(b.name for b in sub.glob("host*/target*/*/block/*")))
        found.append(
            UsbDevice(
                source="linux-sysfs",
                bus_path=dev.name,
                vendor_id=vid,
                product_id=pid,
                bcd_device=_hex(dev / "bcdDevice"),
                manufacturer=_read(dev / "manufacturer"),
                product=_read(dev / "product"),
                serial=_read(dev / "serial"),
                speed_mbps=_read(dev / "speed"),
                interfaces=ifaces,
                block_devices=blocks,
                profile_matches=matches,
            )
        )
    return found


def import_windows_report(path: str | Path) -> list[UsbDevice]:
    """Parse the JSON produced by scripts/windows/Get-DigimaxInfo.ps1."""
    raw = Path(path).read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    out = []
    for d in data.get("devices", []):
        vid, pid = int(d["vendor_id"], 16), int(d["product_id"], 16)
        out.append(
            UsbDevice(
                source="windows-pnp-import",
                bus_path=d.get("location", ""),
                vendor_id=vid,
                product_id=pid,
                bcd_device=int(d["bcd_device"], 16) if d.get("bcd_device") else None,
                manufacturer=None,
                product=d.get("bus_reported_description"),
                serial=None,
                speed_mbps=None,
                interfaces=[
                    {"class": c["class"], "subclass": c["subclass"], "protocol": c["protocol"]}
                    for c in d.get("interfaces", [])
                ],
                block_devices=[
                    f"disk {x['number']} ({x['size']} bytes, {x['partition_style']})"
                    for x in d.get("disks", [])
                ],
                profile_matches=match_usb(vid, pid),
            )
        )
    return out
