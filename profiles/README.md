# ROM profiles

`civds` requires an exact profile for write-capable ROM workflows. Generate the profile from the legally obtained local ROM you intend to use:

```bash
civds profile create path/to/CivRev.nds \
  --id civrev-usa \
  --output profiles/civrev-us.json
```

The generated JSON contains only identity, SHA-256, and Nintendo DS layout metadata. It does not contain ROM bytes and is safe to version as project evidence.

The default Civ-DS CLI profile is `profiles/civrev-us.json`.
