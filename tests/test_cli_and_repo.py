import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from digimax import usb
from digimax.cli import EXIT_OK, EXIT_UNSUPPORTED, EXIT_USAGE, main
from digimax.profiles import load_profile, match_usb

ROOT = Path(__file__).resolve().parents[1]


def run(capsys, *argv: str) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_version_and_frame(capsys) -> None:
    code, out = run(capsys, "sd", "frame", "8", "0x1AA")
    assert code == EXIT_OK and out.strip() == "48 00 00 01 aa 87"


@pytest.mark.parametrize("argv", [["patch", "plan"], ["patch", "build", "x", "a402"], ["capture"]])
def test_unsupported_commands_exit_3(capsys, argv) -> None:
    code, out = run(capsys, "--json", *argv)
    assert code == EXIT_UNSUPPORTED
    assert json.loads(out)["supported"] is False


def test_card_check_refuses_device(capsys) -> None:
    code, _ = run(capsys, "card", "check", "/dev/null")
    assert code == EXIT_USAGE


def test_pattern_make_and_verify(tmp_path: Path, capsys) -> None:
    img = tmp_path / "p.img"
    assert run(capsys, "card", "make-pattern", str(img), "--sectors", "4096", "--seed", "5")[0] == 0
    code, out = run(capsys, "--json", "card", "verify-pattern", str(img), "--seed", "5", "--full")
    assert code == 0 and json.loads(out)["checked"] == 4096
    # simulate aliasing: copy sector 0 over sector 2048
    data = bytearray(img.read_bytes())
    data[2048 * 512 : 2049 * 512] = data[0:512]
    img.write_bytes(bytes(data))
    code, out = run(capsys, "--json", "card", "verify-pattern", str(img), "--seed", "5")
    res = json.loads(out)
    assert code == 1 and res["coverage"] == "boundary-sample"
    assert any("ALIASING" in f["reason"] for f in res["failures"])
    # refuses to overwrite
    assert run(capsys, "card", "make-pattern", str(img), "--sectors", "1")[0] == EXIT_USAGE


def test_sd_address_rejects_out_of_range(capsys) -> None:
    code, out = run(
        capsys,
        "--json",
        "sd",
        "address",
        "--capacity-sectors",
        "1000",
        "--addressing",
        "block",
        "1000",
    )
    assert code == 1 and json.loads(out)["ok"] is False


def test_exposure_commands(capsys) -> None:
    code, out = run(capsys, "--json", "exposure", "table")
    assert code == 0 and len(json.loads(out)) == 16 * 2 * 3
    code, out = run(capsys, "exposure", "mock", "plusminus", "right", "plusminus")
    assert code == 0 and "1/125" in out


def test_env_check_json(capsys) -> None:
    _code, out = run(capsys, "--json", "env", "check")
    assert "python" in json.loads(out)


def test_inspect_profile(capsys) -> None:
    _code, out = run(capsys, "--json", "inspect")
    assert json.loads(out)["usb"]["mass_storage"]["vendor_id"] == 0x0839


# ---------------------------------------------------------- profiles & discovery
def test_profile_match_only_verified() -> None:
    assert match_usb(0x0839, 0x003C)[0]["profile"] == "a402"
    assert match_usb(0x0839, 0x0005) == []
    prof = load_profile("a402")
    assert prof["soc"]["isa"] == "unknown"  # must not be asserted until proven
    with pytest.raises(ValueError):
        load_profile("../etc")


def _fake_sysfs(root: Path) -> None:
    dev = root / "1-2"
    dev.mkdir(parents=True)
    for k, v in {
        "idVendor": "0839",
        "idProduct": "003c",
        "bcdDevice": "0100",
        "product": "DIGITAL CAMERA",
        "serial": "SECRET123",
        "speed": "12",
    }.items():
        (dev / k).write_text(v + "\n")
    iface = dev / "1-2:1.0"
    iface.mkdir()
    for k, v in {
        "bInterfaceClass": "08",
        "bInterfaceSubClass": "06",
        "bInterfaceProtocol": "50",
    }.items():
        (iface / k).write_text(v + "\n")
    (iface / "host3/target3:0:0/3:0:0:0/block/sdz").mkdir(parents=True)
    other = root / "1-3"
    other.mkdir()
    (other / "idVendor").write_text("1d6b\n")
    (other / "idProduct").write_text("0002\n")


def test_sysfs_discovery(tmp_path: Path) -> None:
    _fake_sysfs(tmp_path)
    devs = usb.scan_sysfs(tmp_path)
    assert len(devs) == 1
    d = devs[0].to_dict()
    assert d["vendor_id"] == "0839" and d["serial"] == "<redacted>"
    assert devs[0].interfaces == [{"class": 8, "subclass": 6, "protocol": 0x50}]
    assert devs[0].block_devices == ["sdz"]
    assert devs[0].profile_matches[0]["profile"] == "a402"
    assert len(usb.scan_sysfs(tmp_path, all_devices=True)) == 2


def test_windows_import(tmp_path: Path) -> None:
    report = {
        "devices": [
            {
                "vendor_id": "0839",
                "product_id": "003C",
                "bcd_device": "0100",
                "bus_reported_description": "DIGITAL CAMERA",
                "interfaces": [{"class": 8, "subclass": 6, "protocol": 80}],
                "disks": [{"number": 1, "size": 504365056, "partition_style": "MBR"}],
            }
        ]
    }
    p = tmp_path / "r.json"
    p.write_text("﻿" + json.dumps(report), encoding="utf-8")
    devs = usb.import_windows_report(p)
    assert devs[0].profile_matches and devs[0].bcd_device == 0x0100


# ------------------------------------------------------------- repository policy
def test_sources_registry_schema() -> None:
    data = yaml.safe_load((ROOT / "docs/evidence/sources.yaml").read_text())
    ids = [s["id"] for s in data["sources"]]
    assert len(ids) == len(set(ids))
    for s in data["sources"]:
        assert {"id", "title", "kind", "retrieved", "redistributable", "notes"} <= set(s), s["id"]
        assert s["redistributable"] in (True, False, "unknown")
        assert s.get("url") or s.get("location"), s["id"]


def test_public_safety_scan_passes() -> None:
    res = subprocess.run(
        [sys.executable, "scripts/check_public_safety.py"], cwd=ROOT, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout


def test_exif_cli_summary(tmp_path: Path, capsys) -> None:
    from fractions import Fraction

    from digimax.exif import build_test_jpeg

    for i, t in enumerate((Fraction(1, 30), Fraction(1, 30), Fraction(250, 577))):
        (tmp_path / f"S402{i:04d}.JPG").write_bytes(
            build_test_jpeg({0x829A: (5, t), 0x8827: (3, 200)})
        )
    files = sorted(str(p) for p in tmp_path.iterdir())
    code, out = run(capsys, "--json", "exif", "--summary", *files)
    res = json.loads(out)
    assert code == 0 and res["count"] == 3
    assert res["summary"]["exposure_time"] == {"1/30": 2, "250/577": 1}
    code, out = run(capsys, "--json", "exif", *files)
    assert all(r["file"] is None for r in json.loads(out)["files"])  # names hidden by default
