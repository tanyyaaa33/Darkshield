"""Write a minimal RGBA PNG shield icon for the Chrome extension (stdlib only)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_shield_png(path: Path, size: int = 128) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w = h = size
    # Simple shield silhouette: green fill (#00FF88) on transparent background
    pixels = bytearray(w * h * 4)
    cx, cy = w / 2, h * 0.42
    for y in range(h):
        for x in range(w):
            nx = (x - cx) / (w * 0.42)
            ny = (y - cy) / (h * 0.55)
            inside = ny >= abs(nx) * 0.9 - 0.15 and ny <= 1.05
            if inside:
                i = (y * w + x) * 4
                pixels[i : i + 4] = bytes([0, 255, 136, 230])
    raw = b"".join(b"\x00" + pixels[y * w * 4 : (y + 1) * w * 4] for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    write_shield_png(root / "extension" / "icons" / "icon.png", 128)
    print("Wrote", root / "extension" / "icons" / "icon.png")
