# Reference ROM map

All values below are confirmed directly from ROM SHA-256 `f19db60920731ba7af2f0e7977870383973fa3a85096aa7d52f9d672e4002c08`.

| Region | ROM offset | Size |
|---|---:|---:|
| ARM9 | `0x4000` | `0x1907b8` |
| ARM9 overlay table | `0x194800` | `0x220` |
| ARM7 | `0x1ccA00` | `0x26dd8` |
| FNT | `0x1f3800` | `0xce1c` |
| FAT | `0x200800` | `0x5608` |
| Banner | `0x206000` | header pointer only |

The FAT contains 2,753 file records. The FNT manifest and 17-overlay manifest are normalized JSON under `analysis/rom/`.
