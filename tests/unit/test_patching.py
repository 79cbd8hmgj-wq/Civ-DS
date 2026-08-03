from pathlib import Path
import pytest
from civds.errors import CivDSError
from civds.patching import GuardedPatch, apply_patch

def test_guarded_patch_is_applied(tmp_path: Path) -> None:
    target = tmp_path / "binary"
    target.write_bytes(b"abcdef")
    apply_patch(target, GuardedPatch("example", 2, b"cd", b"XY"))
    assert target.read_bytes() == b"abXYef"

def test_mismatch_is_atomic(tmp_path: Path) -> None:
    target = tmp_path / "binary"
    target.write_bytes(b"abcdef")
    with pytest.raises(CivDSError, match="differ"):
        apply_patch(target, GuardedPatch("example", 2, b"zz", b"XY"))
    assert target.read_bytes() == b"abcdef"
