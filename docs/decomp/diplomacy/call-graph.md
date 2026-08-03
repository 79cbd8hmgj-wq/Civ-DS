# Diplomacy call graph

Confirmed direct ARM branches:

- attack/action callers `0x0205f108`, `0x020601c4`, `0x020606fc`, `0x02060778` → validation/UI dispatcher `sub_02063238`
- `sub_02063238` → pair-state query candidate `sub_02095a5c`
- accepted declaration/treaty-breaking paths in `sub_02063238` → authoritative setter `sub_02041f4c(..., value=0, ...)`
- `sub_02041f4c` direct path → symmetric matrix writes at `0x0219fb54`
- `sub_02041f4c` propagated path → `sub_02089788(message=38, ...)` → `sub_02093a4c`
- overlay 1 `sub_02206ff4` → presentation consumer `sub_02206610`

The branch edges, matrix arithmetic, and constants are confirmed. `sub_02095a5c` semantics and network helper names remain candidates.
