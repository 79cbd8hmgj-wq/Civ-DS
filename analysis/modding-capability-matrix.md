# Civilization Revolution DS — modding capability matrix

Goal: make broad gameplay/content mods possible without opening a
disassembler for routine changes. This tracks, per major game system,
whether that goal is met today.

Status legend:

- `DATA_EDITABLE` — a tested parser/writer + guarded patch-manifest CLI
  exists; a mod author edits values and runs `civds`, no disassembler needed.
- `CODE_PATCHABLE` — the behavior lives in code, but the exact instructions
  to change are identified precisely enough that `civds source-patch` (or a
  guarded `binary_replace`) can alter it safely.
- `PARTIAL` — some fields/behavior in the system are `DATA_EDITABLE` /
  `CODE_PATCHABLE`; others are still unknown. Documented per system below.
- `BLOCKED` — no reverse engineering has established the table/format/code
  path yet. A mod author would have to reverse engineer it themselves.

| System | Status | Tooling |
| --- | --- | --- |
| Unit stats (attack/defense/movement/fuel/cost/tech links) | `DATA_EDITABLE` | `civds units summarize` / `civds units patch-manifest` |
| Unit categories (settler/naval/air/great-person/great-general/spy/ICBM/carrier) | `DATA_EDITABLE` (read) | exposed as booleans in `civds units summarize`; not independently patchable (part of the `flags` word, see below) |
| Unit `flags` word bits not yet named (13 of 21 observed bits) | `PARTIAL` | raw `flags` value is visible and technically patchable as a whole word; individual bits are not exposed as named, independently-guarded patch fields yet (see "Remaining RE targets") |
| Unit descriptor bytes `+0x45`/`+0x47` | `BLOCKED` | present in `civds units summarize` output (`unknown_0x45`, `unknown_0x47`) for visibility, but no runtime consumer recovered, so no gameplay guarantee attaches to editing them |
| Unit descriptor byte `+0x46` | `PARTIAL` | confirmed runtime consumer (a 3-way unit-rendering position mode), but the exact visual effect of each of the 3 modes is undecoded, so it is visible but not exposed as a guarded patch field |
| Technology names | `DATA_EDITABLE` | `civds technology summarize` / `civds technology patch-manifest` (`--effect`, patchable text) |
| Technology prerequisites (tech tree edges) | `DATA_EDITABLE` | `civds technology patch-manifest --prerequisite-0/1/2`; proven end to end (patch -> rebuild -> re-parse), see `evidence/re/technology-patch-e2e.json` |
| Technology effect/flavor text | `DATA_EDITABLE` | `civds technology patch-manifest --effect` (only 6 of 47 technologies use it today - government unlocks - but the field itself is a plain fixed-length ASCII slot, safe to (re)populate on any technology) |
| Technology `category_mask` | `PARTIAL` | parsed and visible in `civds technology summarize`; values cluster into a small bitset (`-1,1,2,3,4,5,7,8,15`) but no runtime consumer has been traced yet, so it is not exposed as a patch field |
| Technology `reserved_0x28` | `BLOCKED` | always `-1` across all 48 records in the supported ROM; no consumer found |
| Civilization leader names (16 civs) | `DATA_EDITABLE` | `civds civilization summarize` / `civds civilization patch-manifest --new-leader-name` |
| Civilization nation names, starting bonuses, unique units, AI personality | `BLOCKED` | only the leader-name pointer table was located; no companion "nation name" or per-civilization gameplay-parameter table has been found yet |
| Map / terrain (tile types, resources, terrain yields) | `BLOCKED` | not yet located |
| Cities / buildings / improvements | `BLOCKED` | not yet located |
| Wonders | `BLOCKED` | not yet located; likely lives in a table adjacent to or sharing code with technologies (several wonders are technology-adjacent in classic Civ design) but this has not been checked |
| Combat resolution formula | `BLOCKED` | unit `attack`/`defense`/`movement` values are `DATA_EDITABLE`, but the code that turns those numbers (plus terrain/fortification/etc.) into a combat outcome has not been traced, so interactions between edited stats and hidden multipliers are unverified |
| Diplomacy / AI decision-making | `BLOCKED` | not yet located |
| Victory conditions | `BLOCKED` | not yet located |
| Narrative/advisor/tooltip text (`Localization/str_*.STR`, `STBL`-tagged) | `BLOCKED` | file format identified (magic `STBL`) and confirmed to hold flavor/advisor dialogue text (e.g. French "Guerriers", "Colons" advisor lines), but the record format has not been parsed; note the US ROM ships no `str_ENG.STR`, so the base-language text for this content is elsewhere (likely inline in `arm9`/overlays, consistent with the unit/technology name fields already being plain embedded ASCII) |
| Rendering / audio / UI / SDK internals | *(not prioritized)* | explicitly out of scope unless a specific mod requires it |

## What "the technology tree is DATA_EDITABLE" actually means

As of this session, a mod author can, using only `civds` (no disassembler):

1. `civds technology summarize <rom> --output technologies.json` to see all
   48 technologies (names, prerequisite ids/names, category mask, effect
   text).
2. `civds technology patch-manifest <rom> "<Technology>" --prerequisite-0/1/2 <id> --effect "<text>" --output patch.json`
   to build a fail-closed patch (every edit records and checks the *current*
   bytes, so a stale or wrong-version ROM refuses to apply rather than
   silently corrupting the table).
3. `civds patch <workspace> patch.json` then `civds rebuild <rom> <workspace> <output.nds>`.

This was proven end to end on the real, hash-verified ROM: `Code of Laws`'s
second prerequisite was moved from `Alphabet` to `Pottery` and its effect
text rewritten, the ROM was rebuilt, and the rebuilt ROM was re-parsed to
confirm both changes landed and nothing else moved
(`evidence/re/technology-patch-e2e.json`).

Because prerequisites are a fully general 48x48 directed graph (three edges
per technology, `-1` = none), this is enough to build an entirely custom
tech tree — reorder eras, remove gates, add new dependencies among the
existing 47 technologies — without any binary-format knowledge.

## What "civilization leader names are DATA_EDITABLE" actually means

`civds civilization summarize <rom> --output civilizations.json` lists all
16 civilizations (index, leader name) by walking a recovered pointer table
(anchored on the unique `Caesar\0` string, civilization 0) into a packed,
variable-length ASCII string pool shared with other game text.
`civds civilization patch-manifest <rom> "<current leader name>" --new-leader-name "<new name>"`
emits a fail-closed patch: it computes the exact byte capacity of that
leader's slot (the gap up to whatever string follows it in the shared pool)
and refuses to build a patch for a name that would not fit, rather than
silently overflowing into the next string.

Proven end to end on the real ROM: civilization 9's leader was renamed
`Napoleon` -> `Louis`, the ROM was rebuilt, and the rebuilt ROM was
re-parsed to confirm exactly that one name changed and all 15 others (and
their table order/pointers) were untouched
(`evidence/re/civilization-patch-e2e.json`).

Only the leader *name* is exposed today - no gameplay-parameter table
(starting techs, unique unit, AI trait, civilization color) has been
located for civilizations yet, so renaming is a real but narrow slice of
"civilization modding" (see the `BLOCKED` row above).

## Prioritized next blockers (highest mod-value first)

1. **Combat resolution formula.** Unit stats are editable, but nobody can
   safely balance a mod without knowing what else (terrain, fortification,
   veteran status, randomness bounds) participates in combat. This is the
   highest-value remaining `BLOCKED` item because it gates confidence in
   every unit-stat edit already shipped.
2. **City/building/improvement data.** Core to "content mods"; likely a
   fixed-stride table similar in spirit to units/technologies and may be
   locatable with the same anchor-and-stride method used for both.
3. **Per-civilization gameplay data** (nation name, unique unit/ability, AI
   personality, starting position bias) — the leader-name table found this
   session is a lead: whatever code renders the leader-select screen next
   to a nation name and unique-unit blurb is a promising xref target.
4. **Map/terrain yield tables** — needed for any terrain-balance or
   scenario-design mod.
5. **`STBL` narrative/advisor text format** — lower gameplay priority than
   the above but high "reflavor the whole game" content-mod value once the
   record format is known.

Do not decompile rendering/audio/UI/SDK code to chase any of the above; the
goal is the data/behavior surface a mod author needs, not full source
recovery.
