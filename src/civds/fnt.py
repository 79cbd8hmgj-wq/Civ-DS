"""Strict NitroFS File Name Table hierarchy parser."""

from __future__ import annotations
from dataclasses import dataclass
import struct
from .errors import FormatError

ROOT_ID = 0xF000


@dataclass(frozen=True)
class NitroFile:
    file_id: int
    path: str


@dataclass(frozen=True)
class _Directory:
    entries_offset: int
    first_file_id: int
    parent: int


def parse_fnt(data: bytes, file_count: int) -> list[NitroFile]:
    if len(data) < 8:
        raise FormatError("truncated FNT root")
    root_offset, _, directory_count = struct.unpack_from("<IHH", data, 0)
    if directory_count == 0 or directory_count > 0x1000:
        raise FormatError("invalid FNT directory count")
    table_end = directory_count * 8
    if table_end > len(data) or root_offset < table_end or root_offset >= len(data):
        raise FormatError("invalid FNT directory table")
    directories: list[_Directory] = []
    for index in range(directory_count):
        offset, first_file_id, parent = struct.unpack_from("<IHH", data, index * 8)
        if offset < table_end or offset >= len(data):
            raise FormatError("FNT subtable offset out of range")
        if first_file_id > file_count:
            raise FormatError("FNT first file ID exceeds FAT")
        directories.append(_Directory(offset, first_file_id, parent))
    if directories[0].parent != directory_count:
        raise FormatError("FNT root directory count is inconsistent")
    owners: dict[int, int] = {0: -1}
    visiting: set[int] = set()
    visited: set[int] = set()
    paths: set[str] = set()
    file_owners: dict[int, int] = {}
    result: list[NitroFile] = []

    def walk(index: int, prefix: str) -> None:
        if index in visiting:
            raise FormatError("FNT directory cycle")
        if index in visited:
            raise FormatError("FNT directory alias")
        visiting.add(index)
        directory = directories[index]
        position = directory.entries_offset
        file_id = directory.first_file_id
        while True:
            if position >= len(data):
                raise FormatError("unterminated FNT subtable")
            control = data[position]
            position += 1
            if control == 0:
                break
            size = control & 0x7F
            if size == 0 or position + size > len(data):
                raise FormatError("truncated FNT name")
            raw_name = data[position : position + size]
            position += size
            try:
                name = raw_name.decode("ascii")
            except UnicodeDecodeError as exc:
                raise FormatError("non-ASCII FNT name") from exc
            if name in (".", "..") or "/" in name or "\\" in name or "\0" in name:
                raise FormatError("unsafe FNT path component")
            path = f"{prefix}/{name}" if prefix else name
            if path in paths:
                raise FormatError(f"duplicate FNT path: {path}")
            paths.add(path)
            if control & 0x80:
                if position + 2 > len(data):
                    raise FormatError("truncated FNT directory ID")
                child_id = struct.unpack_from("<H", data, position)[0]
                position += 2
                child = child_id - ROOT_ID
                if child <= 0 or child >= directory_count:
                    raise FormatError("invalid FNT directory ID")
                if child in owners:
                    raise FormatError("FNT directory referenced by multiple parents")
                if directories[child].parent != ROOT_ID + index:
                    raise FormatError("invalid FNT parent relationship")
                owners[child] = index
                walk(child, path)
            else:
                if file_id >= file_count:
                    raise FormatError("FNT file ID exceeds FAT")
                if file_id in file_owners:
                    raise FormatError("duplicate or overlapping FNT file-ID range")
                file_owners[file_id] = index
                result.append(NitroFile(file_id, path))
                file_id += 1
        visiting.remove(index)
        visited.add(index)

    walk(0, "")
    if len(visited) != directory_count:
        raise FormatError("unreachable FNT directory record")
    return sorted(result, key=lambda item: item.file_id)
