"""Read-only MBR / FAT12/16/32 analysis of card *image files*.

Used by ``digimax card check IMAGE``. The analysis never writes and refuses
block/character devices: run it on an image file made with an explicitly
approved, read-only imaging step (see docs/development/card-imaging.md).

FAT type is determined by cluster count, as in Microsoft's FAT specification
(<4085 FAT12, <65525 FAT16, otherwise FAT32) - never by the label string.
"""

from __future__ import annotations

import os
import re
import stat
import struct
from dataclasses import asdict, dataclass, field
from typing import Any, BinaryIO

SECTOR = 512

PARTITION_TYPES = {
    0x00: "empty",
    0x01: "FAT12 (CHS)",
    0x04: "FAT16 <32MB (CHS)",
    0x06: "FAT16 >=32MB (CHS)",
    0x07: "NTFS/exFAT",
    0x0B: "FAT32 (CHS)",
    0x0C: "FAT32 (LBA)",
    0x0E: "FAT16 (LBA)",
    0x0F: "extended (LBA)",
    0x05: "extended (CHS)",
    0xEE: "GPT protective",
}

DCF_DIR = re.compile(r"^[1-9][0-9]{2}[0-9A-Z_]{5}$")
DCF_FILE = re.compile(r"^[0-9A-Z_]{4}[0-9]{4}\.(JPG|AVI|WAV|THM|TIF)$")


class ImageError(ValueError):
    pass


@dataclass
class Partition:
    index: int
    bootable: bool
    type_code: int
    type_name: str
    lba_start: int
    sectors: int


@dataclass
class FatInfo:
    offset_sector: int
    oem_name: str
    bytes_per_sector: int
    sectors_per_cluster: int
    cluster_bytes: int
    reserved_sectors: int
    num_fats: int
    root_entries: int
    total_sectors: int
    fat_sectors: int
    media: int
    hidden_sectors: int
    data_sectors: int
    cluster_count: int
    fat_type: str
    volume_id: str | None
    volume_label: str | None
    fs_type_label: str | None
    root_cluster: int | None = None
    fsinfo_sector: int | None = None
    fsinfo_free_count: int | None = None
    fsinfo_next_free: int | None = None
    computed_free_clusters: int | None = None
    formatter_hint: str = "unknown"
    data_area_aligned: bool | None = None  # first data sector is a multiple of the cluster size


@dataclass
class DirEntry:
    name: str
    is_dir: bool
    size: int
    first_cluster: int


@dataclass
class CardReport:
    path: str
    image_bytes: int
    image_sectors: int
    layout: str  # "mbr", "superfloppy"
    partitions: list[Partition] = field(default_factory=list)
    fat: FatInfo | None = None
    root: list[DirEntry] = field(default_factory=list)
    dcf: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ok"] = self.ok
        return d


def open_image_readonly(path: str) -> BinaryIO:
    st = os.stat(path)
    if stat.S_ISBLK(st.st_mode) or stat.S_ISCHR(st.st_mode):
        raise ImageError(
            f"{path} is a device node. card check only reads image files; create an image "
            "with an approved read-only imaging step first (docs/development/card-imaging.md)."
        )
    if not stat.S_ISREG(st.st_mode):
        raise ImageError(f"{path} is not a regular file")
    return open(path, "rb")


def _read(f: BinaryIO, lba: int, count: int = 1) -> bytes:
    f.seek(lba * SECTOR)
    data = f.read(count * SECTOR)
    if len(data) != count * SECTOR:
        raise ImageError(f"image truncated at sector {lba}")
    return data


def _looks_like_bpb(sector: bytes) -> bool:
    if sector[510:512] != b"\x55\xaa":
        return False
    if sector[0] not in (0xEB, 0xE9):
        return False
    bps = struct.unpack_from("<H", sector, 11)[0]
    spc = sector[13]
    return bps in (512, 1024, 2048, 4096) and spc in (1, 2, 4, 8, 16, 32, 64, 128)


def parse_mbr(sector: bytes) -> list[Partition]:
    parts = []
    for i in range(4):
        off = 446 + 16 * i
        boot, ptype = sector[off], sector[off + 4]
        start, count = struct.unpack_from("<II", sector, off + 8)
        if ptype == 0 and count == 0:
            continue
        parts.append(
            Partition(
                i + 1,
                boot == 0x80,
                ptype,
                PARTITION_TYPES.get(ptype, f"unknown 0x{ptype:02X}"),
                start,
                count,
            )
        )
    return parts


def fingerprint_formatter(sector: bytes) -> str:
    """Best-effort guess of which formatter wrote a FAT boot sector (heuristic).

    Used to tell whether the *camera* formatted a card (SD-01 baseline). The camera rule comes
    from the reference unit's internal memory (EXP-0003): blank OEM name, jump ``E9 00 00`` and
    no boot code at all.
    """
    oem = sector[3:11]
    fat32 = struct.unpack_from("<H", sector, 22)[0] == 0
    boot = sector[90 if fat32 else 62 : 510]
    if oem == b" " * 8 and sector[0:3] == b"\xe9\x00\x00" and not any(boot):
        return "embedded camera formatter (matches Digimax A402 internal memory, EXP-0003)"
    text = oem.decode("ascii", "replace")
    for prefix, who in (
        ("MSDOS5.0", "Windows / DOS"),
        ("MSWIN4.", "Windows 9x"),
        ("mkfs.fat", "Linux dosfstools"),
        ("mkdosfs", "Linux dosfstools"),
        ("BSD  4.4", "macOS / BSD newfs_msdos"),
    ):
        if text.startswith(prefix):
            return who
    return f"unknown (OEM name {text!r})"


def parse_bpb(sector: bytes, offset_sector: int) -> FatInfo:
    (bps,) = struct.unpack_from("<H", sector, 11)
    spc = sector[13]
    reserved, nfats, root_entries, tot16 = struct.unpack_from("<HBHH", sector, 14)
    media = sector[21]
    (fat16sz,) = struct.unpack_from("<H", sector, 22)
    hidden, tot32 = struct.unpack_from("<II", sector, 28)
    total = tot16 or tot32
    fat_sectors = fat16sz
    fat32 = fat16sz == 0
    if fat32:
        (fat_sectors,) = struct.unpack_from("<I", sector, 36)
    if bps == 0 or spc == 0:
        raise ImageError("BPB has zero bytes-per-sector or sectors-per-cluster")
    root_dir_sectors = (root_entries * 32 + bps - 1) // bps
    data_sectors = total - (reserved + nfats * fat_sectors + root_dir_sectors)
    clusters = data_sectors // spc if data_sectors > 0 else 0
    if clusters < 4085:
        fat_type = "FAT12"
    elif clusters < 65525:
        fat_type = "FAT16"
    else:
        fat_type = "FAT32"

    def _txt(raw: bytes) -> str:
        return raw.decode("ascii", "replace").rstrip()

    ext = 64 if fat32 else 36  # offset of drive number in extended BPB
    sig = sector[ext + 2]
    vol_id = label = fstype = None
    if sig in (0x28, 0x29):
        (vid,) = struct.unpack_from("<I", sector, ext + 3)
        vol_id = f"{vid >> 16:04X}-{vid & 0xFFFF:04X}"
        if sig == 0x29:
            label = _txt(sector[ext + 7 : ext + 18])
            fstype = _txt(sector[ext + 18 : ext + 26])
    info = FatInfo(
        offset_sector=offset_sector,
        oem_name=_txt(sector[3:11]),
        bytes_per_sector=bps,
        sectors_per_cluster=spc,
        cluster_bytes=bps * spc,
        reserved_sectors=reserved,
        num_fats=nfats,
        root_entries=root_entries,
        total_sectors=total,
        fat_sectors=fat_sectors,
        media=media,
        hidden_sectors=hidden,
        data_sectors=data_sectors,
        cluster_count=clusters,
        fat_type=fat_type,
        volume_id=vol_id,
        volume_label=label,
        fs_type_label=fstype,
    )
    if fat32:
        info.root_cluster, info.fsinfo_sector = struct.unpack_from("<IH", sector, 44)
    info.formatter_hint = fingerprint_formatter(sector)
    first_data = offset_sector + reserved + nfats * fat_sectors + root_dir_sectors
    info.data_area_aligned = first_data % spc == 0
    return info


def _fat_entries(f: BinaryIO, info: FatInfo) -> list[int]:
    raw = _read(f, info.offset_sector + info.reserved_sectors, info.fat_sectors)
    n = info.cluster_count + 2
    if info.fat_type == "FAT32":
        return [v & 0x0FFF_FFFF for v in struct.unpack_from(f"<{n}I", raw)]
    if info.fat_type == "FAT16":
        return list(struct.unpack_from(f"<{n}H", raw))
    out = []
    for c in range(n):
        off = c + c // 2
        v = raw[off] | raw[off + 1] << 8
        out.append(v >> 4 if c & 1 else v & 0xFFF)
    return out


def _eoc(info: FatInfo, v: int) -> bool:
    return v >= {"FAT12": 0xFF8, "FAT16": 0xFFF8, "FAT32": 0x0FFF_FFF8}[info.fat_type]


def _cluster_lba(info: FatInfo, cluster: int) -> int:
    root_dir_sectors = (info.root_entries * 32 + info.bytes_per_sector - 1) // info.bytes_per_sector
    first_data = info.reserved_sectors + info.num_fats * info.fat_sectors + root_dir_sectors
    return info.offset_sector + first_data + (cluster - 2) * info.sectors_per_cluster


def _parse_dir(raw: bytes) -> list[DirEntry]:
    out = []
    for off in range(0, len(raw), 32):
        e = raw[off : off + 32]
        if e[0] == 0x00:
            break
        if e[0] == 0xE5 or e[11] == 0x0F or e[11] & 0x08:  # deleted, LFN, volume label
            continue
        base = e[0:8].decode("ascii", "replace").rstrip()
        extn = e[8:11].decode("ascii", "replace").rstrip()
        if base in (".", ".."):
            continue
        hi, lo = struct.unpack_from("<H", e, 20)[0], struct.unpack_from("<H", e, 26)[0]
        (size,) = struct.unpack_from("<I", e, 28)
        out.append(
            DirEntry(f"{base}.{extn}" if extn else base, bool(e[11] & 0x10), size, hi << 16 | lo)
        )
    return out


def _read_chain(f: BinaryIO, info: FatInfo, fat: list[int], start: int, limit: int = 4096) -> bytes:
    data, c, seen = bytearray(), start, 0
    while 2 <= c < len(fat) and seen < limit:
        data += _read(f, _cluster_lba(info, c), info.sectors_per_cluster)
        c = fat[c]
        seen += 1
        if _eoc(info, c):
            break
    return bytes(data)


def analyse(path: str, *, scan_fat: bool = True) -> CardReport:
    with open_image_readonly(path) as f:
        size = os.fstat(f.fileno()).st_size
        rep = CardReport(path=path, image_bytes=size, image_sectors=size // SECTOR, layout="?")
        if size % SECTOR:
            rep.warnings.append(f"image size {size} is not a multiple of {SECTOR}")
        if size < SECTOR:
            rep.errors.append("image smaller than one sector")
            return rep
        s0 = _read(f, 0)
        if _looks_like_bpb(s0):
            rep.layout = "superfloppy"
            rep.warnings.append("no partition table (superfloppy); DCF cameras normally use MBR")
            offset = 0
        elif s0[510:512] == b"\x55\xaa":
            rep.layout = "mbr"
            rep.partitions = parse_mbr(s0)
            for p in rep.partitions:
                if p.lba_start + p.sectors > rep.image_sectors:
                    rep.errors.append(
                        f"partition {p.index} ends at sector {p.lba_start + p.sectors}, beyond "
                        f"image end {rep.image_sectors} (truncated image or bad table)"
                    )
                if p.type_code == 0xEE:
                    rep.errors.append("GPT disk: not a DCF/SD-standard layout")
            fat_parts = [p for p in rep.partitions if p.type_code in (1, 4, 6, 0x0B, 0x0C, 0x0E)]
            if not fat_parts:
                rep.errors.append("no FAT partition in MBR")
                return rep
            if len(rep.partitions) > 1:
                rep.warnings.append("multiple partitions; cameras normally use only the first")
            offset = fat_parts[0].lba_start
            if offset % 8:
                rep.warnings.append(f"partition start {offset} not 4 KiB aligned")
        else:
            rep.errors.append("sector 0 has no 0x55AA signature: unformatted or unknown layout")
            return rep

        try:
            vbr = _read(f, offset)
        except ImageError as exc:
            rep.errors.append(str(exc))
            return rep
        if vbr[510:512] != b"\x55\xaa":
            rep.errors.append(f"volume boot sector at {offset} lacks 0x55AA signature")
            return rep
        info = parse_bpb(vbr, offset)
        rep.fat = info
        _validate(rep, info)
        if rep.errors:
            return rep

        if info.fat_type == "FAT32" and info.fsinfo_sector:
            fsi = _read(f, offset + info.fsinfo_sector)
            sigs = struct.unpack_from("<I", fsi, 0)[0], struct.unpack_from("<I", fsi, 484)[0]
            if sigs != (0x4161_5252, 0x6141_7272) or fsi[510:512] != b"\x55\xaa":
                rep.warnings.append("FSInfo signatures invalid; free-space hint unusable")
            else:
                free, nxt = struct.unpack_from("<II", fsi, 488)
                info.fsinfo_free_count = None if free == 0xFFFF_FFFF else free
                info.fsinfo_next_free = None if nxt == 0xFFFF_FFFF else nxt
                if free != 0xFFFF_FFFF and free > info.cluster_count:
                    rep.warnings.append("FSInfo free count exceeds cluster count")

        fat: list[int] | None = None
        if scan_fat:
            fat = _fat_entries(f, info)
            info.computed_free_clusters = sum(1 for v in fat[2:] if v == 0)
            if (
                info.fsinfo_free_count is not None
                and info.fsinfo_free_count != info.computed_free_clusters
            ):
                rep.warnings.append(
                    f"FSInfo free count {info.fsinfo_free_count} != computed "
                    f"{info.computed_free_clusters} (stale hint; harmless if firmware recomputes)"
                )

        if info.fat_type == "FAT32":
            if fat is None:
                fat = _fat_entries(f, info)
            root_raw = _read_chain(f, info, fat, info.root_cluster or 2)
        else:
            root_lba = offset + info.reserved_sectors + info.num_fats * info.fat_sectors
            root_secs = (info.root_entries * 32 + info.bytes_per_sector - 1) // SECTOR
            root_raw = _read(f, root_lba, root_secs)
        rep.root = _parse_dir(root_raw)
        rep.dcf = _dcf(f, info, fat, rep.root)
    return rep


def _validate(rep: CardReport, info: FatInfo) -> None:
    if info.bytes_per_sector != 512:
        rep.warnings.append(f"bytes per sector {info.bytes_per_sector}; SD media use 512")
    if info.sectors_per_cluster & (info.sectors_per_cluster - 1):
        rep.errors.append("sectors per cluster is not a power of two")
    if info.cluster_bytes > 32768:
        rep.warnings.append(f"{info.cluster_bytes}-byte clusters exceed 32 KiB (compatibility)")
    if info.num_fats not in (1, 2):
        rep.warnings.append(f"unusual FAT count {info.num_fats}")
    if info.data_sectors <= 0:
        rep.errors.append("BPB leaves no data area")
    needed = {"FAT12": (info.cluster_count + 2) * 3 // 2, "FAT16": (info.cluster_count + 2) * 2}
    needed_bytes = needed.get(info.fat_type, (info.cluster_count + 2) * 4)
    if info.fat_sectors * info.bytes_per_sector < needed_bytes:
        rep.errors.append("FAT is too small for the cluster count")
    end = info.offset_sector + info.total_sectors
    if end > rep.image_sectors:
        rep.errors.append(
            f"volume claims {info.total_sectors} sectors ending at {end}, beyond image end "
            f"{rep.image_sectors}: capacity mismatch, truncated image or aliasing risk"
        )
    for p in rep.partitions:
        if p.lba_start == info.offset_sector and p.sectors < info.total_sectors:
            rep.errors.append("volume is larger than its partition")
        if p.lba_start == info.offset_sector:
            expected = {
                "FAT12": {0x01},
                "FAT16": {0x04, 0x06, 0x0E},
                "FAT32": {0x0B, 0x0C},
            }[info.fat_type]
            if p.type_code not in expected:
                rep.warnings.append(
                    f"partition type 0x{p.type_code:02X} does not match {info.fat_type}"
                )
            if info.hidden_sectors not in (0, p.lba_start):
                rep.warnings.append("BPB hidden sectors does not match partition start")
    if info.fat_type == "FAT32" and info.root_entries:
        rep.errors.append("FAT32 volume with non-zero root entry count")


def _dcf(f: BinaryIO, info: FatInfo, fat: list[int] | None, root: list[DirEntry]) -> dict[str, Any]:
    dcim = next((e for e in root if e.is_dir and e.name == "DCIM"), None)
    out: dict[str, Any] = {"dcim_present": dcim is not None, "folders": []}
    if dcim is None or fat is None:
        return out
    entries = _parse_dir(_read_chain(f, info, fat, dcim.first_cluster))
    for d in entries:
        if not d.is_dir:
            continue
        files = _parse_dir(_read_chain(f, info, fat, d.first_cluster))
        out["folders"].append(
            {
                "name": d.name,
                "dcf_compliant_name": bool(DCF_DIR.match(d.name)),
                "files": len([x for x in files if not x.is_dir]),
                "non_dcf_files": len(
                    [x for x in files if not x.is_dir and not DCF_FILE.match(x.name)]
                ),
            }
        )
    return out
