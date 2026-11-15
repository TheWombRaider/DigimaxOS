"""DigimaxOS host tooling.

Everything in this package is read-only with respect to cameras and storage
media. Commands that would write to a device are deliberately not implemented
and report themselves as unsupported until the project's recovery gates are met
(see docs/recovery/README.md).
"""

__version__ = "0.1.0.dev0"
