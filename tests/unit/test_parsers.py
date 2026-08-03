import struct
import pytest
from civds.crc import crc16
from civds.errors import FormatError
from civds.fat import parse_fat
from civds.fnt import parse_fnt
from civds.nds_header import parse_header
from civds.overlays import parse_overlays


def valid_header() -> bytearray:
    data = bytearray(0x200)
    struct.pack_into("<4I", data, 0x20, 0x200, 0x02000000, 0x02000000, 0x100)
    struct.pack_into("<4I", data, 0x30, 0x300, 0x02380000, 0x02380000, 0x100)
    struct.pack_into("<H", data, 0x15E, crc16(data[:0x15E]))
    return data


def seal(data: bytearray) -> bytes:
    struct.pack_into("<H", data, 0x15E, crc16(data[:0x15E]))
    return bytes(data)


def make_fnt(records: list[tuple[int, int]], subtables: list[bytes]) -> bytes:
    count = len(records)
    offsets: list[int] = []
    position = count * 8
    for subtable in subtables:
        offsets.append(position)
        position += len(subtable)
    rows = bytearray()
    for index, (first, parent) in enumerate(records):
        rows += struct.pack("<IHH", offsets[index], first, count if index == 0 else parent)
    return bytes(rows) + b"".join(subtables)


def test_header_rejects_truncation_crc_range_entry_and_overflow() -> None:
    with pytest.raises(FormatError, match="truncated"):
        parse_header(b"", 0)
    data = valid_header()
    data[0] ^= 1
    with pytest.raises(FormatError, match="CRC"):
        parse_header(bytes(data), 0x1000)
    data = valid_header()
    struct.pack_into("<II", data, 0x40, 0x1100, 8)
    with pytest.raises(FormatError, match="fnt range"):
        parse_header(seal(data), 0x1000)
    data = valid_header()
    struct.pack_into("<I", data, 0x24, 0x02000200)
    with pytest.raises(FormatError, match="entry"):
        parse_header(seal(data), 0x1000)
    data = valid_header()
    struct.pack_into("<II", data, 0x28, 0xFFFFFFF0, 0x100)
    with pytest.raises(FormatError, match="overflows"):
        parse_header(seal(data), 0x1000)


def test_fat_rejects_truncation_invalid_and_overlap() -> None:
    with pytest.raises(FormatError, match="truncated"):
        parse_fat(b"x", 100)
    with pytest.raises(FormatError, match="invalid"):
        parse_fat(struct.pack("<II", 20, 10), 100)
    with pytest.raises(FormatError, match="overlapping"):
        parse_fat(struct.pack("<IIII", 10, 30, 20, 40), 100)


def test_fnt_parses_hierarchy() -> None:
    data = make_fnt([(0, 0), (1, 0xF000)], [b"\x83dir\x01\xf0\0", b"\x01x\0"])
    assert [(item.file_id, item.path) for item in parse_fnt(data, 2)] == [(1, "dir/x")]


@pytest.mark.parametrize(
    ("data", "match"),
    [
        (make_fnt([(0, 0)], [b"\x02..\0"]), "unsafe"),
        (make_fnt([(0, 0)], [b"\x81x"]), "truncated"),
        (make_fnt([(0, 0)], [b"\x01x\x01x\0"]), "duplicate"),
        (
            make_fnt([(0, 0), (0, 0xF000)], [b"\x81a\x01\xf0\x81b\x01\xf0\0", b"\0"]),
            "multiple parents",
        ),
        (make_fnt([(0, 0), (0, 0xF001)], [b"\x81a\x01\xf0\0", b"\0"]), "parent relationship"),
        (make_fnt([(0, 0), (0, 0xF000)], [b"\0", b"\0"]), "unreachable"),
        (make_fnt([(0, 0), (0, 0xF000)], [b"\x01x\x81a\x01\xf0\0", b"\x01y\0"]), "file-ID range"),
        (
            make_fnt(
                [(0, 0), (0, 0xF000), (0, 0xF001)],
                [b"\x81a\x01\xf0\0", b"\x81b\x02\xf0\0", b"\x81a\x01\xf0\0"],
            ),
            "multiple parents",
        ),
    ],
)
def test_fnt_rejects_malformed_hierarchies(data: bytes, match: str) -> None:
    with pytest.raises(FormatError, match=match):
        parse_fnt(data, 4)


def test_overlay_metadata_and_guards() -> None:
    row = struct.pack("<8I", 3, 0x02200000, 10, 4, 0, 0, 1, 0x01000008)
    item = parse_overlays(row, [0, 8])[0]
    assert item.is_compressed and item.compressed_size == 8
    with pytest.raises(FormatError, match="impossible"):
        parse_overlays(row, [8])
    with pytest.raises(FormatError, match="truncated"):
        parse_overlays(b"x", [8, 8])
    invalid_init = struct.pack("<8I", 3, 0x02200000, 10, 0, 0x02200009, 0x0220000B, 1, 0)
    with pytest.raises(FormatError, match="initializer"):
        parse_overlays(invalid_init, [0, 10])
    compressed = struct.pack("<8I", 3, 0x02200000, 10, 0, 0, 0, 1, 0x01000009)
    with pytest.raises(FormatError, match="compressed size"):
        parse_overlays(compressed, [0, 8])
