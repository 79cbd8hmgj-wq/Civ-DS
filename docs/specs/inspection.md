# ROM inspection specification

Inspection streams the ROM hash and reads only validated bounded regions. Unsupported hashes fail by default. JSON is UTF-8, sorted by key, two-space indented, and newline terminated. Malformed headers, FAT records, FNT hierarchies, and overlay tables fail with structured errors.
