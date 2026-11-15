# DigimaxOS
## Open-source firmware research and enhancement platform for vintage Samsung digital cameras

**Version:** 0.1 — founding engineering specification, 2026-11-14  
**Reference device:** Samsung Digimax A402 (owner's functioning camera)  
**Proposed repository:** `DigimaxOS` (public GitHub repository under the owner's authenticated account)  
**Development host:** Ubuntu Linux server, Claude Code, Git and command-line tools  
**Status:** Research and design; no custom firmware or hardware compatibility claims have been validated.

## 1. Mission and execution contract

Act as DigimaxOS's founding principal embedded-systems engineer, firmware reverse engineer, release engineer and open-source maintainer. Develop a collaborative, reproducible enhancement platform for the A402, ultimately extensible to other verified compatible vintage Samsung cameras. Preserve the characteristic CCD images, original shooting modes, owner data and working hardware. Deliver useful host-side tooling even if native firmware modification proves infeasible.

Two flagship product objectives are coequal: (1) reliable support for SDHC media up to 32 GB and (2) a dedicated full manual exposure mode. Build recovery infrastructure first. Do not mistake aspirational features for existing ones. Make evidence-based decisions, publish limitations, and prefer incremental enhancements to a full firmware rewrite. Do not buy hardware, disassemble the original camera, run destructive experiments, upload private artifacts or flash it without specific owner approval. Authorized initial work includes creating the public repository for original project materials, installing reasonable project-local dependencies if permitted, writing tooling, and safe offline research. Pause only at genuinely blocked or risky gates; keep contributing independent safe work.

## 2. Verified starting point and research register

Owner reports camera works and supplied photographs identify it as an A402. The display shows an SD indicator but card capacity, firmware revision and present storage contents are unknown. Baseline the exact unit, not a merely similar model.

| Item | Documented baseline | Confidence / consequence |
|---|---|---|
| Sensor and image | 4 MP effective CCD; 2272 × 1704 maximum stills; service block diagram names Panasonic MN39482 | Manual evidence; verify actual unit |
| Lens and focus | 5.8 mm fixed focal length; normal/macro manual focus switch; nominal f/3.5 or f/7 | No assumption of continuous iris, focus motor or optical zoom |
| Exposure | ISO 100/200/400 or auto; Night mode permits shutter and aperture settings, 8 s–1/1000 s documented | Strong reuse opportunity; actual allowed combinations need bench measurements |
| Storage | 16 MB internal flash storage; SD/MMC; 512 MB guaranteed, not proven hard limit | Test larger standard-capacity cards before changing code |
| Main processor | Service block diagram names SPCA535; schematic section names SPCA536; update file label MEGA536 | Unresolved conflict; do not assume ISA, binary format, usable debug ports or RAM map |
| Memory and control | Service block diagram lists 256 Mbit SDRAM, 16 MB NAND, 93C66 EEPROM; LCD 1.8-inch | Distinguish storage from firmware regions; verify part/revision and memory budget |
| USB | USB 1.1; mass-storage and PictBridge-related functionality documented | No proof of raw readback, remote shutter control, or webcam mode |
| Power | Two AA NiMH cells supported by user manual | Use healthy matched cells for baseline; stable power and voltage sag testing required before any authorized update |
| Upgrade path | Service manual web page 32 (printed p.34) references `MEGA536` copied via camera USB, not card reader | Procedure is not proof of recoverability or unsigned update acceptance |
| Diagnostic mode | Service manual web page 34 (printed p.36) describes factory test and calibration functions | Do not execute calibration or firmware menu functions merely to explore |

Use the following sources, preserve retrieval dates and source IDs in `docs/evidence/sources.yaml`, and record page/section identifiers. Do not redistribute manuals or OEM binaries without permission. The manuals are linked references, not project assets.

- [S1] A402 user manual: https://www.manualslib.com/manual/145735/Samsung-Digimax-A402.html (pp. 30–33, 36, 85–86; shooting and specifications).
- [S2] Night exposure controls: https://www.manualslib.com/manual/145735/Samsung-Digimax-A402.html?page=33 and https://manualsdump.com/en/manuals/samsung-digimax_a402/205766/32
- [S3] Service manual: https://www.manualslib.com/manual/4252216/Samsung-Digimax-A402.html ; block diagram web p.50, DSP web p.52, memory/SD web p.55, update p.32, test mode p.34. Printed page numbering differs. Some detailed pages were inaccessible during initial research; retrieve independently before relying on their contents.
- [S4] SD Association capacity overview: https://www.sdcard.org/developers/sd-standard-overview/capacity-sd-sdhc-sdxc-sduc/
- [S5] SD Association simplified physical-layer specification (v7.10): https://www.sdcard.org/cms/wp-content/themes/sdcard-org/dl.php?f=Part1_Physical_Layer_Simplified_Specification_Ver7.10.pdf ; review initialization, CSD/OCR and addressing; consult current publicly available version as necessary.
- [S6] Linux Sunplus family driver: https://github.com/torvalds/linux/blob/master/drivers/media/usb/gspca/sunplus.c (related hardware only; check exact VID/PID, license and verified protocol).
- [S7] Related but different SoC research: https://github.com/mheistermann/spca-fun (SPCA6350, not an A402 port). Use as methodology inspiration; never assume binary compatibility.
- [S8] CHDK concept/reference: https://chdk.fandom.com/wiki/CHDK ; investigate legal/license boundaries before any code reuse.

No exact A402 custom firmware distribution or original firmware image has been located in initial research. Search reputable archives, historical Samsung support pages, old driver CDs, model aliases (Kenox D402), firmware collections and public repos; preserve provenance and avoid untrusted executables. Do not publish a claim of being the world's first project based on a non-exhaustive search.

## 3. Product requirements and priority

| ID | Priority | Requirement | Acceptance summary |
|---|---|---|---|
| CORE-01 | Gate | Original firmware acquisition and recovery | Verified reproducible backup, per-device calibration preservation and independent restore path before hardware writes |
| CORE-02 | P0 | Device identification and reproducible build/patch | Exactly matching model/board/base hash only; reject unknown inputs |
| SD-01 | P0 | SDSC 1 and 2 GB compatibility investigation | Stock baseline first; no corruption; verified read/write beyond 512 MB where supported |
| SD-02 | P0 | SDHC 4/8/16/32 GB, FAT32 | True full-address-space operation with no aliasing; interoperable files; safe failures |
| EXP-01 | P0 | Standalone M mode | Independent shutter/ISO/aperture selection where combinations are valid; predictable persistence, no automatic override |
| EXP-02 | P0 | Accurate exposure and metadata | Measured output and EXIF agree with effective settings, explicit unsupported combinations |
| RAW-01 | P1 | RAW or RAW+JPEG; host conversion to DNG | Authentic pre-JPEG sensor samples, documented packing/CFA, valid DNG and reproducibility |
| UI-01 | P1 | Histogram, clipping indicators, grid, exposure meter | Display remains legible and capture works within measured CPU/RAM budgets |
| CAP-01 | P1 | Intervalometer, bracketing, self-timer improvements | Cancelable deterministic sequences, low battery/storage handling, no unsafe flash duty cycle |
| USB-01 | P1 | Host CLI and Python SDK; tethered capture if possible | Device safe discovery, bounded operations, transfer integrity; don't advertise capture until proven |
| POWER-01 | P2 | NiMH battery indicator and power improvements | Documented stock calibration preserved; tested voltage thresholds and no brownout regression |
| SD-03 | P2 | SDXC 64 GB+ feasibility | Separately verified SDXC transport, filesystem and full-capacity behavior; no implied support |
| VIDEO-01 | P2 | Improved video options | Preserve stock MJPEG/audio; bounded thermal, throughput and codec feasibility |
| UI-02 | P2 | Custom menus, profiles, boot branding | Reversible, readable at native LCD resolution; no loss of stock modes |
| PORT-01 | P3 | Other camera models | New explicit board/firmware profiles with separate recovery and hardware tests |

P0 is the first functional firmware release scope, not a guarantee. Dependencies can block each independent feature. Preserve JPEG, playback, USB transfer, SD/MMC behavior, internal storage, image numbering, flash, camera controls, settings, and reset functionality. The stock focus switch remains mechanical. Higher resolutions, arbitrary aperture values, unlimited exposure, optical zoom, modern video codecs and Wi-Fi are not promised. Do not invent features that require absent hardware.

## 4. SDHC engineering workstream (flagship)

### 4.1 Baseline and isolate layers

Test known-good expendable 128/256/512 MB SDSC cards (if available), then genuine 1 GB and 2 GB SDSC; identify card type independently on host. Preserve any existing owner card offline. Collect stock recognition, capacity, formatting, image creation, playback, movie, USB transfer and full-volume behavior using test cards only. Record actual sector count and filesystem; do not infer from the label. A 512 MB guarantee is not a proof that larger cards fail. Then assess 4/8/16/32 GB SDHC with scratch media; never approve formatting or writes to owner data. Do not create nonstandard 4 GB SDSC as a recommended solution.

Separate layers: electrical interface and host controller; card initialization; block read/write/erase transport; capacity math; partition parsing; filesystem; DCF/image indexing/free-space accounting. Use schematics, binary analysis, and if authorized non-invasive trace hardware to establish whether the host controller is programmable. A newer filesystem by itself cannot make an SDSC-only transport speak SDHC.

### 4.2 Implementation targets

- Identify existing SD/MMC entry points, register map, controller mode (native SD or SPI), data-transfer engine, card-detect/write-protect behavior, error handling, buffer size and clock configuration. No speculative register writes on the original camera.
- Study CMD0, CMD8, CMD55/ACMD41 with HCS and OCR/CCS negotiation; native versus SPI OCR retrieval, card selection, CSD v1/v2 parsing, default voltage/bus width/rate and correct timeouts. Retain SDSC and existing MMC path. Use conservative default legacy signaling/speed, not UHS or voltage-switch modes without support.
- Normalize all storage operations to logical 512-byte sectors, explicitly convert SDSC byte addressing at the transport boundary and SDHC block addressing at the appropriate boundary. Account for CMD16 behavior, single/multiblock operations, stop/busy handling, CRC and error recovery. Audit DMA lengths and overflows, use suitable wide arithmetic for capacities/byte offsets, validate range before I/O. Preserve erase/write-protect semantics; never implement an automatic destructive fallback.
- Investigate FAT12/16 coexistence and FAT32 BPB, cluster counts, FSInfo, directory operations, free-space math and file size/counter limits. Evaluate an appropriately licensed proven filesystem library only if existing code cannot be adapted; quantify ROM/RAM footprint. Standard SDHC uses FAT32; SDXC normally uses exFAT and is outside P0. A FAT32-formatted SDXC test is distinct from standards-compliant SDXC support.
- Use a host emulator or block-device fixtures with synthetic card responses, malformed structures, card busy/timeout/removal, read-only media, full filesystem and allocation boundary tests. Make no claims that emulation simulates analog behavior or unavailable peripherals.
- If fixed hardware or immutable ROM prevents SDHC, publish exact evidence and revise scope to maximum reliable SDSC, or investigate an optional hardware interface on a donor unit only. Do not advertise unsupported 32 GB support.

### 4.3 Release acceptance (SD)

For every advertised capacity, verify raw logical read/write through the new storage path (not only host-side writes), data beyond 512 MB/1 GB/2 GB and near last usable sector, sector patterns unique to their address, no wrap or aliasing, read-back checksums and independent host-side volume consistency. Use dedicated disposable media and an explicitly approved destructive test stage. Prefer a bounded full-volume write/read diagnostic (where safe) plus independent host verification; distinguish sampling from complete coverage. Repeat on two cards/vendors per supported class where available, record exact card models and revisions, ten cold starts, at least 100 still captures plus playback and a movie, near-full and full-card behavior, card removal only when safe, power interruption tests on sacrificial media/donor after approval, and legacy regressions. Accurate free-space display or explicit sensible cap; no misleading capacity claims. If coverage is incomplete, mark experimental.

## 5. Manual photography workstream (flagship)

### 5.1 Establish stock baseline

Night scene already provides shutter and aperture selection via the +/- controls. Program mode permits ISO and other controls but not independent shutter/aperture. Test exact stock menu options and exposure values, record sample images and EXIF, confirm whether selectable ISO and manual exposure can coexist and whether shutter/aperture persist. Establish repeatable scene with stable lighting, tripod, flash disabled, consistent target and camera position. Measure exposure time using a safe optical test (e.g. timed LED target) and inspect brightness/raw response; EXIF alone is not proof of actual settings.

### 5.2 Native M mode design

- Add a dedicated `M` menu alongside Auto/Program/Scene, or a reversible overlay/shortcut if adding a mode is unsafe. Use existing working shutter/ND/iris and analog gain routines when practical. Enforce only proven shutter steps within 8 s–1/1000 s at first; ISO 100/200/400; two documented f-number states f/3.5 and f/7. Verify the optical mechanism before labeling it a physical diaphragm or assuming continuously variable aperture.
- Allow independent selection when hardware supports it; expose a clear reason for invalid combinations instead of silently changing values. Auto exposure metering should become advisory in M mode, not override the selected settings. Support explicit flash control, original flash timing limits, white balance, metering indicator, image quality and capture confirmation. Exposure compensation in fully manual mode is a meter reference, not a hidden change in exposure.
- Proposed UI: top row M, remaining shots and battery; lower row shutter/aperture/ISO; +/- opens selection; direction and confirmation buttons match original interaction; a reset defaults command; optional grid/histogram later. Do not assume exact framebuffer size, fonts or button event IDs. Create host-side UI mock and navigation state tests before touching firmware.
- Persist validated settings in an isolated or verified compatible configuration area with version/checksum; avoid writes to undocumented EEPROM/calibration offsets. If safe persistence cannot be established, use session settings and document it. Preserve stock mode behavior and factory reset.
- Stretch: A/S priority modes, extended exposure, alternate gain settings, long exposure dark-frame subtraction; only after characterization of CCD clocks, noise, thermal/current and shutter constraints. No unvalidated changes to flash charge control or CCD drive voltages.

### 5.3 Release acceptance (EXP)

Measure supported settings across a documented shutter/ISO/aperture matrix (all exposed combinations or explicitly explain limits), repeat ≥3 captures per representative setting; confirm monotonic expected exposure changes under fixed light and characterize deviations, saturation and noise. Validate shutter timing within an empirically established tolerance, report it; check EXIF fields, flash off/on behavior where safe, button navigation, persistence, repeated capture, low battery handling, and stock modes. Record raw evidence, not a claim of success based on UI labels. Publish sample photographs of non-private targets with stripped personal metadata as appropriate.

## 6. Extended functionality

**RAW/DNG:** identify CCD readout path, image pipeline, pre-ISP or pre-JPEG buffer, effective vs optical-black pixels, packing, bit depth, Bayer/CFA pattern (if applicable), black/white levels, orientation and color calibration. Never rename a JPEG as RAW. Start with documented binary+metadata and host-side DNG export using a suitable licensed library; validate with multiple readers. Native RAW+JPEG is optional subject to RAM, storage speed and safe hooks.

**Photography automation:** interval scheduler using established timer/clock APIs, configurable delay/count, graceful cancellation, deferred capture while busy, low-battery/full-card guard, bracketing using approved exposures, flash off by default for automated bursts; verify no duplicate or skipped frames beyond documented limits.

**Live overlays:** bounded sampled histogram/luminance clipping hints, exposure meter and framing grid; compare performance against stock and make optional. Do not allocate full-frame buffers blindly.

**Host tools:** Linux-first `digimax` command and Python SDK; discover device, inspect model and capability manifest, safely list/download images, inspect EXIF, analyze firmware files, compare dumps, generate reports and optional tethered commands only following verified protocol. Prefer standard mass storage/libgphoto2 where supported. Never blind-fuzz vendor USB requests that could erase or alter camera state. USB 1.1 bottleneck and lack of a confirmed live-view interface limit tethering.

**Video/battery:** measure stock 640×480 MJPEG modes and throughput first; no promise of codec upgrades. Characterize matched NiMH batteries under idle, capture and flash load; keep calibration intact. No battery pack modifications or 3.7 V AA-sized lithium cells.

## 7. Firmware research and safe modification strategy

### Phase A: Evidence & non-invasive reconnaissance

Inventory Ubuntu version, architecture, disk, toolchain, USB availability, existing workloads and GitHub authentication. Set up isolated workspace and least-privilege project-local Python environment. If physical camera is not connected, continue repository, source archive, parser fixtures and design work without reporting hardware results. On owner connection, use `lsusb`, targeted descriptors and observed kernel logs; identify which USB device is the camera; list block storage without mounting writable or auto-formatting. Ask owner before copying original photographs; work with scratch data or privately backed-up media. Document stock firmware version from supported menus if available and record external markings without publishing serials.

Investigate official update file acquisition (MEGA536 label, exact name and extension unknown), historical OEM support and device aliases. Hash and store obtained packages privately, note source and rights, inspect on an isolated host without executing legacy Windows installers. Compare packages across models only as research. Never install another model's firmware. Confirm factory diagnostic mode documentation; observe only with explicit owner permission, no calibration, reset or upgrade action.

### Phase B: Firmware readback and static analysis

Explore supported USB readback/export or vendor documentation first. An update package is not necessarily a complete dump; mass-storage image is not necessarily firmware. Establish what includes bootloader, actual executable, NAND OOB/ECC, bad-block map, settings, EEPROM and camera-specific calibration. Seek reproducible readback; multiple independent reads, SHA-256 and byte comparison, explain naturally varying fields. If inaccessible, plan hardware recovery with qualified electronics support on a donor. Do not open owner's camera automatically: flash capacitor may retain dangerous voltage after battery removal. No probing or soldering until safe servicing procedures, qualified handling, identified chips, voltage levels, bus isolation and approval exist.

Use file signatures, entropy, strings (including multibyte), image/asset extraction, container checksums, update metadata, offsets and candidate instruction patterns; Ghidra, binutils, Python and other appropriate tools. Establish ISA, endianness, memory maps, code/data separation, reset vectors and calling conventions using multiple independent clues. Do not assume 8051 or ARM from chip family alone. Document confidence/provenance for every symbol and hypothesis. Investigate boot path, update checks, storage calls, exposure routines, display event loop, JPEG and DMA buffers. Respect licenses; keep OEM bytes, disassembly exports containing copyrighted code, and device dumps private unless distribution rights established. Derived public notes should describe interfaces and observations independently.

### Phase C: Recovery gate and modification method

Preferred order: host-only tools; stock configuration or supported temporary extension; verified RAM-only payload/loader if a documented safe mechanism exists; minimal binary patch built from user's lawful base; standalone replacement firmware only if justified. Establish independent recovery path from non-booting application, verify on a donor if obtainable. An ordinary updater that requires working firmware is not sufficient. Preserve factory boot region and calibration, validate image bounds and format. Document power requirements and restore procedure. If no defensible recovery path, do not flash owner unit; continue offline or on explicitly approved sacrificial hardware. No blind trial flashing.

First authorized patch should be tiny, observable and reversible (noncritical menu text or version marker, not shutter/SD/bootloader). A matching-base patcher must enforce preimage hashes and expected bytes, size/offset checks, reproducibility, output validation, and explicit dry-run. Do not bypass authentication/verification mechanisms blindly; investigate supported image integrity requirements and document legal/security boundaries. No installer should automatically flash. Recovery, baseline and diagnostic documentation must precede experimental releases.

## 8. Architecture and implementation

Separate device-specific facts from host-independent algorithms. Initial repository may contain scaffolding; never disguise placeholders as working firmware.

```text
DigimaxOS/
  README.md                  # project purpose, status, warnings and start here
  LICENSE                    # proposed MIT for original tooling; see licensing policy
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md
  SECURITY.md
  AGENTS.md
  CLAUDE.md
  ROADMAP.md
  CHANGELOG.md
  docs/
    architecture/            # system, boot, storage, exposure, USB, UI
    evidence/                # source registry, hypotheses, experiment IDs
    hardware/                # independently authored board profiles and pin findings
    compatibility/           # model/board/firmware and card support matrix
    recovery/                # backup, recovery and risk decisions
    development/             # host setup, build, tests and release process
    test-results/            # sanitized hardware evidence
  profiles/a402/             # VID/PID, board and firmware IDs when verified
  tools/digimax/             # Python host tools, firmware inspection & private patching
  tools/dng/                 # optional host converter
  firmware/                  # original code only; no guessed ISA scaffolding as product
    core/                    # storage, exposure, scheduler, UI abstractions
    targets/a402/            # board integration after ISA/ABI discovery
    patches/                 # redistributable definitions only, reviewed provenance
  sim/                      # host-only unit models and virtual block devices
  tests/                    # unit, fixtures, fuzz, integration, hardware manifests
  scripts/                  # environment setup, verification, build and reports
  .github/                  # templates, PR checks, workflows, issue forms
```

Prefer Python 3 with `pyproject.toml`, pytest and a locked dependency approach for host tools; choose target C/assembly/compiler only after ISA and toolchain evidence. Use deterministic builds, pinned tool versions, no opaque scripts, no global changes to the server without consent. Host CLI design (all initially capability-gated): `digimax discover`, `digimax inspect`, `digimax firmware inspect FILE`, `digimax firmware compare A B`, `digimax patch plan BASE PROFILE`, `digimax patch build BASE PROFILE`, `digimax card check IMAGE`, `digimax capture` (unsupported until proven). Output JSON for automation plus human readable summaries. Separate commands that inspect vs write. Default to dry-run/read-only; validate exact model and action. Never use broad raw disk paths without confirming correct target and owner approval. Keep a local private artifact workspace outside Git, with restrictive permissions, for firmware backups and camera images.

## 9. Public GitHub repository and community governance

Create `DigimaxOS` under authenticated owner's GitHub account if available and name unused. Check `gh auth status`, identity and existing repositories. If name collision, do not overwrite; report proposed alternative. Public visibility explicitly requested for original project content only. Proposed description: **Open-source research and firmware enhancements for vintage Samsung Digimax cameras, starting with the A402.** Do not imply affiliation with Samsung. Set repository topics: firmware, reverse-engineering, digital-camera, ccd, embedded, samsung, digimax, sdhc.

Initialize a clean tree, `.gitignore` for binaries/dumps, photos, keys, traces, local device details and tooling secrets; scan staged content before every public push. Propose MIT for new original code, with explicit third-party licensing review; GPL kernel/CHDK code must not be copied into MIT files without respecting applicable license; link or independently implement interfaces when appropriate. If a component requires another license, document and isolate it appropriately. No distribution of OEM firmware, calibration or private images; prefer a local patch generator consuming user-provided base firmware. Review even binary diffs for embedded OEM bytes. Document lawful acquisition and research; seek appropriate advice if uncertain about rights.

Publish README, roadmap, status banner (research-only), safety/install warnings, contribution guide, code of conduct (standard Contributor Covenant if compatible), security reporting instructions and issue/PR templates. Enable Issues; Discussions if available and desired, labels `research`, `sdhc`, `manual-mode`, `firmware`, `hardware`, `recovery`, `good first issue`, `needs reproduction`, `experimental`, `blocked`. Seed transparent, actionable issues with evidence links and test acceptance, not claims of working code. Use GitHub milestones `v0.1 research toolkit`, `v0.2 recovery/first patch`, `v0.3 manual mode`, `v0.4 SDHC`, `v1.0 tested feature release`; manual/SDHC can proceed in parallel and order may change. Require review for firmware and hardware-write changes, record maintainer decisions, avoid pushing secrets. Protect main branch where account supports it; if unavailable document equivalent process. CI should run host unit tests, lint/type-check, reproducible fixture validation, dependency/license checks and safety checks; real camera tests are manual/opt-in with explicit device labels, never in default unattended CI. Public CI must not have access to private firmware or untrusted PR hardware privileges.

Issue templates: feature proposal, compatibility report (redacted VID/PID, model, board, firmware hash, card type/capacity), bug reproduction and experiment report. PRs need evidence, tests, bounded scope, license/provenance, hardware risks, before/after for UI, and whether AI assistance was used. Separate hypotheses from verified functionality. Invite contributors who own spare cameras, know Sunplus hardware, have archived update binaries, or can contribute safe protocol notes; public discussion should not solicit unauthorized OEM redistribution. Use original project branding rather than Samsung logos.

## 10. Verification, evidence and release policy

Each experiment records ID, source revision, camera/profile, firmware hash (if available), instrumentation, power, media, exact commands, expected vs actual results, log hashes, sanitized evidence and whether it was simulated, observed on stock, observed on modified hardware, or blocked. Never publish unverified support. Use `pytest` fixtures for FAT address math, capacity parsing, protocol state machine, invalid binaries, overflow/range checks, mock UI input, EXIF and host parser; property/fuzz tests offline on synthetic data. Regression suite checks stock functionality after authorized modifications. Host tests alone do not prove firmware works.

| Gate | Required evidence | Outcome |
|---|---|---|
| G0 | Public repository sanitized; documentation + host setup; physical device identification if connected | Research release only |
| G1 | Verified firmware identity, acquisition provenance, ISA/container findings; baseline reports | Offline engineering allowed |
| G2 | Verified independent recovery, calibration backup, known-good power, separate approval | First reversible hardware patch may proceed |
| G3 | Manual mode physical acceptance and regressions | Label supported model/base only |
| G4 | SD capacity and full-range integrity acceptance; stock regressions | Label tested card capacities only |
| G5 | Documentation, recovery, repeatability, reviewed release artifacts | Stable label only for individually verified features |

Never enable automatic updates or unreviewed firmware flashing. Publish signed/tagged release metadata or checksums, model and base-hash scope, status and changes, rollback guide, reproducibility inputs, known issues, test provenance and license information. First actual firmware releases marked experimental until sufficient hardware evidence; no binary distribution unless lawful. Incomplete rollback blocks stable firmware publication. Use donor unit for deliberate power-cut or destructive recovery experiments. If no hardware available, publish host tooling and research without flashable output.

## 11. Execution backlog and first session deliverables

Claude must perform actual work rather than merely summarize the specification. In this first session:

1. Inspect server and GitHub authentication; locate repository name conflict; create public repository only if authenticated and authorized by this spec. Create a local Git repo regardless if no remote access; report actual remote URL or blocker. Preserve existing services.
2. Seed original README/roadmap/contribution/safety/agent docs, source registry, compatibility matrix and a structured issue backlog. Add GitHub issue templates and CI as feasible. Publish only after scanning for prohibited material. Create initial issues for firmware acquisition, exact SoC identification, safe readback/recovery, stock Night exposure tests, SDSC compatibility, SDHC transport, FAT32, regression fixtures and USB research.
3. Research original firmware and identify additional source references. Record concrete findings and unresolved contradictions, not fabricated downloads. Archive only locally where permitted.
4. Build functional read-only host CLI for environment checks, optional USB discovery and offline file metadata/hash analysis; include tests using synthetic fixtures. Implement SD addressing/CSD test vectors and exposure-menu acceptance plan as independent offline work. Clearly flag unsupported CLI operations.
5. If camera is connected, enumerate safely, verify target and report actual device descriptors. If disconnected or USB cable unavailable, document the exact user action required; do not stop independent work. No calibration, disassembly, card formatting, update or flash in this session unless separately approved and gates met.
6. Run local tests, inspect Git diff, commit original files in coherent commits, push public-safe content if available, open initial issues if permitted, and provide a concise status report (actual GitHub URL, files created, tests executed with counts, original firmware status, known blockers, highest-value next operation). Record durable checkpoint in `docs/development/status.md` and the GitHub issue tracker. Future sessions resume from evidence and checkpoints rather than repeat discovery.

Do not falsely represent repository creation, actual test counts, firmware availability, ISA determination or SDHC/manual functionality. Do not invent deadlines. Prioritize P0 work and keep independent tasks progressing while blockers remain. Use small reviewable commits, and keep project accessible for non-AI contributors. If lower-confidence assumptions change, update this spec in a tracked decision record.

**Begin execution now. The first release is a research and recovery toolkit, not a firmware image.**
