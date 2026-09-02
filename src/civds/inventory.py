from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


def _require_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"{key!r} must be a JSON array")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{key!r} entries must be JSON objects")
    return rows


def _extension(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix or "<none>"


def _top_level(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if len(parts) > 1 else "<root>"


def _ranked_counter(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def summarize_inventory(
    files_payload: dict[str, Any],
    assets_payload: dict[str, Any],
    *,
    rare_extension_limit: int = 25,
    example_limit: int = 12,
    largest_limit: int = 25,
) -> dict[str, Any]:
    """Summarize committed Civ-DS NitroFS metadata without reading ROM payload bytes."""
    if rare_extension_limit < 1 or example_limit < 1 or largest_limit < 1:
        raise ValueError("summary limits must be positive")

    files = _require_rows(files_payload, "files")
    assets = _require_rows(assets_payload, "assets")

    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    directory_counts: Counter[str] = Counter()
    directory_bytes: Counter[str] = Counter()
    compression_counts: Counter[str] = Counter()
    paths_by_extension: dict[str, list[str]] = defaultdict(list)

    seen_file_ids: set[int] = set()
    normalized_files: list[dict[str, Any]] = []
    for row in files:
        try:
            file_id = int(row["file_id"])
            path = str(row["path"])
            decoded_size = int(row["decoded_size"])
            compression = str(row["compression"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("file metadata row is missing required fields") from exc
        if file_id in seen_file_ids:
            raise ValueError(f"duplicate file_id in file metadata: {file_id}")
        if decoded_size < 0:
            raise ValueError(f"negative decoded_size for file_id {file_id}")
        seen_file_ids.add(file_id)

        extension = _extension(path)
        top_level = _top_level(path)
        extension_counts[extension] += 1
        extension_bytes[extension] += decoded_size
        directory_counts[top_level] += 1
        directory_bytes[top_level] += decoded_size
        compression_counts[compression] += 1
        paths_by_extension[extension].append(path)
        normalized_files.append(
            {
                "file_id": file_id,
                "path": path,
                "decoded_size": decoded_size,
                "compression": compression,
            }
        )

    detected_format_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    unknown_extension_counts: Counter[str] = Counter()
    unknown_paths_by_extension: dict[str, list[str]] = defaultdict(list)
    asset_ids: set[int] = set()
    for row in assets:
        try:
            file_id = int(row["file_id"])
            path = str(row["path"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("asset metadata row is missing required fields") from exc
        if file_id in asset_ids:
            raise ValueError(f"duplicate file_id in asset metadata: {file_id}")
        asset_ids.add(file_id)

        detected = row.get("detected_format")
        detected_format_counts["unknown" if detected is None else str(detected)] += 1
        evidence_counts[str(row.get("evidence", "unknown"))] += 1
        if detected is None:
            extension = _extension(path)
            unknown_extension_counts[extension] += 1
            unknown_paths_by_extension[extension].append(path)

    extension_stats = [
        {
            "extension": extension,
            "count": extension_counts[extension],
            "decoded_bytes": extension_bytes[extension],
        }
        for extension in sorted(
            extension_counts,
            key=lambda value: (-extension_counts[value], value),
        )
    ]
    directory_stats = [
        {
            "directory": directory,
            "count": directory_counts[directory],
            "decoded_bytes": directory_bytes[directory],
        }
        for directory in sorted(
            directory_counts,
            key=lambda value: (-directory_counts[value], value),
        )
    ]
    rare_extensions = [
        {
            "extension": extension,
            "count": extension_counts[extension],
            "paths": sorted(paths_by_extension[extension]),
        }
        for extension in sorted(extension_counts)
        if extension_counts[extension] <= rare_extension_limit
    ]
    unknown_extensions = [
        {
            "extension": extension,
            "count": unknown_extension_counts[extension],
            "example_paths": sorted(unknown_paths_by_extension[extension])[:example_limit],
        }
        for extension in sorted(
            unknown_extension_counts,
            key=lambda value: (-unknown_extension_counts[value], value),
        )
    ]
    largest_files = sorted(
        normalized_files,
        key=lambda row: (-row["decoded_size"], row["path"], row["file_id"]),
    )[:largest_limit]

    return {
        "format_version": 1,
        "totals": {
            "files": len(files),
            "assets": len(assets),
            "decoded_bytes": sum(row["decoded_size"] for row in normalized_files),
            "top_level_directories": len(directory_counts),
            "extensions": len(extension_counts),
        },
        "top_level_directories": directory_stats,
        "extensions": extension_stats,
        "compression": _ranked_counter(compression_counts),
        "detected_formats": _ranked_counter(detected_format_counts),
        "asset_evidence": _ranked_counter(evidence_counts),
        "unknown_extensions": unknown_extensions,
        "rare_extensions": rare_extensions,
        "largest_files": largest_files,
    }


def write_inventory_summary(
    files_path: Path,
    assets_path: Path,
    output: Path,
) -> Path:
    files_payload = json.loads(files_path.read_text(encoding="utf-8"))
    assets_payload = json.loads(assets_path.read_text(encoding="utf-8"))
    summary = summarize_inventory(files_payload, assets_payload)

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return output
