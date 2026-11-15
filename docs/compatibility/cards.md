# Card compatibility matrix

"Stock" means unmodified Samsung firmware. Only results that cite an experiment ID count. Record
the exact card brand, model, capacity, sector count (as the host reports it, not the label),
filesystem and who formatted it.

| Class | Capacity | Stock result | DigimaxOS result | Evidence |
|---|---|---|---|---|
| MMC | ≤ 128 MB | untested | — | — |
| SDSC | 128 / 256 MB | untested | — | — |
| SDSC | 512 MB (guaranteed) | **enumerates over USB; card holds camera-written DCF folder** (capture/playback not yet exercised in a controlled test) | — | EXP-0001 |
| SDSC | 1 GB | untested (SD-01) | — | — |
| SDSC | 2 GB | untested (SD-01) | — | — |
| SDSC (non-standard "4 GB") | 4 GB | not recommended; will not be pursued | — | spec 4.1 |
| SDHC | 4 / 8 / 16 / 32 GB | untested; predicted to fail at initialisation (H-002) | target (SD-02) | — |
| SDXC | ≥ 64 GB | out of P0 scope (SD-03) | — | — |

## Test cards wanted

Use **expendable** cards only. Never use cards holding someone's photos. Preferred: two vendors per
class, such as genuine SanDisk, Kingston, Transcend or Panasonic SDSC 1 GB and 2 GB, and SDHC 4 GB
and 32 GB. Fakes and relabelled cards are common for old capacities. Verify the capacity with a
full host-side write/read pass (for example `f3`) before testing.

See [docs/test-plans/sd-capacity.md](../test-plans/sd-capacity.md) for the procedure.
