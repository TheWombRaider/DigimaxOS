# ADR 0003: Private artifact workspace outside Git

- **Status:** accepted, 2026-11-14

## Decision

All non-public research material lives in `$DIGIMAX_PRIVATE` (default
`~/.local/share/digimaxos-private`), mode 0700, never inside the repository tree. Every file is
recorded in `SHA256SUMS`, and OEM downloads also get a `RETRIEVED_AT` timestamp. Public documents
refer to these files by relative path and hash only. `digimax env check` warns if the directory is
group- or world-accessible.

## Consequences

Evidence can be reproduced and verified by hash without being published. Each contributor keeps
their own workspace. Sharing between maintainers happens privately and only where the rights
allow it.
