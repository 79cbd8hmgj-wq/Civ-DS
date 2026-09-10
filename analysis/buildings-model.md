# Civilization Revolution DS — city improvement / wonder / city-instance model

Recovered from the supported US ROM (`profiles/civrev-us.json`, sha256
`f19db60920731ba7af2f0e7977870383973fa3a85096aa7d52f9d672e4002c08`), ARM9
component only. All addresses are RAM addresses (`0x02......`); ARM9 loads
at `0x02000000`, so `arm9_relative_offset = ram_address - 0x02000000`.

## Session note (city-effect follow-up pass)

This follow-up session had no ROM file and no disassembler/emulator
available in its environment (the ROM is intentionally never committed to
the repository; a live disassembly session requires a user-supplied ROM,
as in the session that produced the rest of this document). Nothing below
that is new this session was obtained by running the toolkit against the
real ROM - it is entirely static mining of evidence already committed by
the prior session (`evidence/re/*.json`/`*.txt`), specifically
`evidence/re/unit-formation-flags-trace.txt`, whose candidate-context
windows happen to overlap this function's own address range and were not
fully transcribed into this document the first time. See
`evidence/re/city-effect-availability-trace-extended.txt` for the full
stitched trace and `evidence/re/city-yield-ui-leads.json` for concrete
next-session xref targets. No confidence level in this document was
upgraded by this pass except where the extended trace made an already-
documented but not-fully-transcribed detail (the city-turn-count special
case, the spaceship-part cap check) concrete; the city-effect application
path itself remains unresolved, and wonders' field confidence levels are
unchanged (still "strongly supported", not "proven") even though wonders
are now wired into `civds` - see "What was intentionally not promoted"
below for why that is still the right bar.

## Method

Per-instructions, this was targeted structural reconnaissance, not blind
string searching: known building names (`Library`, `Temple`, `Bank`, ...)
were used only to find *candidate regions*; every table boundary, stride,
and field below was then proven by repeated fixed-spacing structure and/or
by finding the executable code that indexes the same base address at the
same stride and reads the same field offsets (`civds`'s existing
`_unique_offset` anchor-then-cross-validate pattern, matching how the
unit/technology/civilization tables were recovered in prior sessions).

## 1. Building/improvement table (proven, `DATA_EDITABLE`)

- **Location**: RAM `0x021778EC` (anchored on the unique string
  `Palace\0`).
- **Stride**: `0xCC` (204 bytes). **Record count**: 24 (indices 0-22 are
  real, buildable improvements; index 23 is a `never`-named sentinel -
  see below).
- Boundary proven two ways: (a) walking the table at the confirmed stride
  lands on 24 consecutive valid-looking records and then stops cleanly
  (unrelated data follows); (b) the runtime availability-check loop
  (`0x02086e34`-`0x02087004`, see section 3) increments its table pointer
  by exactly `0xCC` per iteration and its loop bound is `23` — i.e. the
  game itself only ever considers indices 0-22 buildable, corroborating
  that index 23 is a non-gameplay placeholder.

### Record layout (`civds.buildings.BuildingRecord`)

| Offset | Width | Field | Status |
| ---: | ---: | --- | --- |
| `0x00` | 32 | `name` | proven (display text) |
| `0x20` | 32 | `model_name` | proven present/consistent; not proven read by any executable site this session (treated as an internal asset key by precedent, like units'/technologies' own model-name fields) |
| `0x40` | 1 | `unknown_0x40` | **unresolved** — observed `0xF8` for indices 0-5 (Palace..Library), `0x08` for indices 6-22, `0x00` for the sentinel. No consumer found; left unnamed per instructions ("do not assign semantic names from value patterns alone") |
| `0x41` | 1 | `production_cost_quanta` (`cost = quanta * 5`) | strongly supported: clean, era-scaled round-number costs (20..200) matching the exact `quanta * 5` convention already proven for units; no direct executable read of this byte was located this session, so it is *not* claimed proven by execution — see "Confidence summary" |
| `0x42` | 2 (`int16`) | `prerequisite_technology_id` | **proven** — read at three independent code sites (see section 3); `0` (`never`) means no prerequisite |
| `0x44` | 4 (`uint32`) | `requires_building_mask` | **proven** — bitmask over this same table's own indices; the availability check treats the building unavailable unless the city's built-buildings bitmask has at least one bit in common with this mask (`0` = no requirement). Empirically forms exact "upgrade chain" pairs: Bank requires bit 4 (Market), Cathedral requires bit 3 (Temple), University requires bit 5 (Library) |
| `0x48` | 4 (`uint32`) | `excludes_building_mask` | **proven** — bitmask over this same table's own indices; the availability check makes the building unavailable if the city's built-buildings bitmask has *any* bit in common with this mask. Market excludes bit 10 (Bank), Temple excludes bit 11 (Cathedral), Library excludes bit 12 (University) — the mirror image of the `requires` pairs above, i.e. "no longer offered once its upgrade exists" |
| `0x4C` | up to 128 | `description` | strongly supported (plain NUL-terminated flavor/effect text, e.g. `"+2 food from plains"`, `"4x city gold production"`); not itself proven read by executable code this session (very low risk either way — it is unambiguously display text) |

No maintenance/upkeep field, no separate numeric "city bonus" fields (food
/production/trade/science/culture as discrete numbers), no
population/city-size requirement field, no explicit
civilization/government-restriction field, and no
model/icon/sound-identifier field distinct from `model_name` were found in
this record. Their apparent absence is recorded as such, not guessed at —
see "Unresolved / not found" below.

### The sentinel record (index 23, `never`)

Its `name` field is the literal text `never` (matching the technology
table's own `never`/id-0 sentinel-naming convention). Its remaining bytes
are **not** valid NUL-padded text in the real ROM — e.g. the "model name"
slot contains `63 00 63 00 63 00 FF FF FF FF 00...` rather than a clean
string. Since the availability-check loop bound (`23`) proves the game
itself never inspects this record as a real building, `civds.buildings`
decodes its `name` strictly (needed for the boundary check) but decodes
`model_name`/`description` leniently (falls back to `""` rather than
raising) specifically for this one record - real buildings still fail
closed on invalid text.

## 2. Wonders (distinct table, data-documented, evidence-only this session)

Per-instructions ("investigate wonders separately if the evidence
indicates a distinct table"): wonders are **not** rows in the building
table above. They are a separate table, discovered because its start
address is *exactly* the unit table's own confirmed `Pyramids of
Egypt\0` end-anchor (RAM `0x0217B518` = the unit table's last byte,
already load-bearing in `civds.units`) continuing directly into a second,
larger structure — i.e. the wonder table begins immediately where the
unit table ends, with no gap.

- **Location**: RAM `0x0217B518`. **Stride**: `0x14C` (332 bytes).
  **Record count**: 21, cross-validated by the *same* runtime-availability
  code path (a sibling loop right next to the building-table check, bound
  `0x15` = 21, stride confirmed by `add r8,r8,#0x14c`).
- **Record layout** (data-derived from 21 samples; not exercised through
  `civds` tooling this session — see "What was intentionally not
  promoted" below):
  - `0x00` (32): `name` (e.g. `"Pyramids of Egypt"`)
  - `0x20` (32): reserved/unused (zero in every sample)
  - `0x40` (2, int16): `production_cost_quanta` (`cost = quanta * 5`;
    values 10-150 matching a plausible steep wonder-cost curve)
  - `0x42` (2, int16): unresolved — constant `8` in 20 of 21 records, `4`
    in one (`The World Bank`); no consumer found, no semantic asserted
  - `0x44` (2, int16): `prerequisite_technology_id` — **strongly
    supported** by 9+ exact real-world tech-name matches (Great
    Wall/Masonry, Colossus/Bronze Working, Great Library/Writing, Oxford
    University/University, Leonardo's Workshop/Invention,
    Hollywood/Mass Media, Internet/Networking, Apollo Program/Space
    Flight, Manhattan Project/Atomic Theory); not independently
    cross-referenced against an executable read this session, so kept at
    "strongly supported" rather than "proven"
  - `0x46` (2, int16): `-1` in 19/21 records, `0` in the two "victory"
    wonders (United Nations, The World Bank) — pattern consistent with an
    `obsolete_technology_id`-style sentinel but not independently proven
  - `0x48` (2, int16): unresolved, sparsely nonzero, no pattern found
  - `0x4A` (64): `short_name` (e.g. `"Pyramid"`, `"Colossus"`)
  - `0x8A` (64): `model_name` — mostly the shared string `"Pyramid_anc"`
    across many otherwise-unrelated wonders, i.e. a reused generic
    3D-monument asset, not a per-wonder unique model
  - `0xCA` (~128): `description` (flavor/effect text, e.g. `"trade will
    be doubled in this city."`)
  - `0x14A` (2, int16): unresolved trailing field, small values (0-3)
    observed
  - Several records' `short_name`/`model_name` do not match their
    `name` (e.g. `"The East India Company"` has `short_name` /
    `model_name` = `"AngkorWat"`; `"Shakespeare's Theatre"` has
    `"GlobeTheater"`) — evidence of the record having been renamed from
    an earlier internal design without the internal fields being
    updated. Recorded as an observation, not explained further.
- Full extraction: `evidence/re/wonders.json` (all 21 records, every
  field above, addresses, data-extraction only).

### What was intentionally not promoted

Only `prerequisite_technology_id` and `production_cost_quanta` have
strong (not proven-by-execution) support; several fields are outright
unresolved (`0x42`, `0x46`, `0x48`, `0x14A`), and none of the wonder
table's fields were cross-referenced against an executable read in the
session that recovered this table (the runtime-availability trace in
section 3 confirms the table's *location* and *stride*, not its
individual field semantics beyond what the building table's parallel
structure already implies).

**Update (city-effect follow-up session):** `civds wonders summarize` /
`civds wonders patch-manifest` were added this session, exposing exactly
`name`, `short_name`, `model_name`, `description` (read-only summary
fields, mirroring `BuildingRecord`'s own inclusion of equally
"strongly supported rather than proven" text fields) and, for patching,
only `production_cost` / `prerequisite_technology_id` / `description` —
the same confidence bar (strongly supported, unambiguous display text, or
a clean `quanta * 5` cost convention already proven for buildings/units)
already used to justify the building table's own patch-manifest fields.
`unknown_0x42`, `unknown_0x46` (informally called
`obsolete_technology_id`-shaped in the raw data-extraction evidence, but
**not** independently proven - kept unnamed per this document's own
confidence table), `unknown_0x48`, and `unknown_0x14a` remain unnamed and
unpatchable; `model_name` is excluded from patch-manifest (shared/reused
asset key, e.g. `Pyramid_anc`, same reasoning as the building table's own
`model_name` exclusion) and `short_name` is exposed read-only but also
excluded from patch-manifest pending proof of an independent runtime
consumer. No new executable cross-reference was performed this session -
this is the same "safe to expose by precedent, not newly proven" step,
not an upgrade of any field's confidence level.

## 3. Runtime availability-check function (proven)

Location: `0x02086cb8`-`0x02087050` (arm9), reached via one of five
literal-pool references to the building-table base address. This function
iterates buildings 0-22 (and, in a neighboring loop, wonders 0-20) for a
specific city/player and decides which are currently buildable. For each
building (`sb` = building index, `r6`/table pointer advanced by `0xCC`
per iteration):

```
ldrsh r0, [r6, #0x42]        ; prerequisite_technology_id
cmp   r0, -1
beq   have_no_prereq
ldrsb r1, [r8]                ; r8 = civ/player id
bl    0x20957a0                ; has_researched(civ, tech) -> r0
cmp   r0, #0
beq   not_buildable            ; tech not researched -> unavailable
have_no_prereq:
ldr   r0, [r8, #0x10]         ; r0 = CITY-INSTANCE "already-built buildings" bitmask
mov   r1, #1
tst   r0, r1, lsl sb
bne   not_buildable            ; bit already set -> already built, unavailable
...                             ; (a second, city-turn-count-based special-case skip)
ldr   r1, [r6, #0x48]         ; excludes_building_mask
cmp   r1, #0
beq   no_exclusion
tst   r0, r1                   ; any already-built building in my excludes set?
bne   not_buildable             ; yes -> unavailable
no_exclusion:
ldr   r1, [r6, #0x44]         ; requires_building_mask
cmp   r1, #0
beq   no_requirement
tst   r1, r0                   ; any required building already built?
beq   not_buildable              ; none -> unavailable
no_requirement:
...                             ; buildings 19-22 (the spaceship parts) get an
                                ; additional, unique per-index cap check here
```

This is the single function that answers "can this city build X" for
ordinary buildings, and directly proves the `prerequisite_technology_id`,
`requires_building_mask`, and `excludes_building_mask` fields above (the
exact bit positions line up one-to-one with the building table's own
indices, confirmed against real names: e.g. Bank's `requires` bit 4 is
literally Market's own table index).

A second, related function (`0x02049dfc`-`0x0204a3b8`) walks the same
building table (again `ldrsh r0,[table_ptr,#0x42]`, stride `0xCC`, 23
iterations) as part of an AI build-value evaluation pass triggered right
after a technology is researched — a different consumer of the same
proven `prerequisite_technology_id` field, and additional independent
confirmation of the field's offset and meaning.

A third function (`0x020835d4`-`0x02083644`) performs the "tech just
researched -> notify player of newly available production options" pass
across three tables in one sweep: units (`+0x4A`, already proven),
buildings (`+0x42`), and a small 8-byte-stride array holding two further
`prerequisite_technology_id`-shaped halfwords at `+0x44`/`+0x46` — this
led directly to discovering the wonder table (see section 2), since that
8-byte array's base literal resolved to `0x0217B518`.

## 4. City-effect application path (still not located)

The specific code that, on completing a building, actually *applies* its
effect to city food/production/trade/science/culture/happiness/defense
totals was not found in the session that recovered the building table.
What is proven instead is the *inverse* direction — a per-city "already-
built buildings" bitmask (`city_instance + 0x10`, see section 5) that the
availability-check function reads to decide what's already built and what's
excluded. No building-descriptor field decodes as a scalar "+N food"/"+N
gold"/etc. bonus; every effect observed is a `description` *string* (`"+2
food from plains"`, `"2x city gold production"`, ...), which strongly
suggests the actual numeric effect (if any beyond a simple flat/multiplier
baked into general city-yield code) is computed by a separate, per-effect-
category function keyed off which building bits are set — that function
was not located.

**Update (city-effect follow-up session):** this session's own priority
target was recovering that path. With no ROM/disassembler available (see
"Session note" above), the achievable work was static-evidence mining
rather than fresh disassembly:

- The full extent of the availability-check function that this document's
  section 3 already summarized was re-mined from already-committed
  evidence (`evidence/re/unit-formation-flags-trace.txt`) and stitched
  into `evidence/re/city-effect-availability-trace-extended.txt`. Every
  instruction recovered in `0x02086cb8`-`0x02086f2c` (most, not all, of
  the documented `0x02086cb8`-`0x02087050` range) is a comparison, branch,
  table-stride walk, or a call to a boolean/list-append-shaped helper —
  **no city-yield accumulation instruction was found**. This is a
  meaningful negative result: it makes it very unlikely the effect-
  application logic is colocated with the availability check, narrowing
  (not resolving) the search.
- That same pass made two previously-summarized-but-not-transcribed
  details concrete: the "second, city-turn-count-based special case" is
  `ldrsh r1,[r8,#0x38]; sub r1,r1,#0x64; cmp sb,r1; beq not_buildable`,
  and the "buildings 19-22 (spaceship parts) get an additional cap check"
  reads a per-civilization 8-byte-stride array (index = civ id) and calls
  a generic gate helper (`0x2096db8`) — both still pure availability
  logic, not effect application.
- A static survey of the executable string table
  (`evidence/re/executable-keywords.json`, already committed) surfaced a
  concrete, unexplored lead: a 4-entry consecutive literal-pool cluster
  (`City focus is Gold/Food/Production/Science`, one xref each, 4 bytes
  apart) plus 5 consecutive `+@NUM`-shaped yield-label template strings
  (`Population:`/`Food +`/`Science +`/`Gold +`/`Culture +`) — recorded
  with exact addresses in `evidence/re/city-yield-ui-leads.json`. The
  city-focus cluster in particular is a strong next-session disassembly
  target: city focus selects which yield category a city's production is
  biased toward, so its display/selection function is very likely
  adjacent to (if not part of) the actual per-category yield accumulator.

This remains recorded as the clearest concrete next step for buildings'
*gameplay effect*, distinct from their *availability*, which is fully
proven. It is now a session-item with a precise disassembly starting
point rather than an open-ended search.

## 5. City-instance state (kept separate from the descriptor table)

Per-instructions, city-instance data is documented separately rather than
folded into `BuildingRecord`:

- A city/player-scoped structure, referenced as `r8` in section 3's
  trace, has at least:
  - `+0x10`: 32-bit "already-built buildings" bitmask (bit index = the
    building table's own record index, 0-22)
  - `+0x38`: a halfword used in one further availability special-case
    (`ldrsh r1,[r8,#0x38]; sub r1,r1,#0x64; cmp sb,r1`) — not decoded
    further
  - `+0x24`: a word tested against bit 0 (`ldr r0,[r8,#0x24]; tst r0,#1`)
    gating one further unit-flags bit-2 special case, per the extended
    trace in `evidence/re/city-effect-availability-trace-extended.txt` —
    newly observed this session, **not decoded further** (recorded per
    "promote fields only when encountered naturally"; not claimed to be a
    city-yield field, just logged as an offset on the same base register)
- A separate, `0xBC`-byte-stride (188-byte) array was observed at two
  other xref sites (`0x0203fe08`-, `0x020872cc`-) with a per-record flags
  word (tested against bit `0x400`) and a per-record halfword compared
  against `0xC8` (200) — very likely a per-city record (population/turn
  counters, a growth-related cap), but its base address, exact stride
  role, and relationship (if any) to the `r8` structure above were not
  resolved this session.

No city-instance parser/tooling was added — per-instructions this is
recorded as a lead, not promoted, since its own field catalog is still
largely unresolved.

## Confidence summary

| Confidence | Fields |
| --- | --- |
| **Proven** (executable cross-reference) | building `prerequisite_technology_id`, `requires_building_mask`, `excludes_building_mask`; building/wonder table locations, strides, record counts; the availability-check function and its logic; city-instance `+0x10` built-buildings bitmask |
| **Strongly supported** (clean, convention-consistent data pattern; not independently executable-proven) | building `production_cost_quanta`/`production_cost`, `name`, `model_name`, `description`; wonder `prerequisite_technology_id`, `production_cost_quanta` |
| **Unresolved** (no consumer found, no name assigned) | building `unknown_0x40`; wonder `0x42`, `0x46`, `0x48`, `0x14A`; the `0xBC`-stride city array's exact field catalog; the city-effect application path itself |

## What this unlocks for modding

`civds buildings summarize <rom> --output buildings.json` lists all 24
building/improvement records (name, model name, cost, prerequisite
technology + name, requires/excludes masks, description).
`civds buildings patch-manifest <rom> "<Building>" --production-cost N
--prerequisite-technology-id N --requires-building-mask 0xNN
--excludes-building-mask 0xNN --description "<text>" --output patch.json`
emits guarded, single-field patches (expected-byte checked, one field per
patch entry, no neighboring-field mutation) for exactly the fields proven
or strongly supported above — `model_name` and `unknown_0x40` are
deliberately excluded (asset-key / unresolved, respectively), matching
the same conservative bar the unit/technology/combat capabilities use.

Proven end to end on the real ROM: Bank's production cost was raised
60 -> 100 and its description rewritten, the ROM was rebuilt, and the
rebuilt ROM was re-parsed to confirm exactly those two fields changed,
the record's other fields (prerequisite technology, requires-building
mask) were untouched, and neighboring records (Spice Shop, Cathedral)
were completely unaffected (`evidence/re/building-patch-e2e.json`).

Because `requires_building_mask`/`excludes_building_mask` are bitmasks
over the table's own indices, a mod author can now restructure the entire
building upgrade graph (which buildings gate or obsolete which others)
alongside the already-proven tech-tree editing from `civds technology`,
without a disassembler.

`civds wonders summarize <rom> --output wonders.json` lists all 21 wonder
records (name, short name, model name, cost, prerequisite technology +
resolved name, description).
`civds wonders patch-manifest <rom> "<Wonder>" --production-cost N
--prerequisite-technology-id N --description "<text>" --output patch.json`
emits the same kind of guarded, single-field, expected-byte-checked
patches as the building command, restricted to the fields with strong or
better support (see "What was intentionally not promoted" above for the
reasoning and what is deliberately excluded). This was not proven end to
end on a real ROM this session (no ROM was available); it is validated by
55 passing unit/CLI tests against synthetic ROM fixtures using the exact
byte layout this document already records, following the same test
pattern already proven correct for buildings/units/technology/
civilization/combat.
