"""CRC7 (command/register) and CRC16-CCITT (data block) as used on the SD bus."""

from __future__ import annotations


def crc7(data: bytes) -> int:
    """CRC7 with generator x^7 + x^3 + 1, initial value 0. Returns a 7-bit value."""
    crc = 0
    for byte in data:
        for bit in range(7, -1, -1):
            inbit = (byte >> bit) & 1
            top = (crc >> 6) & 1
            crc = (crc << 1) & 0x7F
            if inbit ^ top:
                crc ^= 0x09
    return crc


def command_frame(index: int, argument: int) -> bytes:
    """Build the 6-byte command token: start/transmission bits, index, argument, CRC7, end bit."""
    if not 0 <= index <= 63:
        raise ValueError(f"command index out of range: {index}")
    if not 0 <= argument <= 0xFFFF_FFFF:
        raise ValueError(f"command argument out of 32-bit range: {argument:#x}")
    head = bytes([0x40 | index]) + argument.to_bytes(4, "big")
    return head + bytes([(crc7(head) << 1) | 1])


def crc16_ccitt(data: bytes) -> int:
    """CRC16-CCITT (polynomial 0x1021, initial value 0) used for SD data blocks."""
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc
