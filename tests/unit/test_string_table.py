import struct
import pytest
from civds.errors import FormatError
from civds.string_table import parse_stbl


def table(text: bytes = b"Peace") -> bytes:
    header = b"STBL" + struct.pack("<III", 1, 0, 0) + struct.pack("<II", 1, 0)
    offset = 32
    return header + struct.pack("<II", offset, 0x12345678) + struct.pack("<I", len(text)) + text


def test_parse_stbl_record() -> None:
    record = parse_stbl(table())[0]
    assert (record.index, record.key_hash, record.text) == (0, 0x12345678, "Peace")


def test_rejects_bad_stbl() -> None:
    with pytest.raises(FormatError):
        parse_stbl(b"bad")
    malformed = bytearray(table())
    struct.pack_into("<I", malformed, 24, 0xFFFFFFF0)
    with pytest.raises(FormatError):
        parse_stbl(bytes(malformed))
