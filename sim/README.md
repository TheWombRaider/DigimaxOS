# sim/

Host-only models. `digimax_sim.sdcard.SimulatedCard` emulates the **logical** SD/MMC protocol:
CMD8/ACMD41 negotiation, OCR/CSD, byte vs block addressing, busy/timeout, removal and write
protect, with sparse media up to 2 TB. It does not model timing, electrical behaviour or any
camera peripheral. A result that passes here proves nothing about hardware.
