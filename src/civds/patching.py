"""Atomic expected-byte guarded binary patching."""

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
from civds.errors import CivDSError


@dataclass(frozen=True)
class GuardedPatch:
    patch_id: str
    offset: int
    expected_original: bytes
    replacement: bytes


def apply_patch(path: Path, patch: GuardedPatch) -> None:
    if patch.offset < 0 or len(patch.expected_original) != len(patch.replacement):
        raise CivDSError("patch has invalid offset or unequal byte lengths")
    with path.open("rb") as stream:
        data = bytearray(stream.read())
    end = patch.offset + len(patch.expected_original)
    if end > len(data) or data[patch.offset : end] != patch.expected_original:
        raise CivDSError(f"patch {patch.patch_id}: expected original bytes differ")
    data[patch.offset : end] = patch.replacement
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
