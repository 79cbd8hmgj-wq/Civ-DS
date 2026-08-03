import pytest
from civds.compression.blz import decompress, footer
from civds.errors import FormatError


def test_blz_detection_rejects_impossible_footers() -> None:
    assert footer(b"") is None
    assert footer(b"12345678") is None
    impossible = b"12345678" + (0x08000020).to_bytes(4, "little") + (4).to_bytes(4, "little")
    assert footer(impossible) is None
    with pytest.raises(FormatError, match="not a valid"):
        decompress(impossible)
