import struct
import pytest
from civds.errors import FormatError
from civds.fat import parse_fat
from civds.fnt import parse_fnt
from civds.nds_header import parse_header
from civds.overlays import parse_overlays


def test_header_rejects_truncation_and_impossible_range() -> None:
    with pytest.raises(FormatError, match="truncated"):
        parse_header(b"", 0)
    data = bytearray(0x200)
    struct.pack_into("<II", data, 0x40, 0x300, 8)
    with pytest.raises(FormatError, match="fnt range"):
        parse_header(bytes(data), 0x200)


def test_fat_rejects_truncation_invalid_and_overlap() -> None:
    with pytest.raises(FormatError, match="truncated"):
        parse_fat(b"x", 100)
    with pytest.raises(FormatError, match="invalid"):
        parse_fat(struct.pack("<II", 20, 10), 100)
    with pytest.raises(FormatError, match="overlapping"):
        parse_fat(struct.pack("<IIII", 10, 30, 20, 40), 100)


def test_fnt_parses_hierarchy() -> None:
    root = struct.pack("<IHH", 16, 0, 2)
    child = struct.pack("<IHH", 23, 1, 0xF000)
    data = root + child + b"\x83dir\x01\xf0\0" + b"\x01x\0"
    assert [(x.file_id, x.path) for x in parse_fnt(data, 2)] == [(1, "dir/x")]


def test_fnt_rejects_path_traversal_duplicate_and_truncation() -> None:
    for tail, match in ((b"\x02..\0", "unsafe"), (b"\x81x", "truncated")):
        with pytest.raises(FormatError, match=match):
            parse_fnt(struct.pack("<IHH", 8, 0, 1) + tail, 2)
    data = struct.pack("<IHH", 8, 0, 1) + b"\x01x\x01x\0"
    with pytest.raises(FormatError, match="duplicate"):
        parse_fnt(data, 2)


def test_overlay_metadata_and_guards() -> None:
    row = struct.pack("<8I", 3, 0x2200000, 10, 4, 0, 0, 1, 0x01000008)
    item = parse_overlays(row, 2)[0]
    assert item.is_compressed and item.compressed_size == 8
    with pytest.raises(FormatError, match="impossible"):
        parse_overlays(row, 1)
    with pytest.raises(FormatError, match="truncated"):
        parse_overlays(b"x", 2)
