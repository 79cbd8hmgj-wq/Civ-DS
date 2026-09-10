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
| Combat resolution formula | `PARTIAL` (core formula + 11 modifier constants `CODE_PATCHABLE`; RNG/round-loop mechanism now proven, read-only) | `civds combat summarize` / `civds combat patch-manifest --set NAME=VALUE`; odds formula, effective-strength calc, 5 modifier sources, and 6 "overwhelming force" thresholds are patchable; the RNG algorithm (global MSVC-style LCG) and the per-round "army" elimination loop (weighted coin-flip winner, random victim-slot pick, up to 3 sub-units/side) are now fully traced and documented but not exposed as patchable constants - each candidate (RNG constants, round-cap, army-size cap) was evidence-checked and rejected as unsafe to patch in isolation; see `analysis/combat-model.md` and `evidence/re/combat-rng-loop-trace.txt` |
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

## What "combat is PARTIAL/CODE_PATCHABLE" actually means

`analysis/combat-model.md` traces attack/defense from `UnitRecord` into an
effective-strength calculation (`base_stat * cumulative_percent_modifier`)
and a confirmed odds formula
(`attacker_strength * 100 / (attacker_strength + defender_strength + 1)`),
identifies 5 modifier sources (2 tied directly to debug-print strings,
high confidence) and 2 "overwhelming force" auto-resolve threshold checks
(6 constants total, medium confidence), and documents what remains
genuinely unknown (the RNG/dice-roll call and the per-round HP loop -
explicitly left unresolved rather than guessed) rather than claiming the
system is fully solved.

`civds combat summarize <rom> --output combat.json` lists all 11 recovered
constants (name, description, confidence, current value).
`civds combat patch-manifest <rom> --set NAME=VALUE [--set NAME=VALUE ...] --output patch.json`
emits guarded single-byte patches (each constant is a plain unrotated
8-bit ARM immediate; the patch replaces only that byte, verified against
the current value, and the surrounding opcode/registers are provably
untouched - see the byte-level check in the e2e evidence below).

Proven end to end on the real ROM: `fortified-in-city-bonus` was raised
100 -> 150 and both `veteran-tier-bonus` constants 50 -> 75 in one
manifest, applied, rebuilt, and re-parsed - confirming exactly those three
constants changed and the other eight were untouched
(`evidence/re/combat-patch-e2e.json`).

## What "the RNG/round-loop mechanism is now proven" actually means

`evidence/re/combat-rng-loop-trace.txt` traces forward from the two
confirmed odds call sites into the third ("mode 0", actual-resolution)
branch of the same function and recovers, with addresses: the RNG
algorithm (a global linear congruential generator, `state = state *
214013 + 2531011` — the exact Microsoft Visual C/C++ runtime `rand()`
constants, confirmed via 24 xrefs spanning nearly the whole `arm9`
image); the per-round loop (a "combine up to 3 sub-units per side" army
model where each round is a weighted coin flip using the same
attacker/(attacker+defender) probability as the preview odds, the loser's
randomly-picked sub-unit is eliminated, and the loop repeats until one
side's pool is empty — an elimination model, not classic gradual
HP-depletion); a provably-inert 1000-iteration safety cap; and leads
(not fully resolved) on a retreat-style check, a post-battle RNG draw,
and a new connection to the still-unnamed unit-flag group `0x00080000`.

No new patchable constant came out of this pass. Three numeric candidates
(the RNG multiplier/increment, the safety cap, the 3-unit army-size cap)
were each evaluated and rejected for concrete, checked reasons — global
blast radius, gameplay inertness, and coupled buffer/bit-index sizing
respectively — documented in the trace file's "What was deliberately not
exposed" section. This is a deliberate application of the same "safely
patchable" bar the existing 11 constants meet, not a gap in the tracing.

## Prioritized next blockers (highest mod-value first)

1. **City/building/improvement data.** Core to "content mods"; likely a
   fixed-stride table similar in spirit to units/technologies and may be
   locatable with the same anchor-and-stride method used for both. Now the
   top blocker: the RNG/round-loop gap that previously outranked it is
   resolved at the model level (see above), and the remaining combat
   open questions (the `+0x52` field, the retreat helper, the post-battle
   roll, the `0x00080000` flag interaction) are narrower, lower-value
   follow-ups rather than a blocker for trusting unit-stat mods.
2. **Per-civilization gameplay data** (nation name, unique unit/ability, AI
   personality, starting position bias) — the leader-name table found this
   session is a lead: whatever code renders the leader-select screen next
   to a nation name and unique-unit blurb is a promising xref target.
3. **Map/terrain yield tables** — needed for any terrain-balance or
   scenario-design mod.
4. **`STBL` narrative/advisor text format** — lower gameplay priority than
   the above but high "reflavor the whole game" content-mod value once the
   record format is known.
5. **Remaining combat open questions** (`+0x52` field semantics, the
   `0x0209bf7c` retreat/support helper's internals, the post-battle RNG
   draw's consumer, the `0x00080000` flag/combat interaction) — worth a
   future targeted pass but no longer gate trusting the core formula.

Do not decompile rendering/audio/UI/SDK code to chase any of the above; the
goal is the data/behavior surface a mod author needs, not full source
recovery.
