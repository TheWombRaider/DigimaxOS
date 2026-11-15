# Architecture overview

DigimaxOS keeps three things apart: **device facts** (profiles, evidence), **host-independent
algorithms** (storage math, exposure model, UI state machines) and **target integration** (code that
runs on the camera). Target integration cannot start until the CPU architecture and ABI are
established (see [status](../development/status.md)).

```text
                      ┌──────────────────────────── host (Linux-first) ─────────────────────────────┐
 profiles/a402  ───►  │ digimax CLI ── discover / inspect / firmware / card / sd / exposure        │
 evidence/            │      │                                                                      │
                      │      ├── digimax.sd        CRC, OCR/CSD, addressing, init reference model  │
                      │      ├── digimax.fat       MBR/FAT/DCF image analysis                       │
                      │      ├── digimax.exposure  capability model, M-mode UI state machine        │
                      │      └── digimax.firmware  offline analysis (hash/entropy/strings/ISA hints)│
                      │ sim/digimax_sim  simulated SD/MMC card (logical protocol only)              │
                      └──────────────────────────────────────────────────────────────────────────────┘
                                   │ algorithms are ported/re-expressed, not copied, once the ISA is known
                                   ▼
                      ┌─────────────────────── camera (future, gated) ───────────────────────────────┐
                      │ firmware/core        storage / exposure / scheduler / UI abstractions       │
                      │ firmware/targets/a402  hooks into stock firmware (patches against an exact  │
                      │                        base hash), board specifics                          │
                      │ firmware/patches     redistributable patch *definitions* (no OEM bytes)     │
                      └──────────────────────────────────────────────────────────────────────────────┘
```

## Modification strategy (spec 7C, in order of preference)

1. **Host-only tools.** No camera change at all (current work).
2. **Stock configuration** or a supported temporary extension, such as a card-resident file the
   stock firmware already reads.
3. **A RAM-only payload or loader**, if a documented, safe entry mechanism exists. Nothing is
   persisted.
4. **A minimal binary patch** built locally from the owner's lawfully obtained base image. Its
   preimage hashes are checked, and the patch definition contains no OEM bytes.
5. **Standalone replacement firmware**, only if justified by evidence. Not expected.

## Design rules

- A single transport boundary converts logical 512-byte sectors to card addresses
  ([storage.md](storage.md)).
- The user's exposure choices are never overridden. The meter is advisory ([exposure.md](exposure.md)).
- Every write path defaults to dry-run, checks that the target matches exactly and needs separate
  approval.
- Unknowns stay explicitly unknown in profiles. Tools refuse to depend on unverified fields.
