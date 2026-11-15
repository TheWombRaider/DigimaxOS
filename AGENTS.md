# Instructions for AI coding agents

This file applies to any automated agent (Claude Code, Codex, Copilot and others) working in this
repository. Human contributors may find it a useful summary too.

## Authority

- The engineering specification is
  [`docs/development/spec/DigimaxOS-Project-Specification.md`](docs/development/spec/DigimaxOS-Project-Specification.md).
  Changes to its assumptions are recorded as ADRs in `docs/development/decisions/`.
- Current state and the next actions are in
  [`docs/development/status.md`](docs/development/status.md). **Read it first, and update it at
  the end of every working session.**

## Hard rules

1. Never flash, update, format, partition or write to a camera or its storage. Never run its
   factory test or calibration menus. Never send USB control or vendor requests to it. All of
   these require gate G2 plus explicit, per-action approval from the device owner. Earlier approval
   does not carry over to a new action.
2. Never commit OEM firmware, update files, manuals, drivers, calibration data, device dumps, photos,
   serial numbers, credentials or personal data. Keep them in the private workspace
   (`$DIGIMAX_PRIVATE`, default `~/.local/share/digimaxos-private`, mode 0700). Run
   `python3 scripts/check_public_safety.py --staged` before every commit.
3. Never present a hypothesis, simulator result or placeholder as verified functionality. Update
   `docs/evidence/findings.md` with a confidence level and source/experiment ID.
4. Do not copy GPL code into MIT files. Do not reuse CHDK code without a license review.
5. Never store credentials in files, memory or commit messages. Ask the owner every time.
6. Do not buy hardware, disassemble the owner's camera or make global changes to the host without
   consent.

## Working conventions

- Run `scripts/verify.sh` before committing. CI runs the same checks.
- The runtime CLI is limited to the standard library. Any new runtime dependency needs an ADR.
- Commands that inspect and commands that write stay separate. Default to dry-run and read-only.
- New experiments get the next `EXP-NNNN` ID in `docs/evidence/experiments/`. New sources get the
  next `S` ID in `sources.yaml`, with a retrieval date.
- Keep commits small and coherent. File GitHub issues for follow-up work instead of leaving TODOs in
  code.
