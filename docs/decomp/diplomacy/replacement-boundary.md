# Replacement boundary

## Confirmed authoritative boundary

`sub_02041f4c` is the first confirmed authoritative relationship storage boundary. Its direct path symmetrically updates `g_relationship_state_0219fb54[6][6]`; its propagated path emits network message 38. A future hook may wrap this function only after initialization, save/load, message-38 receive handling, and all numeric state values are confirmed. Replacing it now would risk desynchronizing multiplayer and secondary relationship metadata.

Overlay 1 `sub_02206610` remains presentation-only and must not be used as a gameplay hook. ARM9 `sub_02063238` is a validation/UI boundary for attempted attacks; it is suitable for observation and guarded breakpoints, not yet wholesale replacement.
