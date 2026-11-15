# Risk register

Severity and likelihood are rated 1 (low) to 3 (high).

| ID | Risk | Sev | Lik | Mitigation | Owner |
|---|---|---|---|---|---|
| R-01 | A bricked reference camera after a failed or incompatible write | 3 | 2 | Recovery gate G2; donor-first testing; never blind-flash | maintainers |
| R-02 | Loss of per-unit calibration (shutter, bad pixels, battery) | 3 | 2 | Back up the EEPROM and calibration regions separately (R3); never write undocumented offsets | maintainers |
| R-03 | Loss of the owner's photos on the inserted card | 2 | 2 | Never write to the owner's card; image read-only after approval; use scratch cards for tests | operator |
| R-04 | Electric shock from the flash capacitor while opening a camera | 3 | 1 | No disassembly of the owner's unit; donor work by qualified people with a discharge procedure | anyone handling hardware |
| R-05 | A brownout during an update (AA cells sag under load) | 3 | 2 | Measured power requirements (R6); fresh matched cells; abort below a threshold | maintainers |
| R-06 | Redistributing OEM firmware, manuals or drivers (legal) | 2 | 2 | Safety scanner in CI; private workspace; local patch generation from the user's own base image | maintainers |
| R-07 | Personal data leaking (photos, EXIF owner fields, serials, credentials) | 2 | 2 | Safety scanner; redaction defaults in tools; review checklist | everyone |
| R-08 | A false compatibility claim leads users to lose data on large cards | 2 | 2 | Acceptance tests (sd-capacity.md); "experimental" labels; tested capacities only | maintainers |
| R-09 | Host tool wrecks a host disk (wrong device path) | 3 | 1 | Card tools refuse device nodes; future imaging needs an exact target match and confirmation | maintainers |
| R-10 | The SoC turns out to be undocumented or its ISA unidentifiable, which stalls firmware work | 2 | 2 | Deliver host tooling regardless; seek datasheets and donor boards; revise scope publicly | maintainers |
| R-11 | Immutable ROM or fixed-function hardware makes SDHC impossible | 2 | 1 | Publish the evidence; reduce scope to the largest reliable SDSC capacity; optional donor hardware research | maintainers |
| R-12 | Vendor USB requests change camera state | 3 | 1 | No vendor or control requests in tooling; observation only, through standard class drivers | maintainers |
| R-13 | Credentials shared during agent sessions are persisted | 2 | 1 | Agents never store credentials; prefer SSH keys authorised by the owner | maintainers |
