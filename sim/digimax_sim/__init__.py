"""Host-only simulation models for DigimaxOS.

These models emulate *logical protocol behaviour* (command/response, address
semantics, busy/timeout/removal). They do not model analog signalling, timing,
power or any camera peripheral, and passing tests here proves nothing about real
hardware (spec section 4.2).
"""
