from pathlib import Path
import json
import pytest
from civds.errors import CivDSError
from civds.hashing import sha256_file
from civds.rebuild import rebuild, verify_rebuild


def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    (root / "original" / "fat").mkdir(parents=True)
    (root / "modified" / "fat").mkdir(parents=True)
    (root / "reports").mkdir()
    rom = root / "original" / "rom.nds"
    rom.write_bytes(b"HEADERpayloadTAIL")
    payload = root / "original" / "fat" / "0000.bin"
    payload.write_bytes(b"payload")
    manifest = {
        "rom_sha256": sha256_file(rom),
        "files": [
            {"file_id": 0, "rom_offset": 6, "stored_size": 7, "stored_sha256": sha256_file(payload)}
        ],
    }
    (root / "reports" / "extraction.json").write_text(json.dumps(manifest))
    return root


def test_no_change_rebuild_is_byte_identical(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    output = tmp_path / "rebuilt.nds"
    report = rebuild(root, output)
    assert report["byte_identical"] is True
    assert verify_rebuild(root / "original" / "rom.nds", output)["byte_identical"] is True


def test_same_size_change_and_relocation_refusal(tmp_path: Path) -> None:
    root = workspace(tmp_path)
    modified = root / "modified" / "fat" / "0000.bin"
    modified.write_bytes(b"PAYLOAD")
    output = tmp_path / "rebuilt.nds"
    assert rebuild(root, output)["changed_file_ids"] == [0]
    assert output.read_bytes() == b"HEADERPAYLOADTAIL"
    modified.write_bytes(b"too long")
    with pytest.raises(CivDSError, match="relocation"):
        rebuild(root, output)
