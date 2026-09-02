# Civilization Revolution DS unit descriptor recovery

This note records the current evidence boundary for the 38-entry unit descriptor table in the supported US ROM. It deliberately separates code-proven semantics from unresolved metadata so later modding code does not turn membership guesses into API contracts.

## Table layout

- anchor: `Settlers\0`
- record count: `38`
- record size: `0x94` (148 bytes)
- next-table anchor: `Pyramids of Egypt\0`

Recovered fields used by `civds.units.UnitRecord`:

| Offset | Width | Interpretation | Status |
| ---: | ---: | --- | --- |
| `0x00` | `0x20` | unit display/internal name slot | confirmed |
| `0x20` | `0x20` | primary model name slot | confirmed |
| `0x40` | 1 | attack | confirmed |
| `0x41` | 1 | defense | confirmed |
| `0x42` | 1 | movement | confirmed |
| `0x43` | 1 | fuel/turn limit used by air units | confirmed |
| `0x44` | 1 | production-cost quanta (`value * 5`) | confirmed |
| `0x45` | 1 | unknown | unresolved; no provenance-backed unit-table consumer recovered |
| `0x46` | 1 | unknown | unresolved; no provenance-backed unit-table consumer recovered |
| `0x47` | 1 | unknown | unresolved; no provenance-backed unit-table consumer recovered |
| `0x48` | 1 | formation mask | confirmed |
| `0x49` | 1 | reserved in supported ROM | all 38 records are zero; no semantic use established |
| `0x4A` | 2 | unlock technology id | confirmed |
| `0x4C` | 2 | obsolete technology id 1 | confirmed |
| `0x4E` | 2 | obsolete technology id 2 | confirmed |
| `0x50` | 4 | unit flags | confirmed container; individual bits below |
| `0x54` | `0x20` | alternate model A | confirmed |
| `0x74` | `0x20` | alternate model B | confirmed |

## Code-proven flag semantics

| Mask | Public interpretation | Supporting membership / behavior |
| ---: | --- | --- |
| `0x00000001` | `is_settler` | Settlers and FSettler; direct runtime consumers |
| `0x00000002` | `is_naval` | Submarine, Galley, Galleon, Cruiser, Battleship; direct domain checks |
| `0x00000004` | `is_air` | Bomber, Fighter, ICBM; direct domain checks |
| `0x00000010` | `can_carry_units` | Galley/Galleon/Cruiser/Battleship; code maintains dependent unit-instance carrier references through `+0x26` |
| `0x00000080` | `is_great_person` | seven Great Person records; multiple direct runtime consumers |
| `0x00008000` | `is_great_general` | Great General only; direct runtime consumers |
| `0x00010000` | `is_spy` | Spy only; multiple direct runtime consumers |
| `0x00020000` | `is_icbm` | ICBM only; direct runtime consumer |

These names are exposed by `UnitRecord` and serialized by `build_unit_summary()`.

## Unresolved flag bits

The following bits are preserved in the raw `flags` word but are intentionally not given gameplay-semantic API names yet.

| Mask | Supported-ROM membership | Current evidence boundary |
| ---: | --- | --- |
| `0x00000008` | unnamed unit 3, Archer, Riflemen, Modern Infantry, Tank, Catapult, Cannon, Artillery, Submarine, Galleon, Cruiser, Battleship, Space Station, Bomber, Fighter | broad combat/ranged-looking membership is insufficient to name the bit |
| `0x00000020` | Naval Crew, unnamed units 3-5, Warrior, Militia, Legion, Archer, Riflemen, Horsemen, Knights, Phalanx, Catapult | no precise semantic established |
| `0x00000040` | Horsemen, Tank, ICBM, Spy, Caravan, Great People | no precise semantic established |
| `0x00000100` | Warrior, Legion, Archer | membership-only subcategory in current provenance-backed scan |
| `0x00000200` | Horsemen, Knights | membership-only subcategory in current provenance-backed scan |
| `0x00000400` | Archer | membership-only singleton; identity/capability not code-proven |
| `0x00000800` | Riflemen | membership-only singleton; identity/capability not code-proven |
| `0x00002000` | Fighter | one provenance-backed descriptor test exists, but its branch does not yet distinguish a Fighter identity marker from a narrower air-combat capability |
| `0x00004000` | unnamed units 3-5 | no precise semantic established |
| `0x00040000` | unnamed units 3-5, Warrior, Legion, Archer, Riflemen, Modern Infantry, Horsemen, Knights, Tank, Phalanx | no precise semantic established |
| `0x00080000` | Spy, Caravan, seven Great People | seven provenance-backed runtime tests exist; code repeatedly treats this group specially, but the evidence does not justify a precise public name |
| `0x00100000` | Caravan | membership-only; corrected high-byte tracing found no provenance-backed direct descriptor-flag test |
| `0x00200000` | Catapult, Cannon, Artillery | membership-only; corrected high-byte tracing found no provenance-backed direct descriptor-flag test |

### High-byte tracing note

A follow-up scan checked whether `0x00100000` and `0x00200000` were being read through byte/halfword accesses at descriptor `+0x52`. Apparent `0x10`/`0x20` hits were traced to unrelated unit-instance `+0x52` fields or register reuse rather than the descriptor flag word. They therefore do not count as semantic proof for these descriptor bits.

## Evidence files

The committed reverse-engineering evidence remains under `evidence/re/`, especially:

- `unit-flag-bit-survey.json`
- `unit-flag-runtime-uses.json`
- `unit-flag-function-context.txt`
- `unit-flag-0x10-trace.txt`
- `unit-next-flags-trace.txt`
- `unit-high-byte-flag-trace.txt`
- `unit-unresolved-trace.txt`
- `unit-formation-flags-trace.txt`
- `units.json`

The supported-ROM evidence should be regenerated whenever a newly proven semantic is added to the public unit summary.
