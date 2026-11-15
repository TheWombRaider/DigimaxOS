# firmware/

**Intentionally empty.** No camera-side code exists yet. See
[ADR 0004](../docs/development/decisions/0004-no-firmware-target-code-before-isa.md): target code
starts only after the A402's instruction set, memory map and ABI are established from evidence.

| Directory | Future contents |
|---|---|
| `core/` | Target-independent storage / exposure / scheduler / UI logic, ported from the host reference models in `tools/digimax` |
| `targets/a402/` | Hooks into the stock firmware for an exact base hash, plus board specifics |
| `patches/` | Redistributable patch **definitions** with reviewed provenance. They never contain OEM bytes |
