# Test plan: SD capacity baseline and acceptance (SD-01, SD-02)

## Rules

- Use **dedicated, expendable test cards only.** The owner's card is never formatted or written.
- Verify every card on the host first: confirm it is genuine and its full capacity is real (a full
  write/read pass, for example `f3write`/`f3read`). Record the vendor, model, capacity label,
  **host-reported sector count**, CID manufacturer/OEM ID if a reader exposes it, and the
  purchase source.
- Destructive stages (formatting, full-card writes, power interruption) need explicit approval
  before they start. Power-cut tests are done only on sacrificial media or a donor camera.

## Phase 1: stock baseline (SD-01)

For each card: 128/256/512 MB SDSC if available, then 1 GB and 2 GB SDSC, then one SDHC card
(4–32 GB) to record the failure mode.

| Step | Action | Record |
|---|---|---|
| 1 | Insert the card as the host formatted it (FAT16 for ≤ 2 GB; FAT32 for SDHC) | camera message, LED behaviour |
| 2 | Format in the camera | success/failure; then image the card on the host and run `digimax card check` (partition, FAT type, cluster size, OEM name) |
| 3 | Displayed capacity and shots remaining at each quality setting | whether the numbers are plausible for the capacity |
| 4 | 20 stills, 1 movie, 1 voice memo; play each back | success, errors |
| 5 | USB transfer: copy everything to the host and compare hashes with the files read back through a reader | integrity |
| 6 | Fill the card to full with stills | behaviour at full; does "card full" appear correctly? |
| 7 | Host check: `fsck.fat -n` and `digimax card check` on an image of the full card | consistency, lost clusters |

Expected outcome (hypotheses): ≤ 2 GB SDSC FAT16 may work (H-003). SDHC is rejected at
initialisation (H-002). Both are recorded either way.

## Phase 2: acceptance for DigimaxOS SD support (SD-02, gate G4)

For every advertised capacity class, on **two cards from different vendors**:

| # | Criterion |
|---|---|
| B1 | Raw logical write/read **through the camera's new storage path** (not host-side writes) of address-unique patterns (`pattern_for_sector`). The probes cover sector 0 and 1, every power-of-two boundary, 512 MB, 1, 2, 4, 8, 16 and 32 GiB, and the last two sectors (`boundary_probe_lbas`). |
| B2 | Bounded **full-volume** pattern pass where time allows. Reports must say whether the coverage was full or sampled. |
| B3 | Host verification of the pattern image with `digimax card verify-pattern --full`. Zero aliasing, zero corruption. |
| B4 | FAT32 volume consistency (`fsck.fat -n`) after 100 captures, playback and 1 movie |
| B5 | Data written beyond 512 MB, 1 GB, 2 GB, 4 GiB and near the last cluster reads back correctly on the host |
| B6 | 10 cold starts with the card inserted; card detected every time |
| B7 | Near-full and full-card behaviour; displayed free space is accurate, or a documented cap is shown |
| B8 | Removing the card while idle is handled safely (no hang, no corruption of other cards) |
| B9 | Power interruption during a write is tested on sacrificial media or a donor only, and only after approval. Record the outcome, then check the filesystem. |
| B10 | Legacy regression: 512 MB SDSC and MMC still work exactly as in the Phase 1 baseline; internal memory unaffected |

Any capacity that misses a criterion is labelled **experimental** or left out of the support
list. 32 GB support is never advertised unless every criterion passes at 32 GB.
