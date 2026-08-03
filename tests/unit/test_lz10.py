import pytest
from civds.compression.lz10 import decompress, is_lz10
from civds.errors import FormatError

def test_literals_and_back_reference() -> None:
    encoded = bytes((0x10, 6, 0, 0, 0x10, ord("A"), ord("B"), ord("C"), 0, 2))
    assert is_lz10(encoded)
    assert decompress(encoded) == b"ABCABC"

def test_rejects_malformed_streams() -> None:
    for data in (b"", b"\x10\x03\0\0", b"\x10\x03\0\0\x80\0\0"):
        with pytest.raises(FormatError):
            decompress(data)
