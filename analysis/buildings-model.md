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

## Session note 2 (runtime-capable toolkit, still no ROM/emulator)

This session's brief specifically called for melonDS GDB-RSP runtime
experiments via the newly-upgraded toolkit (`NDS-Disassembly-Toolkit` @
`4b08df5a3a070fffafa10d4064f58e89d0c525d1`, which adds
`nds-toolkit runtime ...`). The environment was checked directly rather
than assumed unavailable: no `.nds` ROM exists anywhere on the machine,
and the toolkit's own `nds-toolkit runtime doctor --emulator melonds`
reports `"emulator executable not found"` (melonDS itself is not
installed either). `nds-toolkit runtime probe` fails immediately with
connection-refused. **No runtime experiment was possible this session.**
See `evidence/re/city-effect-runtime-session-2.md` for the full
verification record and a ready-to-execute runtime plan for a future
session that has both a ROM and a melonDS build.

What remained achievable — deeper static mining of already-committed
evidence, the same technique the prior session used — found one new,
speculative lead: a 6-way switch dispatch at `0x020a9c34`, keyed off a
byte at `[some_global_pointer, #6]` with a `-1..4` range (matching the
shape of a `city_focus` enum), sitting roughly `0x780` bytes before the
`City focus is Gold/Food/Production/Science` string cluster
(`evidence/re/city-yield-ui-leads.json`). The same pointer's target also
has five consecutive `ldrsh` reads at `+0x40..+0x48`. This is recorded in
full in `evidence/re/city-effect-runtime-session-2.md` as a **lead only**
— it is explicitly not proven that this is the same city struct already
documented in section 5 below (a different base register is used, and no
evidence bridges the address gap to the string cluster), and the `+0x40`
offsets could just as plausibly belong to a wonder-record reader as to a
city-yield struct. No field names were added or promoted from this lead.

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

## 4. City-effect application path (yield-computation function now located; building/wonder linkage still not proven)

**Update (runtime session 3 - real ROM + real emulator):** a follow-up
session, supplied with the actual ROM and a working DeSmuME GDB-RSP
build, resolved the primary open question this document's "Update
(runtime-capable-toolkit follow-up session)" paragraph below could only
leave as a static lead. See section 6 for the full write-up: the
function that computes a city's per-turn food/production/science/gold/
culture yields is now located and partially disassembled
(`evidence/re/city-yield-recompute-function-trace.txt`), and all five
yield fields in the city-instance struct are proven
(`evidence/re/city-instance-yield-fields.json`). What remains unresolved
is whether/how *building* ownership specifically (as opposed to worked
tiles, inter-city distance, and several still-unidentified per-city
effect-check calls) feeds into this computation - see section 6's
"Unresolved" list.

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

**Update (runtime-capable-toolkit follow-up session):** this session's
brief specifically called for melonDS runtime experiments to resolve the
city-focus lead above. No ROM and no melonDS binary were available in
this environment (verified via the toolkit's own `runtime doctor` check
and a failed `runtime probe`, not assumed — see "Session note 2" above
and `evidence/re/city-effect-runtime-session-2.md`), so no runtime
experiment could be run. Deeper static mining of already-committed
evidence turned up one new, unproven lead: a 6-way switch dispatch at
`0x020a9c34`, keyed off a byte with a `city_focus`-shaped value range,
roughly `0x780` bytes before the city-focus string cluster — full detail,
including the explicit reasons this is *not* claimed proven, in
`evidence/re/city-effect-runtime-session-2.md`. The next-session runtime
plan in that file (breakpoints at `0x020a9c34` and the string-cluster
xrefs, then a baseline/Gold-focus/Production-focus differential trace) is
ready to execute as soon as both a ROM and a melonDS build are available.

This remains recorded as the clearest concrete next step for buildings'
*gameplay effect*, distinct from their *availability*, which is fully
proven. It is now a session-item with a precise disassembly starting
point and a ready-to-run runtime experiment plan, not an open-ended
search.

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

**Update (runtime session 3 - real ROM + real emulator):** the city
struct above is now confirmed reachable live (its runtime address is
data, not fixed - see section 6), and five more of its fields are
**proven**: `+0x06` (`city_focus`), `+0x40`/`+0x42`/`+0x44`/`+0x46`/
`+0x48` (the five current-turn yields). The `0xBC`-stride array
mentioned above was also encountered again this session, live, inside
the yield-recompute function itself, in enough additional context to
upgrade it from "very likely a per-city record" to "strongly supported
to be a fixed 128-entry *all cities in the game* registry" (not the same
struct as the per-city detail struct reached via `[ui_context+0x124]`)
— see section 6.

No city-instance parser/tooling was added — none of the newly-proven
fields are stored in the ROM file (they are pure runtime/heap state, not
static data), so there is nothing here for `civds` (a ROM-file editing
tool) to parse or patch; this section remains documentation/evidence
only, per-instructions.

## 6. City yield recomputation — runtime-proven (real ROM, real emulator)

A follow-up session was supplied with the actual, legally-owned US ROM
and a working DeSmuME (0.9.14, `--enable-gdb-stub`) build for the first
time, unblocking the runtime-analysis work two prior sessions could only
plan for statically. Full narrative, verification commands, and the
complete annotated disassembly are in
`evidence/re/city-effect-runtime-session-2.md` (environment/tooling
notes from the immediately-prior session) and
`evidence/re/city-yield-recompute-function-trace.txt` (this session's
capture); the proven field catalog is in
`evidence/re/city-instance-yield-fields.json`. This section summarizes
the conclusions.

### 6.1 The city-focus lead, confirmed

The static lead from the prior session — a 6-way switch dispatch at
`0x020a9c34`, keyed off a byte with a `city_focus`-shaped `-1..4` value
range, near the already-known `City focus is Gold/Food/Production/
Science` string cluster — was confirmed exactly. A code breakpoint at
that address was hit within one rendered frame of opening the in-game
city panel. The city-instance struct's own `+0x06` byte is **proven**
(by direct write-then-observe: forcing the byte to `1` changed the live
on-screen label to "City focus is Gold" on the next frame) to be
`city_focus` (`0` = Balanced, `1` = Gold; `2`/`3`/`4` are predicted by
UI string order — Food/Production/Science — but not individually
write-tested this session).

### 6.2 The five yield fields, proven by a real differential experiment

A write watchpoint on the resolved city struct's `+0x40` halfword fired
immediately from a *different* function (`~0x02052478`), proving the
city-focus UI code only *displays* cached per-turn totals rather than
computing them. Reading the full struct before and after forcing the
focus to Gold and advancing one real in-game turn (via the actual
"End Turn" control, not a savestate trick) gave two independent,
exact numeric matches between `city+0x40/0x42/0x44/0x46/0x48` and the
in-game city panel's own displayed food-growth/production/science/gold/
culture numbers — see `evidence/re/city-instance-yield-fields.json` for
the full before/after byte dumps. This is now **proven**:

| Offset | Width | Field | Confidence |
| ---: | ---: | --- | --- |
| `0x40` | 2 (int16) | `current_food_yield` | proven (watchpoint-proven write site + 2/2 value matches) |
| `0x42` | 2 (int16) | `current_production_yield` | proven by value correlation (2/2 exact matches; this field's own 2->0 change across the two snapshots is what disambiguated the field order) |
| `0x44` | 2 (int16) | `current_science_yield` | proven by value correlation (2/2 exact matches) |
| `0x46` | 2 (int16) | `current_gold_yield` | proven by value correlation (2/2 exact matches) |
| `0x48` | 2 (int16) | `current_culture_yield` | proven by value correlation (2/2 exact matches) |

These fields are a **persistent, once-per-turn-recomputed cache**, not a
live per-frame recalculation: forcing the focus byte alone (without
ending a turn) did not change the displayed numbers.

### 6.3 The yield-recompute function itself

The write site resolves into a large function observed across RAM
`0x02052180`-`0x02052880` (neither its start/prologue nor its end/
epilogue were reached this session — this is an internal window, not
the full function). Structurally, in address order, it:

1. Runs a chain of calls to two generic per-city "effect check" helpers
   (`0x2096a58`, `0x20957fc` — both already seen in a prior session's
   trace of the building-availability function, reused here with
   different integer IDs) that gate small additive/multiplicative
   bonuses into a running yield accumulator.
2. Applies further multipliers (`x2`, a rounded `x1.5`, a three-way
   `x2`/`x1.5`/`+1` choice) gated by bits of a *separate* per-city-index
   global flags word (not the city struct itself), each gate wrapped in
   another `0x2096a58` call.
3. Iterates a **128-record, `0xBC`-byte-stride array** — the same stride
   already flagged in section 5 as an unresolved lead, now much better
   understood: each record has an owner byte (`+0x00`), a validity/flag
   word (`+0x10`, tested against bit 0), and `x`/`y` coordinates
   (`+0x30`/`+0x32`); the loop skips records that don't pass those
   checks, computes a distance from *this* city's own coordinates, and
   folds a distance-weighted bonus into the yield accumulators. This is
   **strongly supported** (not proven) to be a fixed, 128-entry "every
   city currently in the game" registry, distinct from the per-city
   detail struct — an inter-city proximity bonus (trade routes / culture
   pressure), not a building or tile effect.
4. Iterates a **256-record, `0x54`-byte-stride array** — worked map
   tiles. Reads a terrain-type byte (validated `< 31`), a "currently
   worked" flag (`+0x0C` bit 2), and dispatches on `terrain_type - 31`
   through a 7-way jump table that each accumulate into the same running
   totals using the identical "sum then round-half-up via `lsr #31`/
   `asr #1`" pattern already proven for unit production cost — i.e. this
   is the actual per-worked-tile food/production/trade accumulation.
5. Writes the five yield fields (section 6.2), each immediately followed
   by a conditional add into one of **three separate, 40-byte-stride,
   per-civilization global total arrays** — i.e. **some city yields do
   feed a civilization-wide total**, structurally proven, though which
   specific yields and the exact civ-wide semantics were not decoded
   field-by-field.
6. A further government/city-size-gated block applies a few more
   tile-type bonuses through a *third*, distinct generic per-city helper
   (`0x2095a5c`).
7. Includes a conditional "zero all five yields" branch gated on a flag
   bit of the same per-city-index global flags word from step 2, shaped
   like a civil-disorder/anarchy "this city produces nothing" rule (not
   decoded further).

### 6.4 What this proves and what it still doesn't, for buildings specifically

**Proven:** city yields are computed by one large, turn-boundary routine
that reads worked tiles, nearby friendly cities, and at least three
distinct "does this city/civ have effect X" boolean/counter helper
calls, then writes both per-city and (for some yields) civilization-wide
totals.

**Not proven, not found this session:** no direct reference to the
building descriptor table base (`0x021778EC`) or to the already-proven
`city+0x10` built-buildings bitmask was located anywhere in the ~1.75 KB
of this function captured this session. Building bonuses, if applied
here at all, are not obviously colocated with the worked-tile/inter-city
loops in the observed window. The three generic per-city helpers
(`0x2095a5c`, `0x2096a58`, `0x20957fc`) each take a small integer ID
whose ID-space (technology? building? government? wonder? a unified
"effect flag" space spanning several of these?) was **not decoded** this
session — resolving that is the single highest-value next step for
finally connecting buildings to their gameplay effect (see the modding
capability matrix's prioritized next blockers).

## 7. Library differential experiment — the three helpers ruled out (real ROM, real emulator, session 4)

A follow-up session ran the exact controlled experiment section 6.4 called
for: resolve the city-instance pointer live, set breakpoints on the three
generic per-city helpers (`0x2095a5c`, `0x2096a58`, `0x20957fc`), capture
every call's arguments/return value while the city panel was open (which,
it turns out, re-triggers the yield-recompute call sequence continuously —
no turn advance was needed to observe it), then directly write
`city_instance+0x10` from `0x1` (Palace only) to `0x21` (Palace + Library,
building index 5) as a **clearly-documented runtime-state manipulation**
standing in for playing through the tech research and production queue,
and recaptured the identical sequence. Full data in
`evidence/re/library-yield-helper-diff.json`; full disassembly in
`evidence/re/library-helper-functions-trace.txt`.

**Result: PROVEN negative.** All 23 distinct call sites to the three
helpers inside the yield-recompute function produced byte-identical
arguments and byte-identical return values (all `0x0`/false) before and
after the Library bit was set. Zero behavioral change anywhere.

**Why, now proven by full disassembly:**

- The yield-recompute function's **exact bounds are now proven**:
  `0x0205195c`-`0x02052888` (a real `push {r3-r9,sl,fp,lr}` prologue and
  matching `popeq {...,pc}` epilogue were read directly from live memory).
  The entire function — not just the previously-captured internal window —
  was checked, and it contains **no reference anywhere** to the building
  descriptor table (`0x021778EC`) or to `city+0x10`.
- Full disassembly of all three helpers shows what they actually check:
  `0x2095a5c` reads the **wonder table** (`wonder_table_base(0x0217B518)
  + 0x48`, i.e. the wonder record's own unresolved `unknown_0x48` field,
  already documented as unresolved in the wonders model) for low-range
  arguments, and a separate 8-byte-stride table for high-range arguments.
  `0x20957fc` reads a civilization-scoped word array and calls the
  already-proven `has_researched()` in a neighboring function. `0x2096a58`
  reads three small parallel lookup tables, not fully decoded. **None of
  the three reference buildings at all** — they gate wonder- and
  technology/civilization-shaped effects, not building ownership.

This conclusively answers the primary experiment this session set out to
run: building ownership is **not** wired into city yield computation
through these three helpers, and — since the function's complete bounds
are now known and were checked in full — not through any other path
inside that function either.

**Narrowest unresolved link** (see the full field in
`evidence/re/library-yield-helper-diff.json`): where a completed
building's effect actually gets marked active, if not via a live read of
the raw built-buildings bitmask during yield recompute. The leading
hypothesis, not yet confirmed, is a building-completion event handler
(not yet located) that populates a separate cache — a concrete candidate
being the civilization-scoped array this session found at `0x021c8b98`.
Two concrete next steps: (1) breakpoint writes to `city+0x10` during
*real* Library construction (not a poke) and trace the caller outward to
see what else it writes; (2) repeat this exact experiment after a real
(not simulated) Library completion to see whether real construction
produces a different result than the raw poke did.

### 7.1 Structural finding: the 0xBC-stride array *is* the city-instance struct

While resolving the yield function's true start, this session found that
several "separate per-city-index global" literal-pool values the function
reads all resolve, for this playthrough, to exactly `city_ptr + <a
proven/strongly-supported offset>` (e.g. the literal used for the
`+0x10` read equals `city_ptr + 0x10` exactly; likewise for `+0x03`,
`+0x24`, `+0x44`, `+0x46`). Combined with the proximity-bonus loop's own
array-base literal (section 6.3) resolving to the *same* address, the
simplest consistent explanation is that the "0xBC-stride, 128-record
city array" and the "city_instance" struct documented throughout this
file are **the same array**: `city_ptr == &all_cities[city_index]`. This
is recorded as **strongly supported, not proven** (only tested with a
single-city game this session). See
`evidence/re/city-array-field-catalog.json` for the consolidated field
catalog this implies, and `evidence/re/library-helper-functions-trace.txt`
section 2 for the full evidence.

A new field was also found at `city+0x03` (byte), read at the very start
of the yield-recompute function and used as an index into a 7-way
jump-table dispatch shaped identically to the already-proven worked-tile
terrain-type switch — **strongly supported** to be the city's own
center-tile terrain category, but not value-correlated against a known
terrain type this session, so recorded as `unknown_0x03`.

## Confidence summary

| Confidence | Fields |
| --- | --- |
| **Proven** (executable cross-reference, or live runtime write-test/value-correlation) | building `prerequisite_technology_id`, `requires_building_mask`, `excludes_building_mask`; building/wonder table locations, strides, record counts; the availability-check function and its logic; city-instance `+0x10` built-buildings bitmask; city-instance `+0x06` `city_focus` (runtime write-test); city-instance `+0x40`/`+0x42`/`+0x44`/`+0x46`/`+0x48` current food/production/science/gold/culture yields (runtime differential, two independent exact value matches); the yield-recompute function's exact bounds (`0x0205195c`-`0x02052888`, real prologue/epilogue read live); that the three generic helpers (`0x2095a5c`, `0x2096a58`, `0x20957fc`) do not reference the building table or `city+0x10` anywhere in their disassembled bodies, and that setting the Library bit in `city+0x10` produces zero change in any of their 23 call sites within the yield function (`evidence/re/library-yield-helper-diff.json`) |
| **Strongly supported** (clean, convention-consistent data pattern; not independently executable-proven) | building `production_cost_quanta`/`production_cost`, `name`, `model_name`, `description`; wonder `prerequisite_technology_id`, `production_cost_quanta`; the `0xBC`-stride array being the *same* array as the city-instance struct (`city_ptr == &all_cities[city_index]`), not a separate structure; some yields feeding per-civilization 40-byte-stride global totals; city-instance `+0x03` as a center-tile terrain-category index (7-way jump table, same shape as the proven worked-tile switch) |
| **Unresolved** (no consumer found, no name assigned) | building `unknown_0x40`; wonder `0x42`, `0x46`, `0x48`, `0x14A`; city-instance `+0x00`, `+0x03` (semantic, not existence), `+0x24`, `+0x38`; the ID spaces consumed by the three generic per-city effect-check helpers' own sub-tables (`0x021c87f0`, `0x021c8b98`, `0x021768cc`/`0x0219fad8`/`0x0219faf0`/`0x02182980`); **where building-completion effects actually get applied**, now that the three named helpers and the entire yield-recompute function are ruled out |

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
reasoning and what is deliberately excluded).

**Update (real-ROM session):** proven end to end on the real ROM. The
Pyramids of Egypt's production cost was raised 150 -> 200 and its
description rewritten, applied to an extracted workspace, rebuilt, and
the rebuilt ROM re-parsed to confirm exactly those two fields changed,
the record's other fields (prerequisite technology, short name, model
name) were untouched, and neighboring records (The Great Wall, Hanging
Gardens of Babylon) were completely unaffected
(`evidence/re/wonder-patch-e2e.json`) — closing the "Wonders real-ROM
proof" item from the modding capability matrix's prioritized blockers.
