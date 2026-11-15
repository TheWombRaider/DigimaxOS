#!/usr/bin/env python3
"""Pre-publication safety scan (spec section 9: "scan staged content before every public push").

Fails if tracked (or staged, with --staged) files include:
  * binary/media/firmware/dump/archive/key formats (OEM bytes, photos, traces)
  * any file over 1 MiB, or binary content outside the allowlist
  * credential-looking strings (private keys, GitHub/AWS/Slack tokens, passwords)
  * personal e-mail addresses (only noreply/project addresses are allowed)

Usage: python3 scripts/check_public_safety.py [--staged]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BLOCKED_EXT = {
    ".bin",
    ".img",
    ".dd",
    ".raw",
    ".rom",
    ".fw",
    ".hex",
    ".srec",
    ".dump",
    ".nand",
    ".oob",
    ".jpg",
    ".jpeg",
    ".thm",
    ".avi",
    ".wav",
    ".mov",
    ".dng",
    ".tif",
    ".tiff",
    ".cr2",
    ".zip",
    ".cab",
    ".7z",
    ".rar",
    ".gz",
    ".tgz",
    ".xz",
    ".iso",
    ".exe",
    ".dll",
    ".sys",
    ".pdr",
    ".inf",
    ".msi",
    ".ex_",
    ".pdf",  # manuals are linked references, not project assets
    ".pcap",
    ".pcapng",
    ".sal",
    ".vcd",
    ".logicdata",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".kdbx",
}
BINARY_ALLOW = {"assets/icon.svg", "uv.lock"}
MAX_BYTES = 1024 * 1024

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"), "GitHub fine-grained token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    (
        re.compile(r"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"<>]{6,}"),
        "password literal",
    ),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_ALLOW = re.compile(
    r"(?i)(@users\.noreply\.github\.com|noreply@anthropic\.com|@example\.(?:com|org)|"
    r"@contributor-covenant\.org)$"
)
SELF = "scripts/check_public_safety.py"


def tracked(staged: bool) -> list[str]:
    cmd = (
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
        if staged
        else ["git", "ls-files"]
    )
    out = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def scan(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in paths:
        p = ROOT / rel
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in BLOCKED_EXT:
            problems.append(f"{rel}: blocked file type {ext}")
            continue
        size = p.stat().st_size
        if size > MAX_BYTES:
            problems.append(f"{rel}: {size} bytes exceeds {MAX_BYTES} limit")
            continue
        data = p.read_bytes()
        if b"\x00" in data and rel not in BINARY_ALLOW:
            problems.append(f"{rel}: binary content (NUL bytes)")
            continue
        if data[:3] == b"\xff\xd8\xff" or data[:4] in (b"RIFF", b"PK\x03\x04", b"MZ\x90\x00"):
            problems.append(f"{rel}: media/archive/executable magic bytes")
            continue
        if rel == SELF:
            continue
        text = data.decode("utf-8", "replace")
        for pat, what in SECRET_PATTERNS:
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{rel}:{line}: possible {what}")
        for m in EMAIL.finditer(text):
            if not EMAIL_ALLOW.search(m.group()):
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{rel}:{line}: e-mail address {m.group()!r} (use a noreply form)")
    return problems


def main(argv: list[str]) -> int:
    paths = tracked("--staged" in argv)
    problems = scan(paths)
    for pr in problems:
        print(f"UNSAFE: {pr}")
    print(f"scanned {len(paths)} files: {'FAIL' if problems else 'ok'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
