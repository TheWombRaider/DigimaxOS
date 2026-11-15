import os
import shutil
import subprocess
from pathlib import Path

import pytest
from digimax.fat import ImageError, analyse
from fixtures.fatimage import make_image

# Geometry observed on the reference unit's card in EXP-0001 (sector counts only, no content).
A402_CARD_SECTORS = 985_088
A402_PART_START = 32
A402_PART_SECTORS = 984_832


def test_a402_observed_geometry_parses(tmp_path: Path) -> None:
    img = tmp_path / "a402.img"
    make_image(
        img,
        total_sectors=A402_PART_START + A402_PART_SECTORS,
        fat_type="FAT16",
        partition_start=A402_PART_START,
        sectors_per_cluster=32,
    )
    with img.open("r+b") as f:  # extend to the full card size (unpartitioned tail)
        f.truncate(A402_CARD_SECTORS * 512)
    r = analyse(str(img))
    assert r.ok, r.errors
    assert r.fat is not None
    assert r.fat.fat_type == "FAT16"
    assert r.fat.cluster_bytes == 16384
    assert r.partitions[0].type_code == 0x06
    assert r.dcf["dcim_present"]
    assert r.dcf["folders"][0]["name"] == "100SSCAM"
    assert r.dcf["folders"][0]["dcf_compliant_name"]
    assert r.dcf["folders"][0]["files"] == 3


@pytest.mark.parametrize("gb", [4, 32])
def test_fat32_sdhc_layout(tmp_path: Path, gb: int) -> None:
    sectors = gb * 1000**3 // 512
    img = tmp_path / f"sdhc{gb}.img"
    make_image(
        img, total_sectors=sectors, fat_type="FAT32", partition_start=8192, sectors_per_cluster=64
    )
    r = analyse(str(img))
    assert r.ok, r.errors
    assert r.fat is not None and r.fat.fat_type == "FAT32"
    assert r.fat.cluster_count >= 65525
    assert r.fat.fsinfo_free_count == r.fat.computed_free_clusters
    assert r.dcf["folders"][0]["files"] == 3


def test_truncated_image_is_an_error(tmp_path: Path) -> None:
    img = tmp_path / "t.img"
    make_image(img, total_sectors=200_000, fat_type="FAT16", sectors_per_cluster=8)
    with img.open("r+b") as f:
        f.truncate(150_000 * 512)
    r = analyse(str(img))
    assert not r.ok
    assert any("beyond image end" in e for e in r.errors)


def test_partition_type_mismatch_warns(tmp_path: Path) -> None:
    img = tmp_path / "m.img"
    make_image(
        img, total_sectors=200_000, fat_type="FAT16", sectors_per_cluster=8, partition_type=0x0C
    )
    r = analyse(str(img))
    assert any("does not match FAT16" in w for w in r.warnings)


def test_superfloppy_warns(tmp_path: Path) -> None:
    img = tmp_path / "s.img"
    make_image(img, total_sectors=200_000, fat_type="FAT16", sectors_per_cluster=8, mbr=False)
    r = analyse(str(img))
    assert r.layout == "superfloppy" and r.ok


def test_unformatted_image(tmp_path: Path) -> None:
    img = tmp_path / "blank.img"
    img.write_bytes(b"\x00" * 4096)
    r = analyse(str(img))
    assert not r.ok


def test_device_nodes_are_refused() -> None:
    with pytest.raises(ImageError, match="device node"):
        analyse("/dev/null")


# ---- independent cross-checks with dosfstools (skipped when not installed) ----
needs_dosfstools = pytest.mark.skipif(
    not (shutil.which("mkfs.fat") and shutil.which("fsck.fat")), reason="dosfstools not installed"
)


@needs_dosfstools
@pytest.mark.parametrize("fat_type", ["FAT16", "FAT32"])
def test_fixture_generator_passes_fsck(tmp_path: Path, fat_type: str) -> None:
    img = tmp_path / "g.img"
    total = 1_200_000 if fat_type == "FAT32" else 200_000
    make_image(
        img,
        total_sectors=total,
        fat_type=fat_type,
        partition_start=0,
        mbr=False,
        sectors_per_cluster=1 if fat_type == "FAT32" else 8,
    )
    res = subprocess.run(["fsck.fat", "-n", "-v", str(img)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr


@needs_dosfstools
@pytest.mark.parametrize(("fat_bits", "mb"), [(12, 8), (16, 64), (32, 600)])
def test_parser_agrees_with_mkfs(tmp_path: Path, fat_bits: int, mb: int) -> None:
    img = tmp_path / "mk.img"
    with img.open("wb") as f:
        f.truncate(mb * 1024 * 1024)
    subprocess.run(
        ["mkfs.fat", "-F", str(fat_bits), "-n", "DGMX", str(img)],
        check=True,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    r = analyse(str(img))
    assert r.ok, r.errors
    assert r.fat is not None and r.fat.fat_type == f"FAT{fat_bits}"
    assert r.fat.volume_label == "DGMX"


# Internal-memory geometry of the reference unit (EXP-0002/EXP-0003): 25,120-sector LUN,
# FAT12 partition (type 0x01) at LBA 57 to the end of the disk, 16 KiB clusters, written by the
# camera's own formatter (blank OEM name, jump E9 00 00, no boot code).
A402_INTERNAL_SECTORS = 25_120
A402_INTERNAL_START = 57


def test_a402_internal_memory_geometry(tmp_path: Path) -> None:
    img = tmp_path / "internal.img"
    lay = make_image(
        img,
        total_sectors=A402_INTERNAL_SECTORS,
        fat_type="FAT12",
        partition_start=A402_INTERNAL_START,
        sectors_per_cluster=32,
        oem="        ",
        jump=b"\xe9\x00\x00",
    )
    assert lay.fat_sectors == 3 and lay.clusters == 782  # same as observed on the unit
    r = analyse(str(img))
    assert r.ok, r.errors
    assert r.fat is not None and r.fat.fat_type == "FAT12"
    assert r.partitions[0].type_code == 0x01
    assert r.fat.data_area_aligned is True  # 57 + 1 + 2*3 + 32 = 96 = 3 clusters
    assert r.fat.formatter_hint.startswith("embedded camera formatter")
    assert r.dcf["folders"][0]["files"] == 3


def test_formatter_fingerprints(tmp_path: Path) -> None:
    img = tmp_path / "w.img"
    make_image(img, total_sectors=200_000, fat_type="FAT16", sectors_per_cluster=8, oem="MSDOS5.0")
    r = analyse(str(img))
    assert r.fat is not None and r.fat.formatter_hint == "Windows / DOS"


@needs_dosfstools
def test_fat12_fixture_passes_fsck(tmp_path: Path) -> None:
    img = tmp_path / "f12.img"
    make_image(img, total_sectors=25_063, fat_type="FAT12", mbr=False, sectors_per_cluster=32)
    res = subprocess.run(["fsck.fat", "-n", "-v", str(img)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr


@needs_dosfstools
def test_mkfs_fingerprint(tmp_path: Path) -> None:
    img = tmp_path / "mk.img"
    with img.open("wb") as f:
        f.truncate(64 * 1024 * 1024)
    subprocess.run(["mkfs.fat", "-F", "16", str(img)], check=True, capture_output=True)
    r = analyse(str(img))
    assert r.fat is not None and r.fat.formatter_hint == "Linux dosfstools"
