# Civilization Revolution DS — combat resolution model

Recovered from the supported US ROM (`profiles/civrev-us.json`, sha256
`f19db60920731ba7af2f0e7977870383973fa3a85096aa7d52f9d672e4002c08`), ARM9
component only. All addresses below are ARM9-relative file offsets unless
marked as a RAM address (`0x02......`); the ARM9 image loads at
`0x02000000` in this ROM, so `ram_address = 0x02000000 + file_offset`.

Goal of this note: make unit-stat mods (`civds units patch-manifest
--attack/--defense/...`) trustworthy by showing exactly how those bytes
flow into a battle outcome, and expose the pieces that are safely
patchable as `civds combat` constants. This is **not** a full
decompilation of the combat function — the function that contains this
logic (entry `0x0008b6d8`/RAM `0x020897ec`, well over 3000 instructions)
also handles unit/tile placement bookkeeping, AI advisories, and on-screen
combat-preview positioning inline; only the parts that determine the
authoritative gameplay outcome were traced.

## What is proven

### 1. Effective strength = base stat x cumulative percent modifier

Inside the shared modifier/odds section of the function (arm9
`0x0008b6fc`-`0x0008bcd0`, RAM `0x0208b6fc`-`0x0208bcd0`), the attacker's
running bonus percentage lives at `[sp,#0xc8]` and the defender's at
`[sp,#0xc4]`, seeded by the function's caller (not located within this
session's tracing budget - see "Open questions" below) and then adjusted
by every modifier in the table below via plain `add`/`sub #imm`
instructions. At `0x0008bc7c`-`0x0008bca8`:

```
ldr r1, [sp, #0x44]      ; r1 = attacker base stat
ldr r0, [sp, #0xc8]      ; r0 = attacker bonus percent
mul r2, r1, r0           ; r2 = base * percent
ldr r1, [sp, #0x40]      ; r1 = defender base stat
ldr r0, [sp, #0xc4]      ; r0 = defender bonus percent
str r2, [sp, #0x44]      ; attacker "effective strength" = base * percent
mul r0, r1, r0
str r0, [sp, #0x40]      ; defender "effective strength" = base * percent
```

A modifier source contributes to the bonus percentage as `+N` or `-N`
(N in whole percent, baseline ~100 = unmodified); the product `base *
percent` is what both the odds formula and the auto-resolve thresholds
consume. There is no separate `/100` step in this code — the ratio in the
odds formula below is scale-invariant with respect to a missing common
divisor, so this does not affect the result.

### 2. Combat-odds formula (confirmed, two call sites)

At `0x0208bc7c` onward there is a 3-way switch on a "mode" parameter
(`[sp,#0x34]`, values 0/1/2):

- **mode 1** (`0x0208bd08`-, pure preview/evaluation, no state mutated):
  ```
  r0 = attacker_effective_strength * 100
  r1 = attacker_effective_strength + defender_effective_strength + 1
  return divide(r0, r1)     ; via callee 0x02159728
  ```
  i.e. **`odds_percent_for_attacker = attacker_strength * 100 /
  (attacker_strength + defender_strength + 1)`** — the classic
  Civilization-family combat-odds formula. This is the value shown by any
  in-game combat-odds preview and very likely the same value AI code
  reads when deciding whether to attack.
- **mode 2**: computes an extra side value (`bl 0x020c5a40`, a
  screen-position/coordinate helper — UI, not gameplay) and then the exact
  same odds formula.
- **mode 0** (default): does not return odds; it continues into
  the state-mutating path (auto-resolve checks, flags, advisor triggers)
  described below. This is the actual "resolve this combat" path, as
  opposed to modes 1/2 which only *evaluate* it.

### 3. Modifier sources (each a plain, guardable ARM immediate)

| Modifier | Effect | Confidence | Evidence |
| --- | --- | ---: | --- |
| Veteran/condition tier | attacker and defender: own tier byte clamped to `[-1, 0, 1, 1]` relative to a middle value, multiplied by **50**, added to that side's percent | high | debug string `Veteran +50%` (RAM `0x02181f88`) loads exactly at the code site that computes this delta for the case the raw tier byte is 2 |
| Fortified in city | defender: **+100%** when the per-tile/per-civ state array (0x5400-stride, tested via the unit's civilization id) has bit `0x10` set | high | debug string `Fortified +100%` (RAM `0x02181f98`) loads at this exact `add r0, r0, #0x64` site |
| Actively fortifying | defender: **+50%** when the same state array has both bit `0x4` and bit `0x8` set | high | debug string `Fortifying +50%` (RAM `0x02181fac`) loads at this exact `add r0, r0, #0x32` site |
| Zone-of-control-style directional check | attacker: **-50%**, shared by four separate directional bit-combination tests (`tst`/`orr` combos on facing-indexed tile data) | medium | code path and magnitude confirmed; no debug string ties this to a specific rule name, so it is documented by mechanism, not asserted to be "ZOC" |
| Category conditional halving | attacker or defender: bonus percent is **halved** (`asr #1`) when the opposing unit's descriptor flags do **not** have bit `0x2`/`0x4`/`0x6` set (naval/air-related); seen at three separate sites | medium | mechanism and bit tests confirmed via the confirmed unit-descriptor `+0x50` flags lookup; the gameplay rule this implements (e.g. a land/ship interaction) is not independently confirmed |
| Terrain | both sides: an arbitrary signed percent returned by a dedicated helper (attacker: `0x0209d008`, defender: `0x0209d36c`) is added directly to that side's percent | medium | call sites and the "add the return value to my percent" pattern are confirmed; the terrain-to-percent mapping inside those two helpers was not traced (that is unrelated per-tile terrain-type code, out of scope for this pass) |
| Support/"army" bonus | both sides: a per-slot helper (`0x0209bf7c`, called with slot index `0..2`, i.e. up to 3 supporting units) contributes an amount subtracted from the effective-strength product (`sub` after `mul`+divide); likely the "Combine three units into an army for increased defense" mechanic named in an advisor tip string | medium | mechanism and the 3-slot loop are confirmed; the exact per-slot value formula inside `0x0209bf7c` was not traced |

### 4. "Overwhelming force" auto-resolve thresholds (two independent checks)

Both are plain `moveq`/`movne #imm` pairs multiplying the *other* side's
effective strength, then comparing:

- Primary (`0x0208c850`-`0x0208c884`): multiplier is **2** if a
  per-civilization difficulty byte equals the global difficulty value,
  else **3**; if `attacker_strength <= defender_strength * multiplier`
  the auto-resolve branch is skipped (`ble 0x0208c960`).
- Secondary (`0x0208bf44`-`0x0208bfd8`, earlier in the same function):
  multiplier is **6**/**4** or **10**/**7** depending on two similar
  civilization-id comparisons, feeding an analogous `cmp`/`blt` gate that
  sets a flag consumed at `0x0208bfe4`.

Both are documented (`confidence: medium`) because the exact downstream
effect of "the check passed" — full-strength auto-win, skip the RNG round
entirely, or something narrower — was not traced past the flag being set;
what is proven is that these six specific numbers are live comparison
thresholds inside the authoritative resolution path (mode 0), not display
code.

### 5. RNG and per-round resolution loop (confirmed)

Full trace: `evidence/re/combat-rng-loop-trace.txt`. Summary:

- **RNG algorithm**: a global (game-wide, not combat-local) linear
  congruential generator at RAM `0x02192304`, `state = state * 214013 +
  2531011` — the exact constant pair used by the classic Microsoft
  Visual C/C++ runtime `rand()`. Confirmed via 24 separate literal-pool
  references to the state struct spanning nearly the whole first 100KB of
  `arm9` (`0x02000d60`-`0x02099f78`), so this is shared by many systems,
  not just combat.
- **Per-round loop** (mode 0 only — modes 1/2 return the preview odds and
  never reach this code): up to 3 sub-units can be combined per side (the
  "army" mechanic). Each round draws the RNG once to decide the winner —
  a weighted coin flip over `[0, attacker_strength + defender_strength)`
  compared against `attacker_strength`, i.e. exactly the same probability
  as the confirmed preview-odds formula — then draws again (retrying on
  an already-eliminated pick) to choose which of the losing side's
  remaining sub-units is eliminated. The loser's picked sub-unit is
  permanently removed from its side's pool; the loop repeats until one
  side's pool is empty (at most 5 rounds with a 3-unit cap). This is an
  **elimination model** (remove a whole sub-unit per round), not the
  classic PC-Civilization gradual-HP-depletion model.
- A 1000-iteration safety cap exists but is provably unreachable in real
  play given the 3-unit cap.
- A retreat-style check (reusing the still-unresolved `0x0209bf7c` helper,
  mode `0x10`) and a post-battle RNG draw (result not consumed before
  return, likely read by the caller — a plausible veteran-promotion roll)
  were both located but not fully decoded.
- A new lead surfaced for the old unresolved unit-flag group `0x00080000`
  (Spy/Caravan/Great People): the winning side's flags are tested for
  this bit right before final cleanup, with extra handling when set.

## Open questions (explicitly unresolved — not guessed)

- **Where the base attack/defense bytes are read.** No `ldrsb`
  `[reg, #0x40]`/`[reg, #0x41]` (the confirmed unit-descriptor attack/
  defense offsets) exists anywhere inside this function's ~3000-instruction
  body. The base stat therefore almost certainly arrives as a parameter
  from this function's caller, which was not located in this session
  (arm9-mode and thumb-mode caller scans both came back empty against the
  raw byte stream, meaning the call site is likely context-dependent code
  the flat scan can't resolve without proper CFG/xref analysis). Everything
  downstream of "attacker/defender base stat" is proven; the exact hop
  from "read attack byte from `UnitRecord`" to "call this function" is not.
- **Exact semantics of terrain (`0x0209d008`/`0x0209d36c`) and
  support-bonus (`0x0209bf7c`) helpers.** Confirmed to contribute to the
  formula (and, per the RNG-loop trace, the same `0x0209bf7c` helper also
  gates a retreat-style check); their internal per-tile-type / per-slot /
  per-mode value tables were not decoded.
- **The unit-instance halfword field at `+0x52`.** Read and preserved
  across each round of the loop but never itself recomputed in the traced
  code — its purpose is unresolved.
- **The post-battle RNG draw's consumer** (likely veteran promotion; not
  confirmed) and **the `0x00080000` flag interaction** noted above.

## What this unlocks for modding

`civds combat summarize` / `civds combat patch-manifest --set
NAME=VALUE` expose the 5 high/medium-confidence flat percentage
modifiers and the 6 overwhelm-threshold multipliers as guarded, named,
single-byte patches (see `src/civds/combat.py` and
`evidence/re/combat-patch-e2e.json` for a proven real-ROM round trip). A
mod author can now, for example, halve the city-defense bonus or double
the veteran bonus without a disassembler.

The RNG/round-loop mechanism is now proven (see above and
`evidence/re/combat-rng-loop-trace.txt`), which is what this note set out
to establish — unit-stat edits can now be trusted to flow through a known
formula and a known win-determination roll. No *additional* patchable
constant was added from this new material: the multiplier/increment are
a global, game-wide RNG (24 xrefs across the binary, not combat-scoped —
patching it would affect far more than combat); the 1000-round safety cap
is provably inert in real play; and the 3-unit army-size cap is coupled
to fixed-size local buffers and bit-index assumptions elsewhere in the
same function, so changing it without re-auditing those dependents risks
stack corruption. Each was deliberately left unpatched rather than force
a capability that does not clear the same "safely patchable" bar the
existing 11 constants meet — see `evidence/re/combat-rng-loop-trace.txt`
("What was deliberately not exposed") for the full reasoning on each.
