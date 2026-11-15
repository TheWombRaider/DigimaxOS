"""``digimax`` command-line interface.

Design rules (spec section 8):
  * every command is read-only; nothing writes to a camera or a storage device
  * commands that would need unverified capabilities exist but exit with
    status 3 ("unsupported") and explain which gate blocks them
  * ``--json`` gives machine-readable output; default output is for humans
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import __version__, env, exposure, fat, firmware, usb
from .sd import addressing, registers
from .sd.crc import command_frame, crc16_ccitt

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNSUPPORTED = 0, 1, 2, 3


def _default(o: Any) -> Any:
    if is_dataclass(o) and not isinstance(o, type):
        return asdict(o)
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, Fraction):
        return str(o)
    if isinstance(o, bytes):
        return o.hex()
    raise TypeError(type(o).__name__)


def emit(args: argparse.Namespace, payload: Any, human: Callable[[], None]) -> None:
    if args.json:
        json.dump(payload, sys.stdout, indent=2, default=_default)
        sys.stdout.write("\n")
    else:
        human()


# --------------------------------------------------------------------------- env
def cmd_env(args: argparse.Namespace) -> int:
    rep = env.check()

    def human() -> None:
        print(f"Python {rep['python']} on {rep['platform']}")
        print(f"USB sysfs available: {rep['usb_sysfs']}")
        ws = rep["private_workspace"]
        print(
            f"Private artifact workspace: {ws['path']} "
            f"({'exists, mode ' + ws.get('mode', '?') if ws['exists'] else 'missing'})"
        )
        for name, t in rep["tools"].items():
            print(f"  [{'x' if t['found'] else ' '}] {name:16} {t['purpose']}")
        for p in rep["problems"]:
            print(f"PROBLEM: {p}")

    emit(args, rep, human)
    return EXIT_OK if rep["ok"] else EXIT_FAIL


# ---------------------------------------------------------------------- discover
def cmd_discover(args: argparse.Namespace) -> int:
    if args.import_report:
        devices = usb.import_windows_report(args.import_report)
    else:
        devices = usb.scan_sysfs(all_devices=args.all)
    payload = {"devices": [d.to_dict(args.show_serial) for d in devices]}

    def human() -> None:
        if not devices:
            print("No Samsung/Sunplus or profiled USB devices found.")
            print(
                "If the camera is attached to another computer, run "
                "scripts/windows/Get-DigimaxInfo.ps1 there and pass the JSON with --import."
            )
            return
        for d in devices:
            dd = d.to_dict(args.show_serial)
            print(
                f"{dd['bus_path']}: {dd['vendor_id']}:{dd['product_id']} "
                f"bcd={dd['bcd_device']} {d.manufacturer or ''} {d.product or ''}".rstrip()
            )
            for i in d.interfaces:
                print(
                    f"    interface class {i['class']:02x}/{i['subclass']:02x}/{i['protocol']:02x}"
                )
            for b in d.block_devices:
                print(f"    block: {b}")
            if d.profile_matches:
                for m in d.profile_matches:
                    print(
                        f"    MATCH verified profile {m['profile']} ({m['name']}), "
                        f"mode {m['usb_mode']}"
                    )
            else:
                print("    no verified profile match - treat as unknown device")

    emit(args, payload, human)
    return EXIT_OK


def cmd_inspect(args: argparse.Namespace) -> int:
    from .profiles import load_profile

    prof = load_profile(args.profile)
    emit(args, prof, lambda: print(json.dumps(prof, indent=2)))
    return EXIT_OK


# ---------------------------------------------------------------------- firmware
def cmd_fw_inspect(args: argparse.Namespace) -> int:
    rep = firmware.inspect(args.file)

    def human() -> None:
        print(f"{rep.path}: {rep.size} bytes")
        print(f"  sha256 {rep.sha256}\n  sha1   {rep.sha1}\n  md5    {rep.md5}")
        print(
            f"  entropy {rep.entropy} bits/byte, 0xFF fill {rep.fill_ff_ratio:.1%}, "
            f"0x00 fill {rep.fill_00_ratio:.1%}"
        )
        print("  regions (4 KiB granularity):")
        for r in rep.regions[:40]:
            print(f"    0x{r.offset:08X} +0x{r.length:X}  {r.kind:22} H={r.entropy}")
        if len(rep.regions) > 40:
            print(f"    ... {len(rep.regions) - 40} more")
        print(f"  signatures: {len(rep.signatures)}")
        for s in rep.signatures[:20]:
            print(f"    0x{s['offset']:08X} {s['type']}")
        print(f"  strings: {rep.strings_ascii} ascii, {rep.strings_utf16} utf-16le; interesting:")
        for s in rep.interesting_strings[:30]:
            print(f"    0x{s['offset']:08X} [{s['encoding']}] {s['text']}")
        for h in rep.isa_hints:
            print(f"  ISA hint ({h['confidence']}): {h['isa']} - {h['clue']}")
        for n in rep.notes:
            print(f"  note: {n}")

    emit(args, rep.to_dict(), human)
    return EXIT_OK


def cmd_fw_compare(args: argparse.Namespace) -> int:
    rep = firmware.compare(args.a, args.b)

    def human() -> None:
        print(f"A {rep.a}: {rep.size_a} bytes sha256 {rep.sha256_a}")
        print(f"B {rep.b}: {rep.size_b} bytes sha256 {rep.sha256_b}")
        if rep.identical:
            print("IDENTICAL")
            return
        print(
            f"{rep.differing_bytes} differing bytes ({rep.identical_ratio:.4%} identical), "
            f"{len(rep.ranges)} ranges{' (truncated)' if rep.ranges_truncated else ''}"
        )
        for r in rep.ranges[:50]:
            print(f"  0x{r['offset']:08X} +{r['length']}")

    emit(args, rep.to_dict(), human)
    return EXIT_OK if rep.identical else EXIT_FAIL


# -------------------------------------------------------------------------- card
def cmd_card_check(args: argparse.Namespace) -> int:
    try:
        rep = fat.analyse(args.image, scan_fat=not args.no_fat_scan)
    except fat.ImageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    def human() -> None:
        print(
            f"{rep.path}: {rep.image_sectors} sectors ({rep.image_bytes} bytes), "
            f"layout {rep.layout}"
        )
        for p in rep.partitions:
            print(
                f"  partition {p.index}: type 0x{p.type_code:02X} {p.type_name}, "
                f"start {p.lba_start}, {p.sectors} sectors{' (boot)' if p.bootable else ''}"
            )
        if rep.fat:
            f = rep.fat
            print(
                f"  {f.fat_type}: OEM '{f.oem_name}', {f.cluster_count} clusters of "
                f"{f.cluster_bytes} bytes, {f.num_fats} FATs x {f.fat_sectors} sectors, "
                f"label {f.volume_label!r}, fs-type string {f.fs_type_label!r}"
            )
            print(
                f"  formatter: {f.formatter_hint}; data area cluster-aligned: {f.data_area_aligned}"
            )
            if f.computed_free_clusters is not None:
                print(
                    f"  free: {f.computed_free_clusters} clusters "
                    f"({f.computed_free_clusters * f.cluster_bytes} bytes)"
                )
        if rep.dcf:
            print(f"  DCIM present: {rep.dcf.get('dcim_present')}")
            for d in rep.dcf.get("folders", []):
                print(
                    f"    {d['name']}: {d['files']} files, DCF name ok={d['dcf_compliant_name']}, "
                    f"non-DCF files={d['non_dcf_files']}"
                )
        for w in rep.warnings:
            print(f"  warning: {w}")
        for e in rep.errors:
            print(f"  ERROR: {e}")
        print("  result:", "OK" if rep.ok else "PROBLEMS FOUND")

    emit(args, rep.to_dict(), human)
    return EXIT_OK if rep.ok else EXIT_FAIL


def cmd_card_make_pattern(args: argparse.Namespace) -> int:
    out = Path(args.output)
    if out.exists():
        print(f"error: {out} exists; refusing to overwrite", file=sys.stderr)
        return EXIT_USAGE
    if args.sectors > 4 * 1024 * 1024:
        print("error: --sectors limited to 4 Mi (2 GiB) for host-side fixtures", file=sys.stderr)
        return EXIT_USAGE
    with out.open("xb") as f:
        for lba in range(args.sectors):
            f.write(addressing.pattern_for_sector(lba, args.seed))
    emit(
        args,
        {"output": str(out), "sectors": args.sectors, "seed": args.seed},
        lambda: print(f"wrote {args.sectors} address-unique sectors to {out} (new file)"),
    )
    return EXIT_OK


def cmd_card_verify_pattern(args: argparse.Namespace) -> int:
    try:
        f = fat.open_image_readonly(args.image)
    except fat.ImageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    with f:
        size = Path(args.image).stat().st_size
        total = size // addressing.SECTOR
        lbas = range(total) if args.full else addressing.boundary_probe_lbas(total)
        failures = []
        for lba in lbas:
            f.seek(lba * addressing.SECTOR)
            chk = addressing.verify_sector(lba, f.read(addressing.SECTOR), args.seed)
            if not chk.ok:
                failures.append(asdict(chk))
    checked = len(lbas)
    payload = {
        "image": args.image,
        "sectors": total,
        "checked": checked,
        "coverage": "full" if args.full else "boundary-sample",
        "failures": failures[:1000],
        "failure_count": len(failures),
        "ok": not failures,
    }

    def human() -> None:
        print(
            f"checked {checked}/{total} sectors ({payload['coverage']}); {len(failures)} failures"
        )
        for fl in failures[:20]:
            print(f"  LBA {fl['lba']}: {fl['reason']}")

    emit(args, payload, human)
    return EXIT_OK if not failures else EXIT_FAIL


# ---------------------------------------------------------------------------- sd
def cmd_sd_csd(args: argparse.Namespace) -> int:
    csd = registers.decode_csd(args.hex)
    d = csd.to_dict()

    def human() -> None:
        print(f"CSD v{csd.version} ({csd.capacity_class}), CRC {'ok' if csd.crc_valid else 'BAD'}")
        print(
            f"  capacity {csd.capacity_bytes} bytes = {csd.capacity_sectors} sectors "
            f"({csd.capacity_bytes / 1e9:.3f} GB)"
        )
        print(
            "  addressing: "
            + ("block (CMD arg = LBA)" if csd.block_addressed else "byte (CMD arg = LBA*512)")
        )
        print(
            f"  C_SIZE={csd.c_size} C_SIZE_MULT={csd.c_size_mult} READ_BL_LEN={csd.read_bl_len} "
            f"TRAN_SPEED={csd.tran_speed_kbit} kbit/s CCC={d['ccc']}"
        )
        print(f"  write protect: perm={csd.perm_write_protect} tmp={csd.tmp_write_protect}")
        for w in csd.warnings:
            print(f"  warning: {w}")

    emit(args, d, human)
    return EXIT_OK


def cmd_sd_ocr(args: argparse.Namespace) -> int:
    ocr = registers.decode_ocr(int(args.hex, 16))
    emit(args, ocr.to_dict(), lambda: print(json.dumps(ocr.to_dict(), indent=2)))
    return EXIT_OK


def cmd_sd_address(args: argparse.Namespace) -> int:
    geom = addressing.Geometry(args.capacity_sectors, addressing.Addressing(args.addressing))
    try:
        arg = addressing.command_argument(geom, args.lba, args.count)
    except addressing.AddressError as exc:
        msg = str(exc)
        emit(args, {"ok": False, "error": msg}, lambda: print(f"REJECTED: {msg}"))
        return EXIT_FAIL
    payload = {
        "ok": True,
        "lba": args.lba,
        "argument": arg,
        "argument_hex": f"0x{arg:08X}",
        "cmd17_frame": command_frame(17, arg).hex(),
    }
    emit(
        args,
        payload,
        lambda: print(
            f"LBA {args.lba} -> CMD argument 0x{arg:08X} (CMD17 frame {payload['cmd17_frame']})"
        ),
    )
    return EXIT_OK


def cmd_sd_frame(args: argparse.Namespace) -> int:
    frame = command_frame(args.index, int(args.argument, 0))
    emit(args, {"frame": frame.hex()}, lambda: print(frame.hex(" ")))
    return EXIT_OK


def cmd_sd_crc16(args: argparse.Namespace) -> int:
    data = Path(args.file).read_bytes()
    crc = crc16_ccitt(data)
    emit(args, {"crc16": f"0x{crc:04X}", "bytes": len(data)}, lambda: print(f"0x{crc:04X}"))
    return EXIT_OK


# ---------------------------------------------------------------------- exposure
def cmd_exposure_table(args: argparse.Namespace) -> int:
    cap = exposure.Capability()
    rows = cap.matrix()

    def human() -> None:
        print(
            "A402 exposure space: range from S1 p.85; shutter values 'observed' are selectable in"
        )
        print(
            "the stock Night-mode menu (EXP-0004, timing not yet measured); 'candidate' values are"
        )
        print("unconfirmed. See docs/test-plans/exposure-baseline.md.\n")
        print(f"{'shutter':>8} {'f/':>4} {'ISO':>4} {'EV100':>6}  {'shutter status':<15} overall")
        for r in rows:
            print(
                f"{r['shutter']:>8} {r['aperture']:>4} {r['iso']:>4} {r['ev100']:>6}  "
                f"{r['shutter_status']:<15} {r['status']}"
            )

    emit(args, rows, human)
    return EXIT_OK


def cmd_exposure_mock(args: argparse.Namespace) -> int:
    ui = exposure.MModeUI()
    keys = [exposure.Key(k) for k in args.keys]
    frames = []
    for k in keys:
        ui.press(k)
        frames.append({"key": k.value, "screen": ui.render(scene_ev100=args.scene_ev)})

    def human() -> None:
        print("Host-side mock of the PROPOSED M mode. Not firmware; layout is not pixel-accurate.")
        print(ui.render(scene_ev100=args.scene_ev) if not frames else "")
        for fr in frames:
            print(f"after '{fr['key']}':\n{fr['screen']}")

    emit(args, {"frames": frames, "final": asdict(ui.committed)}, human)
    return EXIT_OK


# ------------------------------------------------------------------- unsupported
UNSUPPORTED = {
    ("patch", "plan"): "G1: no verified base firmware identity/hash exists yet",
    ("patch", "build"): "G2: recovery gate not met; patch building is disabled",
    ("capture",): "USB-01: no verified tethering protocol; capture is not implemented",
}


def cmd_unsupported(args: argparse.Namespace) -> int:
    key = tuple(args.unsupported_key)
    reason = UNSUPPORTED[key]
    payload = {"supported": False, "command": " ".join(key), "blocked_by": reason}
    emit(
        args, payload, lambda: print(f"digimax {' '.join(key)}: UNSUPPORTED - blocked by {reason}")
    )
    return EXIT_UNSUPPORTED


# ------------------------------------------------------------------------ parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="digimax", description=__doc__.split("\n\n")[0])
    p.add_argument("--version", action="version", version=f"digimax {__version__}")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("env", help="host environment")
    esub = e.add_subparsers(dest="sub", required=True)
    esub.add_parser("check", help="inventory host tools and private workspace").set_defaults(
        fn=cmd_env
    )

    d = sub.add_parser("discover", help="read-only USB discovery")
    d.add_argument("--all", action="store_true", help="list every USB device, not just candidates")
    d.add_argument("--show-serial", action="store_true", help="do not redact serial numbers")
    d.add_argument(
        "--import",
        dest="import_report",
        metavar="JSON",
        help="evaluate a report from scripts/windows/Get-DigimaxInfo.ps1",
    )
    d.set_defaults(fn=cmd_discover)

    i = sub.add_parser("inspect", help="show a device profile and its verification status")
    i.add_argument("--profile", default="a402")
    i.set_defaults(fn=cmd_inspect)

    fw = sub.add_parser("firmware", help="offline firmware file analysis").add_subparsers(
        dest="sub", required=True
    )
    fi = fw.add_parser("inspect", help="hashes, entropy map, signatures, strings, ISA hints")
    fi.add_argument("file")
    fi.set_defaults(fn=cmd_fw_inspect)
    fc = fw.add_parser("compare", help="byte-level comparison of two files")
    fc.add_argument("a")
    fc.add_argument("b")
    fc.set_defaults(fn=cmd_fw_compare)

    card = sub.add_parser("card", help="card *image* analysis (never devices)").add_subparsers(
        dest="sub", required=True
    )
    cc = card.add_parser("check", help="MBR/FAT/DCF consistency of an image file")
    cc.add_argument("image")
    cc.add_argument("--no-fat-scan", action="store_true", help="skip free-cluster scan")
    cc.set_defaults(fn=cmd_card_check)
    cm = card.add_parser("make-pattern", help="create a NEW image file of address-unique sectors")
    cm.add_argument("output")
    cm.add_argument("--sectors", type=int, required=True)
    cm.add_argument("--seed", type=int, default=1)
    cm.set_defaults(fn=cmd_card_make_pattern)
    cv = card.add_parser("verify-pattern", help="detect aliasing/wrap in a pattern image")
    cv.add_argument("image")
    cv.add_argument("--seed", type=int, default=1)
    cv.add_argument("--full", action="store_true", help="check every sector, not a boundary sample")
    cv.set_defaults(fn=cmd_card_verify_pattern)

    sd = sub.add_parser("sd", help="SD protocol reference calculations").add_subparsers(
        dest="sub", required=True
    )
    s1 = sd.add_parser("csd", help="decode a 128-bit CSD register (32 hex digits)")
    s1.add_argument("hex")
    s1.set_defaults(fn=cmd_sd_csd)
    s2 = sd.add_parser("ocr", help="decode a 32-bit OCR register")
    s2.add_argument("hex")
    s2.set_defaults(fn=cmd_sd_ocr)
    s3 = sd.add_parser("address", help="LBA -> CMD17/24 argument with range checks")
    s3.add_argument("--capacity-sectors", type=int, required=True)
    s3.add_argument("--addressing", choices=["byte", "block"], required=True)
    s3.add_argument("--count", type=int, default=1)
    s3.add_argument("lba", type=int)
    s3.set_defaults(fn=cmd_sd_address)
    s4 = sd.add_parser("frame", help="build a command token with CRC7")
    s4.add_argument("index", type=int)
    s4.add_argument("argument")
    s4.set_defaults(fn=cmd_sd_frame)
    s5 = sd.add_parser("crc16", help="CRC16-CCITT of a data block file")
    s5.add_argument("file")
    s5.set_defaults(fn=cmd_sd_crc16)

    ex = sub.add_parser("exposure", help="exposure model and M-mode UI mock").add_subparsers(
        dest="sub", required=True
    )
    ex.add_parser("table", help="documented exposure matrix with EV values").set_defaults(
        fn=cmd_exposure_table
    )
    em = ex.add_parser("mock", help="drive the proposed M-mode UI state machine")
    em.add_argument("keys", nargs="*", choices=[k.value for k in exposure.Key])
    em.add_argument("--scene-ev", type=float, default=None, help="scene EV100 for the meter")
    em.set_defaults(fn=cmd_exposure_mock)

    pt = sub.add_parser("patch", help="(unsupported) firmware patch planning").add_subparsers(
        dest="sub", required=True
    )
    for name in ("plan", "build"):
        sp = pt.add_parser(name, help="UNSUPPORTED until gates are met")
        sp.add_argument("base", nargs="?")
        sp.add_argument("profile", nargs="?")
        sp.set_defaults(fn=cmd_unsupported, unsupported_key=["patch", name])
    sub.add_parser("capture", help="(unsupported) tethered capture").set_defaults(
        fn=cmd_unsupported, unsupported_key=["capture"]
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.fn(args))
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
