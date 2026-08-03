# Relationship state model

## Confirmed authoritative storage

ARM9 global `0x0219fb54` is a symmetric `int32_t[6][6]` matrix. `sub_02041f4c(a, b, value, propagate)` uses a 24-byte row stride, reads `[a][b]`, and directly writes both `[a][b]` and `[b][a]`. It suppresses an unchanged nonzero value but deliberately does not suppress zero. With networking active at `0x0219fa6c`, the propagation path emits message type 38 instead of writing locally.

ARM9 `sub_02063238` consumes the same matrix while validating attacks. Paths presenting alliance, treaty, territorial-war, declaration, Great Wall, and public-refusal messages converge on allow/refuse or negotiation actions. When declaration/treaty-breaking proceeds, it calls `sub_02041f4c` with value zero. Therefore the matrix, not overlay 1, is authoritative and zero is confirmed as the state selected for war initiation. Meanings of observed nonzero values (including 1 and 3) remain candidates until initialization, serialization, and state-specific consumers converge.
