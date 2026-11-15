# Experiments

Each experiment gets a sequential ID (`EXP-NNNN`) and its own file here. Copy the template below.
Private raw outputs, such as full reports, images and traces, stay in the private workspace. Only
their SHA-256 hashes are recorded here.

| ID | Title | Kind | Status |
|---|---|---|---|
| [EXP-0001](EXP-0001-usb-enumeration.md) | USB enumeration of the reference unit | observed on stock | done |

## Template

```markdown
# EXP-NNNN: <title>

- **Date:** YYYY-MM-DD
- **Operator:** <GitHub handle>
- **Kind:** simulated | observed on stock | observed on modified hardware | blocked
- **Source revision:** <git commit of DigimaxOS used>
- **Device / profile:** <profile id>, unit label (no serial numbers)
- **Firmware hash:** <sha256 or "unknown">
- **Instrumentation:** <host OS, tools and versions, meters, analysers>
- **Power:** <cell type, measured voltage at start/end>
- **Media:** <card make/model/capacity/class - scratch or owner card?>
- **Approval:** <who approved, for which exact actions>

## Purpose
## Procedure (exact commands)
## Expected result
## Actual result
## Raw evidence
| File (private) | SHA-256 |
## Interpretation and confidence
## Follow-ups
```
