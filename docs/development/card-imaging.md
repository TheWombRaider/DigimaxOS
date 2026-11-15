# Imaging a card safely (read-only)

`digimax card check` analyses **image files only**. Making an image of a real card is a separate,
deliberate step that needs the owner's approval when the card holds their data.

## Linux (card reader)

1. Insert the card and **do not mount it**. Disable desktop auto-mount for the session if you can.
2. Identify the device precisely: `lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,RM` and check that the size
   and model match the card. **Never guess** `/dev/sdX`.
3. Make the block device read-only before reading: `sudo blockdev --setro /dev/sdX`.
4. Copy it into the private workspace:
   `sudo dd if=/dev/sdX of="$DIGIMAX_PRIVATE/cards/<label>.img" bs=1M status=progress conv=noerror,sync`
5. Hash the image and record it: `sha256sum <label>.img >> "$DIGIMAX_PRIVATE/SHA256SUMS"`.
6. Analyse the copy: `uv run digimax card check "$DIGIMAX_PRIVATE/cards/<label>.img"`.

## Windows

Do not open the raw disk with ad-hoc tools. If you need an image, use a reader on a Linux host as
above. Windows writes a `System Volume Information` folder on mount (F-025). Eject the volume
before removing the card.

## Through the camera

The camera's mass-storage interface shows the card's sectors as the camera presents them. That is
useful later for verifying the *camera's* view of capacity, but reads are slow (USB 1.1, about
1 MB/s). Only do it with explicit approval.
