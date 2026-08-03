# ARM9 boot boundary

**Confirmed:** ROM offset `0x4800`, ARM9 binary offset `0x800`, and runtime address `0x02000800` contain the same entry instructions. Static ARMv5TE decoding and a DeSmuME ARM9 GDB memory read agree byte-for-byte. The entry synchronizes through the DS IPC register region, calls neutral `sub_02000ab0`, switches privileged CPU modes, establishes stack pointers, and calls `sub_02000954` to clear a `0x4000`-byte region.

The precise semantic roles of the two callees remain candidates until their callers and effects are traced. `sub_02000800` is a safe observation boundary but is not yet a replacement boundary because CPU mode and stack invariants must be preserved exactly.
