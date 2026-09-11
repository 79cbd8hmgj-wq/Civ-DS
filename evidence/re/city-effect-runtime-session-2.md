# City-effect follow-up session 2 — runtime environment + new static lead

## Runtime environment: verified unavailable, not assumed

This session was explicitly scoped around the upgraded toolkit's melonDS
GDB-RSP runtime layer (`nds-toolkit runtime ...`). Before doing anything
else, the environment was checked directly rather than assumed:

- No `.nds` ROM file exists anywhere on this machine (broad filesystem
  search by extension and by file size in the plausible DS-ROM range,
  20 MB-200 MB, turned up nothing outside test fixtures/build artifacts).
- No `roms/`, `work/`, `.ndsre`, or `.ndstrace` directory/file exists in
  this repository or elsewhere on the machine — there is no prior
  extracted workspace to reuse.
- The toolkit's own `nds-toolkit runtime doctor --emulator melonds` check
  (its intended environment-readiness diagnostic) reports:

  ```json
  {
    "checks": [{"name": "emulator", "passed": false, "detail": "emulator executable not found"}],
    "emulator": "melonds",
    "passed": false
  }
  ```

- `nds-toolkit runtime probe --cpu arm9 --timeout 3` fails immediately
  with `cannot connect to runtime debugger at 127.0.0.1:3333` (connection
  refused, not a timeout) — confirming nothing is listening on the
  expected GDB-RSP port, consistent with melonDS not being installed.

**Conclusion**: no runtime experiment (probe/snapshot/read-memory/
run-until/step/trace capture/diff) could be performed this session. This
is a verified environment gap (no ROM *and* no melonDS binary), not an
assumption, and not the same issue as a prior session's branch mismatch.
The recommended differential-trace experiment (baseline vs Gold-focus vs
Production-focus city state) is fully specified and ready to run the
moment a future session has both a ROM and a melonDS build available -
see "Next-session runtime plan" below.

## What was still achievable: deeper static mining

With no ROM, no new disassembly could be produced (the toolkit's static
analyzer also needs the ROM's extracted `arm9.bin`). What remained
achievable was the same technique the prior follow-up session used:
re-mining already-committed evidence
(`evidence/re/unit-formation-flags-trace.txt`,
`evidence/re/unit-unresolved-trace.txt`) for anything relevant to the
city-focus/yield lead that wasn't previously written up, since those
files' candidate-context windows incidentally cover a wide, scattered
swath of `arm9` addresses well beyond their own original unit-flag
purpose.

### Ruled out: `evidence/re/unit-field-usage.json` near `0x020aa3b4`-`0x020aa3ea`

Several `metadata_accesses` entries in that file cite addresses in this
range (e.g. `0x020a9c24`... `0x020aa71e`... `0x020aa9fe`), but their
`context` blocks are internally inconsistent (alternating
`b #0x20a....`/short instructions at *every other* halfword, a classic
disassembler-misalignment artifact when a Thumb-mode linear scanner
crosses a **data** region such as a literal pool). This is exactly the
region already known to hold literal-pool pointers to the "City focus is
..." strings (`evidence/re/city-yield-ui-leads.json`), so this is
consistent with — not contradicting — the existing lead. Recorded so a
future session does not re-investigate this specific file/range expecting
real code.

### New lead: a 6-way switch keyed off a byte at `[global_city_ptr, #6]`

`evidence/re/unit-formation-flags-trace.txt` also contains real,
consistently-aligned ARM-mode disassembly (not Thumb, not misaligned)
covering `0x020a9b80`-`0x020a9c38`, roughly `0x780` bytes *before* the
city-focus string cluster's own xref addresses (`0x020aa3bc`-`0x020aa3c8`).
No evidence bridges the gap between `0x020a9c38` and `0x020aa3bc` (every
`.txt` evidence file was checked; nothing else falls in that span), so
this is **not proven to be the same function** as the one holding the
city-focus string literal pool — it is a structurally-motivated candidate
for it, nothing more.

```
0x020a9b9c: ldr      r3, [sb, #0x124]        ; r3 = *(global_ptr + 0x124)
0x020a9ba0: ldr      r0, [pc, #0x7f4]        ; r0 = literal A (table base)
0x020a9ba4: ldrsb    r2, [r3]                ; r2 = signed byte at r3+0
0x020a9ba8: ldr      r1, [pc, #0x7f0]        ; r1 = literal B (table base)
0x020a9bac: ldr      r0, [r0]                ; r0 = *literal A
0x020a9bb0: ldr      r2, [r1, r2, lsl #2]    ; r2 = table_B[r2] (word-indexed)
0x020a9bb8: ldrsh    r4, [r3, #0x40]
0x020a9bbc: ldrsh    r5, [r3, #0x42]
0x020a9bc0: ldrsh    r6, [r3, #0x44]
0x020a9bc4: ldrsh    r7, [r3, #0x46]
0x020a9bc8: ldrsh    r8, [r3, #0x48]
0x020a9bcc: bl       #0x2023a5c              ; distinct from, but near, the
                                              ; already-seen 0x2023acc
                                              ; list/UI-append helper
    ... (stack-argument setup, an RNG/percent-shaped helper call at
         0x2002878, unrelated-looking) ...
0x020a9c24: ldr      r0, [sb, #0x124]        ; same global pointer again
0x020a9c28: ldrsb    r0, [r0, #6]            ; r0 = signed byte at +6
0x020a9c2c: add      r0, r0, #1              ; r0 += 1  (so raw range is -1..4)
0x020a9c30: cmp      r0, #5
0x020a9c34: addls    pc, pc, r0, lsl #2      ; 6-way (0..5) jump table dispatch
0x020a9c38: b        #0x20a9cc8              ; first case body
```

**Why this is worth flagging** (structural pattern match, NOT proof):

- `[sb, #0x124]` is read twice, dereferenced both times as a pointer to a
  small record — consistent with "pointer to the currently-viewed city"
  held in a fixed global slot (the same *kind* of access pattern already
  proven for the `city/player` struct in the building-availability
  function, though that function reaches its struct through `r8`, a
  *different* physical register from `sb`/r9 here — **these two structs
  are not proven to be the same struct**, only plausibly related).
- The byte at `+6`, used as `(byte + 1)` in a bound-5 jump table, has
  exactly the value shape of a `city_focus` enum: 4 named UI strings
  already exist (`City focus is Gold/Food/Production/Science`), and a
  range of `-1..4` (6 raw values) comfortably covers "no focus set" plus
  4-5 focus modes — a very natural switch shape for a "render the city
  info panel differently per focus" routine, i.e. exactly the kind of
  function the prior lead predicted should exist near the string cluster.
- The five consecutive `ldrsh` reads at `+0x40`/`+0x42`/`+0x44`/`+0x46`/
  `+0x48` are read from the *same* base pointer, immediately before that
  switch. If this base pointer is the city struct, these would be five
  new city-instance fields at exactly the offsets this document should
  care most about (candidate base-yield slots). **This is speculative
  pattern-matching, not a proven or even strongly-supported semantic
  claim** — the same offset shape also matches the *wonder* record's own
  `production_cost_quanta`/`unknown_0x42`/`prerequisite_technology_id`/
  `unknown_0x46`/`unknown_0x48` layout, so this could equally be a
  function that reads a *wonder* record (e.g. a "wonder info" panel), not
  a city struct at all. Both readings remain open.

No offset here is added to `analysis/buildings-model.md`'s city-instance
field table as a named field — per the project's confidence rules, this
stays a documented **lead**, not a promoted `unknown_0xNN` city field,
until a live session confirms what `[sb, #0x124]` actually points to.

## Next-session runtime plan (ready to execute once ROM + melonDS exist)

1. `nds-toolkit runtime doctor --emulator melonds --rom <rom>` to confirm
   readiness, then launch melonDS with its GDB stub enabled and JIT
   disabled (per the toolkit's own documented requirement) against the
   supported Civ Rev ROM.
2. `nds-toolkit runtime probe --cpu arm9` to confirm the RSP connection.
3. Set a code breakpoint at `0x020a9c34` (the jump-table dispatch found
   above) and one at whichever address is confirmed to host the actual
   `ldr`/`bl` that loads the `City focus is Gold` string pointer (from
   `evidence/re/city-yield-ui-leads.json`'s xref list,
   `0x020aa3bc`-`0x020aa3c8`).
4. Reach the city screen in-game, open the focus-change UI, and use
   `nds-toolkit runtime run-until` / `step` (bounded step counts, not a
   long synchronous resume) to confirm or refute:
   - whether `0x020a9c34`'s dispatch and the `0x020aa3bc` string loads
     execute in the same call (same function, or caller/callee), and
   - what `[sb, #0x124]` actually resolves to (dump the pointer with
     `runtime read-memory`, then dump the struct's own bytes and compare
     against the known `city_instance+0x10`/`+0x24`/`+0x38` structure
     already proven in the availability-check function, to test whether
     they are the same struct).
5. Follow the differential-trace recipe from the task brief (baseline vs
   Gold focus vs Production focus, `nds-toolkit runtime trace capture` +
   `runtime diff`) to find which memory addresses change when focus
   changes — those addresses are the strongest direct candidates for
   city yield/output state.

This plan is unchanged in substance from the prior session's lead; the
only addition this session made is a more specific starting instruction
address (`0x020a9c34`) instead of only the string cluster.
