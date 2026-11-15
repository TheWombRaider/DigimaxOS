# Recovery gate (CORE-01)

**No write of any kind to a camera** (firmware, EEPROM, settings area or a proprietary update
file) may happen until every item below is satisfied, reviewed and recorded, **and** the device
owner has explicitly approved that specific action.

## Gate checklist

| # | Requirement | Status |
|---|---|---|
| R1 | Original firmware identified: exact version string, and the source of the image or dump with its provenance | ✗ partial: version `M4051S-0525` known (F-033); no image |
| R2 | Complete, reproducible readback of every persistent store: boot ROM/NOR (if present), NAND including spare/OOB and the bad-block map, EEPROM (93C66). At least 3 independent reads must be byte-identical, apart from explained, naturally varying fields. | ✗ partial: the user-area LUN reads back byte-identically (F-050), but the reserved/firmware blocks 809–1023 are **not reachable over USB** (F-047) |
| R3 | Per-device calibration identified and backed up separately (shutter, bad pixels, battery, colour). Restore has been verified. | ✗ |
| R4 | An **independent** recovery path that works when the application firmware is broken: a boot-ROM USB/serial loader, a card-based loader that runs before application code, or an external programmer on a donor board. An ordinary updater that needs working firmware does **not** count. | ✗ unknown |
| R5 | R4 demonstrated end to end on a **donor** unit: break the firmware deliberately, then recover it | ✗ no donor |
| R6 | Power requirements documented: fresh matched cells, the minimum voltage under load, behaviour when power is cut during an update (tested on the donor) | ✗ |
| R7 | Restore procedure written, reviewed and rehearsed | ✗ |
| R8 | Patch tooling enforces preimage hashes, expected bytes, bounds and dry run, and its output is reproducible | ✗ (tooling stubbed: `digimax patch` reports unsupported) |

When R1–R8 are all ✓, gate **G2** is met. The first patch may then be tiny and observable, such as a
version-string change. It must not touch the shutter, the SD driver or the bootloader.

## Readback options under investigation (non-invasive first)

0. **Sunplus USB ISP mode** (F-056, H-014). A 2012 Sunplus ISP tool for the SPCA533/536/538 ships
   `USBISP.BIN` and NAND/ROM ISP images, so this chip family can be programmed over USB. It is the
   leading candidate for R4. Its entry method and whether it can *read* NAND/RSV are unknown.
   **Never** try it on the reference unit before G2. Research it offline, then test on a donor.
   Caution (F-059): on the sibling SPCA533A, ISP is *firmware-driven*, so it would not count as an
   independent path unless the SPCA536 also has a ROM-resident ISP.
0b. **External FlashROM on a donor** (H-016, F-060). If the A402 boots from a parallel NOR
   FlashROM, as the schematic section names and the SPCA533A design suggest, a donor's chip can be
   read and rewritten out of circuit with a standard programmer. That works without any working
   firmware, so it is a true R4 candidate. Prerequisite: the part number from schematic p.55 (#13).

1. **Supported USB paths.** What do mass storage (observed), PictBridge/PTP (untested) and the
   internal-memory LUN (no card inserted) expose? Mass-storage access to internal flash would show
   the user filesystem area, not the firmware.
2. **The official update mechanism.** Understand the `MEGA536` file format and whether the
   bootloader has a counterpart "dump" or a recovery behaviour. **Read only.** Do not supply crafted
   files to the camera.
3. **The factory test mode.** It may show a firmware version. Observing it needs explicit approval,
   and no function may be selected.
4. **Hardware readback on a donor only**, by a qualified person: identify the chips, voltages and
   bus isolation, then read NAND/EEPROM out of circuit or in circuit with the SoC held in reset.
   Discharge the flash capacitor first.

## Decisions

- Blind trial flashing is never acceptable.
- If no defensible recovery path exists, the owner's unit is never flashed. Work continues
  offline, or on explicitly approved sacrificial hardware.
