from pathlib import Path
import pytest
from civds.hashing import sha256_file
from civds.rom import inspect

ROM = Path("local/reference/Sid Meier's Civilization Revolution (USA) (En,Fr,De,Es,It).nds")


@pytest.mark.reference_rom
@pytest.mark.skipif(not ROM.exists(), reason="copyrighted local reference ROM is absent")
def test_exact_reference_identity_and_counts() -> None:
    assert sha256_file(ROM) == "f19db60920731ba7af2f0e7977870383973fa3a85096aa7d52f9d672e4002c08"
    header, files, overlays = inspect(ROM)
    assert header["game_code"] == "YS6E"
    assert header["file_count"] == 2753
    assert len(overlays) == 17
    assert len({item["path"] for item in files}) == len(files)
