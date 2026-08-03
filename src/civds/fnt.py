"""NitroFS File Name Table hierarchy parser."""

from __future__ import annotations
from dataclasses import dataclass
import struct
from .errors import FormatError


@dataclass(frozen=True)
class NitroFile:
    file_id: int
    path: str


def parse_fnt(data: bytes, file_count: int) -> list[NitroFile]:
    if len(data) < 8:
        raise FormatError("truncated FNT root")
    root_offset, _, dir_count = struct.unpack_from("<IHH", data, 0)
    if dir_count == 0 or dir_count * 8 > len(data) or root_offset >= len(data):
        raise FormatError("invalid FNT directory table")
    dirs = []
    for i in range(dir_count):
        off, first, parent = struct.unpack_from("<IHH", data, i * 8)
        if off >= len(data):
            raise FormatError("FNT subtable offset out of range")
        dirs.append((off, first, parent))
    result = []
    paths = set()
    visiting = set()

    def walk(index: int, prefix: str) -> None:
        if index in visiting:
            raise FormatError("FNT directory cycle")
        visiting.add(index)
        pos, file_id, _ = dirs[index]
        while True:
            if pos >= len(data):
                raise FormatError("unterminated FNT subtable")
            control = data[pos]
            pos += 1
            if control == 0:
                break
            size = control & 0x7F
            if size == 0 or pos + size > len(data):
                raise FormatError("truncated FNT name")
            raw = data[pos : pos + size]
            pos += size
            try:
                name = raw.decode("ascii")
            except UnicodeDecodeError as exc:
                raise FormatError("non-ASCII FNT name") from exc
            if name in (".", "..") or "/" in name or "\\" in name or "\0" in name:
                raise FormatError("unsafe FNT path component")
            path = f"{prefix}/{name}" if prefix else name
            if control & 0x80:
                if pos + 2 > len(data):
                    raise FormatError("truncated FNT directory ID")
                child = struct.unpack_from("<H", data, pos)[0] - 0xF000
                pos += 2
                if child < 0 or child >= len(dirs):
                    raise FormatError("invalid FNT directory ID")
                walk(child, path)
            else:
                if file_id >= file_count:
                    raise FormatError("FNT file ID exceeds FAT")
                if path in paths:
                    raise FormatError(f"duplicate FNT path: {path}")
                paths.add(path)
                result.append(NitroFile(file_id, path))
                file_id += 1
        visiting.remove(index)

    walk(0, "")
    return sorted(result, key=lambda x: x.file_id)
