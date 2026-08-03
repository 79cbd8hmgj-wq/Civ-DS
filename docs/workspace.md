# Reproducible workspace

`python -m civds extract ROM WORKSPACE` creates a temporary sibling and atomically renames it only after all payloads and the manifest succeed. A populated destination is refused unless `--force` is explicit. `original/` contains immutable ARM binaries, a bounded banner, all 2,753 FAT payloads, 2,736 safe NitroFS named hard-link views, 17 separately named overlay views, and the source ROM used for exact rebuilding. `decoded/` mirrors resource and overlay views; `modified/` is the only patch input. `rebuilt/`, `reports/`, and `runtime/` separate generated outputs.

The exact reference contains no overlay compression flags and no FAT payload that passes strict LZ10 decoding. Its no-change rebuild is byte-identical with SHA-256 `f19db60920731ba7af2f0e7977870383973fa3a85096aa7d52f9d672e4002c08`. Same-size stored-payload replacements are supported; relocation is deliberately refused until alignment and table rewrite rules are implemented.
