# Development setup

## Host

Linux is the primary platform (developed on Ubuntu 24.04, x86_64). macOS and WSL should work for
everything except `digimax discover`, which reads Linux sysfs. On Windows, use the collection
script instead.

```bash
# Python >= 3.11 and uv (https://docs.astral.sh/uv/) are the only prerequisites
git clone https://github.com/TheWombRaider/DigimaxOS && cd DigimaxOS
scripts/setup-dev.sh        # uv sync --locked; creates the private workspace (mode 0700)
scripts/verify.sh           # ruff, ruff format --check, mypy --strict, pytest, safety scan
uv run digimax env check
```

Optional tools that `env check` looks for: `lsusb`, `udevadm`, `dosfstools` (`fsck.fat`/`mkfs.fat`,
which enables the FAT cross-validation tests), `binwalk`, Ghidra (`analyzeHeadless`),
`binutils`, `p7zip`, `exiftool`. None is installed system-wide by project scripts. Install them
yourself if you want them.

## Private artifact workspace

Firmware images, OEM downloads, device reports, card images and photos **never** go into the Git
tree. Keep them in:

```text
$DIGIMAX_PRIVATE   (default ~/.local/share/digimaxos-private, mode 0700)
  oem/       OEM downloads, with RETRIEVED_AT and SHA256SUMS
  camera/    raw observations (EXP-*)
  dumps/     firmware readbacks (when they exist)
  refs/      third-party reference copies for offline reading (e.g. GPL drivers)
  SHA256SUMS
```

`scripts/check_public_safety.py` and `.gitignore` block common artifact types, but the
responsibility stays with you.

## Camera on another machine (Windows)

The reference camera is attached to a Windows PC. On that PC:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Get-DigimaxInfo.ps1 > digimax-report.json
```

Copy the JSON to the Linux host, then run `uv run digimax discover --import digimax-report.json`.
The script reads only PnP and storage metadata. It never opens files or the raw disk.

## Running tests

```bash
uv run pytest -q                 # all host tests (no hardware)
uv run pytest -m hardware        # opt-in device tests (none yet); never in CI
```

See [card-imaging.md](card-imaging.md) before creating any image of a real card.
