# Initial memory map

| Component | Entry address | Load address | Static size |
|---|---:|---:|---:|
| ARM9 | `0x02000800` | `0x02000000` | `0x1907b8` |
| ARM7 | `0x02380000` | `0x02380000` | `0x26dd8` |

Overlay runtime addresses and sizes are enumerated in `analysis/rom/overlay-manifest.json`. These are loader metadata, not inferred gameplay semantics.
