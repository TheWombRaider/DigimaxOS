"""Deterministic synthetic FAT16/FAT32 card images for tests (sparse files).

Independent of mkfs: lets CI run without dosfstools and lets us build exact
geometries (e.g. the one observed on the reference A402 card in EXP-0001).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

SECTOR = 512


@dataclass
class Layout:
    total_sectors: int
    partition_start: int
    fat_type: str  # "FAT16" | "FAT32"
    sectors_per_cluster: int
    fat_sectors: int
    reserved: int
    root_entries: int
    clusters: int


def _plan(total: int, start: int, fat_type: str, spc: int) -> Layout:
    vol = total - start
    reserved = 32 if fat_type == "FAT32" else 1
    root_entries = 0 if fat_type == "FAT32" else 512
    root_secs = root_entries * 32 // SECTOR
    entry = {"FAT32": 4.0, "FAT16": 2.0, "FAT12": 1.5}[fat_type]
    fat_secs = 1
    while True:
        data = vol - reserved - 2 * fat_secs - root_secs
        clusters = data // spc
        need = (int((clusters + 2) * entry + 0.5) + SECTOR - 1) // SECTOR
        if need <= fat_secs:
            break
        fat_secs = need
    return Layout(total, start, fat_type, spc, fat_secs, reserved, root_entries, clusters)


def _dirent(name: str, ext: str, attr: int, cluster: int, size: int) -> bytes:
    return struct.pack(
        "<8s3sBBBHHHHHHHI",
        name.ljust(8).encode(),
        ext.ljust(3).encode(),
        attr,
        0,
        0,
        0,
        0,
        0,
        cluster >> 16,
        0,
        0x5A21,  # 2025-01-01
        cluster & 0xFFFF,
        size,
    )


def make_image(
    path: Path,
    *,
    total_sectors: int,
    fat_type: str = "FAT16",
    partition_start: int = 32,
    sectors_per_cluster: int = 32,
    partition_type: int | None = None,
    photos: int = 3,
    oem: str = "DGMXTEST",
    mbr: bool = True,
    jump: bytes | None = None,
    hidden: int | None = None,
    geometry: tuple[int, int] = (63, 255),
) -> Layout:
    start = partition_start if mbr else 0
    lay = _plan(total_sectors, start, fat_type, sectors_per_cluster)
    ptype = (
        partition_type
        if partition_type is not None
        else {"FAT32": 0x0C, "FAT16": 0x06, "FAT12": 0x01}[fat_type]
    )
    cluster_bytes = SECTOR * sectors_per_cluster
    root_secs = lay.root_entries * 32 // SECTOR
    first_data = start + lay.reserved + 2 * lay.fat_sectors + root_secs

    def clba(c: int) -> int:
        return first_data + (c - 2) * sectors_per_cluster

    with path.open("wb") as f:
        f.truncate(total_sectors * SECTOR)

        def put(lba: int, data: bytes) -> None:
            f.seek(lba * SECTOR)
            f.write(data)

        if mbr:
            m = bytearray(SECTOR)
            struct.pack_into(
                "<B3sB3sII",
                m,
                446,
                0x00,
                b"\x00\x02\x00",
                ptype,
                b"\xff\xff\xff",
                start,
                total_sectors - start,
            )
            m[510:512] = b"\x55\xaa"
            put(0, bytes(m))

        b = bytearray(SECTOR)
        b[0:3] = jump or (b"\xeb\x58\x90" if fat_type == "FAT32" else b"\xeb\x3c\x90")
        b[3:11] = oem.ljust(8).encode()[:8]
        vol = total_sectors - start
        struct.pack_into(
            "<HBHBHHBHHHII",
            b,
            11,
            SECTOR,
            sectors_per_cluster,
            lay.reserved,
            2,
            lay.root_entries,
            vol if vol < 65536 and fat_type != "FAT32" else 0,
            0xF8,
            0 if fat_type == "FAT32" else lay.fat_sectors,
            geometry[0],
            geometry[1],
            start if hidden is None else hidden,
            0 if (vol < 65536 and fat_type != "FAT32") else vol,
        )
        if fat_type == "FAT32":
            struct.pack_into("<IHHIHH", b, 36, lay.fat_sectors, 0, 0, 2, 1, 6)
            struct.pack_into(
                "<BBBI11s8s", b, 64, 0x80, 0, 0x29, 0x12345678, b"NO NAME    ", b"FAT32   "
            )
        else:
            struct.pack_into(
                "<BBBI11s8s",
                b,
                36,
                0x80,
                0,
                0x29,
                0x12345678,
                b"NO NAME    ",
                fat_type.ljust(8).encode(),
            )
        b[510:512] = b"\x55\xaa"
        put(start, bytes(b))

        # cluster allocation: [root (FAT32 only)], DCIM, 100SSCAM, photos...
        next_c = 2
        root_c = None
        if fat_type == "FAT32":
            root_c, next_c = 2, 3
        dcim_c, folder_c = next_c, next_c + 1
        photo_cs = list(range(folder_c + 1, folder_c + 1 + photos))
        used = ([root_c] if root_c else []) + [dcim_c, folder_c, *photo_cs]
        last_used = max(used)

        if fat_type == "FAT32":
            fsi = bytearray(SECTOR)
            struct.pack_into("<I", fsi, 0, 0x41615252)
            struct.pack_into("<III", fsi, 484, 0x61417272, lay.clusters - len(used), last_used + 1)
            fsi[510:512] = b"\x55\xaa"
            put(start + 1, bytes(fsi))
            put(start + 6, bytes(b))

        fat = bytearray(lay.fat_sectors * SECTOR)
        if fat_type == "FAT12":

            def set12(c: int, v: int) -> None:
                off = c + c // 2
                if c & 1:
                    fat[off] = (fat[off] & 0x0F) | ((v << 4) & 0xF0)
                    fat[off + 1] = (v >> 4) & 0xFF
                else:
                    fat[off] = v & 0xFF
                    fat[off + 1] = (fat[off + 1] & 0xF0) | ((v >> 8) & 0x0F)

            set12(0, 0xFF8)
            set12(1, 0xFFF)
            for c in used:
                set12(c, 0xFFF)
        else:
            eoc = 0x0FFFFFFF if fat_type == "FAT32" else 0xFFFF
            fmt = "<I" if fat_type == "FAT32" else "<H"
            size = 4 if fat_type == "FAT32" else 2
            struct.pack_into(fmt, fat, 0, (0x0FFFFFF8 if fat_type == "FAT32" else 0xFFF8))
            struct.pack_into(fmt, fat, size, eoc)
            for c in used:
                struct.pack_into(fmt, fat, c * size, eoc)
        for copy in range(2):
            put(start + lay.reserved + copy * lay.fat_sectors, bytes(fat))

        root = _dirent("DCIM", "", 0x10, dcim_c, 0)
        if fat_type == "FAT32":
            assert root_c is not None
            put(clba(root_c), root)
        else:
            put(start + lay.reserved + 2 * lay.fat_sectors, root)
        put(
            clba(dcim_c),
            _dirent(".", "", 0x10, dcim_c, 0)
            + _dirent("..", "", 0x10, 0, 0)
            + _dirent("100SSCAM", "", 0x10, folder_c, 0),
        )
        entries = _dirent(".", "", 0x10, folder_c, 0) + _dirent("..", "", 0x10, dcim_c, 0)
        for i, c in enumerate(photo_cs, start=1):
            entries += _dirent(f"SV40{i:04d}", "JPG", 0x20, c, cluster_bytes)
            put(clba(c), b"\xff\xd8\xff\xe1" + b"\x00" * (cluster_bytes - 4))
        put(clba(folder_c), entries)
    return lay
