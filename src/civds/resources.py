"""Access immutable package data independently of the current directory."""

from __future__ import annotations
import json
from importlib.resources import files
from typing import Any, cast


def supported_roms() -> dict[str, Any]:
    resource = files("civds.data").joinpath("supported_roms.json")
    return cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))
