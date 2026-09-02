# Civ Rev DS filesystem inventory

Baseline: USA ROM profile `civrev-usa` (`CIVREV`, game code `YS6E`).

## Result

The extracted filesystem does **not** expose an obvious standalone gameplay-rules database or configuration tree. The strongest current hypothesis is that core gameplay rules and tables are embedded in ARM9 and/or ARM9 overlays, while NitroFS primarily stores presentation, localization, audio, online-support, and graphics resources.

This is an evidence-based triage conclusion, not yet proof that every gameplay value is executable-resident.

## Coverage

- FAT entries in exact ROM profile: **2,753**
- Named NitroFS files represented in the workspace inventory: **2,736**
- ARM9 overlay entries: **17**
- ARM7 overlay entries: **0**
- `2,736 + 17 = 2,753`, accounting for the complete FAT population.

## Named NitroFS composition

Top-level file counts:

| Directory | Files | Decoded bytes | Likely role |
| --- | ---: | ---: | --- |
| `interface` | 1,104 | 3,070,752 | UI graphics/layout assets |
| `structures` | 1,068 | 2,917,584 | structure/city presentation assets |
| `units` | 382 | 1,903,818 | unit presentation assets |
| `leaders` | 68 | 1,168,514 | leader graphics/animation |
| `Localization` | 50 | 3,523,233 | localized names/text |
| `terrain` | 36 | 152,066 | terrain graphics |
| `advisors` | 20 | 307,374 | advisor graphics/animation |
| `title` | 3 | 16,384 | title assets |
| `font` | 2 | 5,576 | font/palette |
| `audio` | 1 | 23,967,584 | Nitro sound archive |
| `dwc` | 1 | 929,892 | Nintendo Wi-Fi/DWC utility |
| root | 1 | 9 | version text |

Total decoded named-file bytes: **37,962,786**.

## Extensions

The dominant extensions are Nintendo graphics-oriented resources:

- `.nbfc`: 743
- `.nbfs`: 743
- `.nbfp`: 739
- `.nanr`: 105
- `.ncer`: 105
- `.ncgr`: 105
- `.nclr`: 105
- `.ntfp`: 18
- `.ntft`: 18

Other files are narrowly scoped:

- `.txt`: 46, concentrated in `Localization/` plus `Version.Txt`
- `.str`: 4 localized string stores (`DEU`, `ESP`, `FRA`, `ITA`)
- `.ini`: `Localization/Text.ini`
- `.bin`: `dwc/utility.bin`
- `.nftr`: `font/Arial14.nftr`
- `.nsbmd`: `units/Combat/Missile.nsbmd`
- `.sdat`: `audio/CIV_sound_data.sdat`

No `.dat`, `.cfg`, `.xml`, `.csv`, `.json`, script tree, database-like directory, or similarly obvious gameplay-rule container appears in the named filesystem inventory.

## Asset scanner status

The generic asset scanner currently recognizes 248 of the 2,736 named files by signature/extension and leaves 2,488 as `unknown`. That large unknown count is not evidence of 2,488 custom gameplay files: most are repeat families of `.nbfc`, `.nbfs`, `.nbfp`, `.nanr`, and `.ncer` presentation assets whose names and directory placement already strongly identify their role.

Known signatures/formats include:

- 105 `NCGR`
- 105 `NCLR`
- 18 `NTFP`
- 18 `NTFT`
- 1 `NSBMD`
- 1 `SDAT`

## RE priority

1. **ARM9** — primary target for gameplay rules, tables, turn logic, economy, combat, technology, AI, and save-state orchestration.
2. **ARM9 overlays 1-16** — identify subsystem ownership using strings and pointer xrefs; overlays 1-13 share one load address and 14-16 share a later load address, indicating mutually exclusive runtime modules/groups.
3. **Localization** — use names/keys as semantic anchors when matching executable references; do not assume localized text files contain mechanics.
4. **NitroFS graphics/audio** — deprioritize for gameplay-rule reconstruction unless a requested mod specifically targets presentation.

## Next evidence pass

Run static ASCII-string extraction plus pointer-xref analysis across ARM9 and every ARM9 overlay, with gameplay-oriented keyword groups. The goal is to assign probable subsystem roles to executable regions before attempting numeric-table discovery or code patching.
