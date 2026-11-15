# ADR 0004: No firmware-target code before ISA and ABI are established

- **Status:** accepted, 2026-11-14

## Context

The SoC identity is contradicted (SPCA535 vs SPCA536) and its CPU core is undocumented in the
sources we have. A related part (SPCA533A) is reported to have an 8032 core, but the spec forbids
inferring the ISA from the chip family.

## Decision

`firmware/` stays empty apart from README files until a later ADR establishes the instruction
set, endianness, memory map and calling convention from several independent clues in an actual
firmware image. Until then, algorithms are developed and tested host-side (`tools/`, `sim/`) in a
form that can be re-expressed in C or assembly later.

## Consequences

No placeholder "firmware" can be mistaken for a product. Progress on the target side is blocked
on firmware acquisition (CORE-01), and that is tracked as the highest-priority issue.
