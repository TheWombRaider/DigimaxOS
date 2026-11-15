from pathlib import Path

from digimax import firmware


def _blob() -> bytes:
    b = bytearray(b"\xff" * 65536)
    b[0:3] = b"\x02\x01\x00"  # LJMP 0x0100 (8051 reset vector shape)
    b[0x100:0x110] = bytes([0x12, 0x01, 0x20, 0x22, 0x90, 0x10, 0x00, 0xE0, 0xF0] + [0x22] * 7)
    b[0x1000:0x1020] = b"FW VER 1.02 2005/01/25 MEGA536\x00\x00"
    b[0x2000:0x2010] = "SPCA536".encode("utf-16-le") + b"\x00\x00"
    b[0x3000:0x3004] = b"\xff\xd8\xff\xe0"
    b[0x4000:0x400C] = b"RIFF\x00\x00\x00\x00WAVE"
    b[0x5000:0x6000] = b"\x00" * 4096
    return bytes(b)


def test_inspect_finds_structure(tmp_path: Path) -> None:
    p = tmp_path / "synthetic.bin"
    p.write_bytes(_blob())
    r = firmware.inspect(p)
    assert r.size == 65536
    kinds = {s["type"] for s in r.signatures}
    assert {"jpeg", "riff/wave"} <= kinds
    texts = " ".join(s["text"] for s in r.interesting_strings)
    assert "MEGA536" in texts and "SPCA536" in texts
    assert any(h["isa"] == "8051-family" and h["confidence"] == "heuristic" for h in r.isa_hints)
    assert any(reg.kind == "fill-00" for reg in r.regions)
    assert any("power of two" in n for n in r.notes)


def test_compare_ranges(tmp_path: Path) -> None:
    a = bytearray(_blob())
    b = bytearray(a)
    b[10] ^= 0xFF
    b[12] ^= 0xFF  # merged with the previous range (gap <= 16)
    b[40000] ^= 0x01
    (tmp_path / "a").write_bytes(a)
    (tmp_path / "b").write_bytes(b + b"tail")
    r = firmware.compare(tmp_path / "a", tmp_path / "b")
    assert not r.identical
    assert r.ranges[0] == {"offset": 10, "length": 3}
    assert r.ranges[1] == {"offset": 40000, "length": 1}
    assert r.ranges[-1] == {"offset": 65536, "length": 4}
    assert r.differing_bytes == 3 + 4


def test_compare_identical(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"abc")
    (tmp_path / "b").write_bytes(b"abc")
    assert firmware.compare(tmp_path / "a", tmp_path / "b").identical


def test_entropy_bounds() -> None:
    assert firmware.shannon(b"") == 0
    assert firmware.shannon(b"\x00" * 100) == 0
    assert abs(firmware.shannon(bytes(range(256))) - 8.0) < 1e-9
