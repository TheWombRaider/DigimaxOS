# Hardware test manifests

Hardware tests are **opt-in** (`pytest -m hardware`) and never run in CI. Each needs a manifest
file kept *outside* the repo (in `$DIGIMAX_PRIVATE`) that names the exact device under test:

```toml
device_label = "A402-REF-1"         # human label, not a serial number
profile = "a402"
usb = "0839:003c"
media = "scratch SanDisk 1GB #2"     # never an owner card
approved_by = "<owner handle>"
approved_actions = ["enumerate", "read-descriptors"]   # nothing implicit
```

No hardware tests exist yet.
