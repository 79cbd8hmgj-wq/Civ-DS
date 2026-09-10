# Civ-DS

Game-specific reverse-engineering and modding workspace for **Sid Meier's Civilization Revolution (Nintendo DS)**.

This repository is a **consumer** of the standalone [NDS Disassembly Toolkit](https://github.com/79cbd8hmgj-wq/NDS-Disassembly-Toolkit). Nintendo DS parsing, extraction/rebuild, compression, disassembly, static analysis, persistent analysis projects, binary patching, and ARM/Thumb source patching remain owned by that toolkit instead of being copied into Civ-DS.

The generic Rom-Mod-Toolkit design is used as project architecture guidance: source ROMs are treated as immutable inputs, exact hashes are recorded, mutations are guarded, and rebuilt outputs are verified. Civ-DS owns Civilization-specific profiles, addresses, symbols, table layouts, evidence, and gameplay modifications.

## Current integration

The `civds` command wraps the toolkit with stricter Civilization-specific defaults:

- exact supported-ROM profile required by default for extraction/rebuild;
- read-only `inspect`, asset inventory, and overlay-map paths can explicitly opt out for investigation;
- reusable toolkit `patch`, `source-patch`, `analyze`, and persistent `.ndsre` project commands remain available;
- exact-ROM profile generation is provided by Civ-DS so the project can lock onto the user's specific dump.

The toolkit dependency is pinned to commit `50cede2494cbdcfe064b2efc84d172c1031f6851` for reproducibility.

## Setup

Requires Python 3.11+.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Keep commercial ROMs, extracted game assets, and rebuilt ROMs local. They should not be added to the repository.

## First-time Civ Rev workspace

Unzip your legally obtained ROM locally, then create the exact profile:

```bash
civds profile create roms/CivRev.nds \
  --id civrev-usa \
  --output profiles/civrev-us.json
```

Inspect the ROM and record the baseline structure:

```bash
mkdir -p analysis
civds inspect roms/CivRev.nds --output analysis/rom-inspection.json
civds assets inventory roms/CivRev.nds --output analysis/assets.json --include-unknown
civds disasm overlay-map roms/CivRev.nds --output analysis/overlay-map.json
```

Extract the deterministic editable workspace:

```bash
civds extract roms/CivRev.nds work/civrev
```

The workspace separates immutable originals from editable decoded files. It includes `arm9.bin`, `arm7.bin`, NitroFS files, overlays, and manifests/hashes needed for guarded rebuilds.

## Rebuild loop

After modifying `work/civrev/modified/` through declared patches or controlled edits:

```bash
mkdir -p build
civds rebuild roms/CivRev.nds work/civrev build/CivRev-modded.nds
```

The toolkit reparses and verifies the rebuilt ROM and emits a build report alongside it.

### Guarded unit edits

The recovered unit descriptor table can generate fail-closed patch manifests for confirmed gameplay fields. The ROM is validated against the exact profile before offsets or expected bytes are emitted.

```bash
mkdir -p patches
civds units patch-manifest roms/CivRev.nds Warrior \
  --attack 2 \
  --defense 2 \
  --movement 2 \
  --fuel-turn-limit 5 \
  --production-cost 15 \
  --output patches/warrior-balance.json

civds patch work/civrev patches/warrior-balance.json
civds rebuild roms/CivRev.nds work/civrev build/CivRev-warrior-balance.nds
```

Each generated edit targets `arm9` with the recovered ARM9-relative offset plus the exact expected original byte. If the workspace, ROM profile, unit table, or original field value does not match, patch application fails rather than writing through the mismatch.

Use `civds units summarize` to inspect the recovered 38-record table before choosing values:

```bash
civds units summarize roms/CivRev.nds --output analysis/units.json
```

Current friendly byte-sized patch fields are `attack`, `defense`, `movement`, `fuel-turn-limit`, and `production-cost`. `fuel-turn-limit` is primarily relevant to units whose runtime behavior consumes that descriptor field, especially air units; changing it on other units should be treated as experimental rather than assumed to create air-style fuel behavior. Unresolved descriptor bytes and unresolved flag semantics remain available only as reverse-engineering evidence and are not exposed as named patch options.

### Guarded binary patches

```bash
civds patch work/civrev patches/example.json
```

Every fixed-length patch manifest should include expected original bytes so a wrong version/address fails closed instead of silently corrupting the workspace.

### ARM/Thumb source patches

```bash
civds source-patch build work/civrev patches/example-source.json
```

Source patches compile against the DS ARMv5TE target and retain the exact Civ Rev profile as the game-specific safety boundary.

## Reverse engineering

The toolkit's Phase 7A-7G analysis stack is exposed directly:

```bash
civds analyze \
  --component arm9 work/civrev/original/arm9.bin 0x02000000 \
  --output analysis/static-analysis.json

civds project create analysis/civrev.ndsre
civds project info analysis/civrev.ndsre
```

As Civ Rev functions, tables, and systems are confirmed, this repository should store the **interpretation layer**: named symbols, known addresses, record schemas, confidence/evidence, patch manifests, and gameplay modifications. Generic DS mechanics stay upstream in the NDS toolkit.

## Repository boundary

Commit:

- source code and tests;
- exact ROM profile metadata/hashes;
- game-specific reverse-engineering notes and symbols;
- patch/source manifests that do not contain copyrighted game payloads;
- synthetic test fixtures.

Do not commit:

- commercial ROM images or ROM ZIPs;
- extracted copyrighted game assets;
- rebuilt ROM images;
- large generated workspaces.
