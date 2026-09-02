from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nds_disassembly_toolkit import assets_cli, disassembly_cli, source_patch_cli
from nds_disassembly_toolkit.analysis.cli import add_analysis_parser, run_analysis_command
from nds_disassembly_toolkit.analysis.project_cli import add_project_parser, run_project_command
from nds_disassembly_toolkit.cli import (
    add_patch_parser,
    add_rom_parsers,
    run_patch_command,
    run_rom_command,
)
from nds_disassembly_toolkit.errors import NdsToolkitError

from civds.inventory import write_inventory_summary
from civds.profile import write_profile

DEFAULT_PROFILE = Path("profiles/civrev-us.json")
_ROM_COMMANDS = frozenset({"inspect", "extract", "rebuild"})


def _add_profile_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "profile",
        help="create and maintain the exact supported Civilization Revolution ROM profile",
    )
    commands = parser.add_subparsers(dest="profile_command")
    create = commands.add_parser(
        "create",
        help="derive an exact-ROM profile from a structurally valid NDS ROM",
    )
    create.add_argument("rom", type=Path)
    create.add_argument("--id", default="civrev-usa")
    create.add_argument("--output", type=Path, default=DEFAULT_PROFILE)


def _add_inventory_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "inventory",
        help="summarize committed Civ Rev filesystem and asset metadata",
    )
    commands = parser.add_subparsers(dest="inventory_command")
    summarize = commands.add_parser(
        "summarize",
        help="build deterministic directory, extension, format, and size statistics",
    )
    summarize.add_argument("files", type=Path)
    summarize.add_argument("assets", type=Path)
    summarize.add_argument("--output", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="civds",
        description="Civilization Revolution DS reverse-engineering and modding workspace",
    )
    subparsers = parser.add_subparsers(dest="command")

    _add_profile_parser(subparsers)
    _add_inventory_parser(subparsers)
    add_rom_parsers(
        subparsers,
        default_profile=DEFAULT_PROFILE,
        supported_by_default=True,
        allow_unsupported_commands={"inspect"},
    )
    add_patch_parser(subparsers)
    disassembly_cli.add_disassembly_parser(
        subparsers,
        default_profile=DEFAULT_PROFILE,
        supported_by_default=True,
    )
    add_analysis_parser(subparsers)
    add_project_parser(subparsers)
    assets_cli.add_assets_parser(
        subparsers,
        default_profile=DEFAULT_PROFILE,
        supported_by_default=True,
    )
    source_patch_cli.add_source_patch_parser(
        subparsers,
        default_profile=DEFAULT_PROFILE,
    )
    return parser


def _run_profile_command(arguments: argparse.Namespace) -> int:
    if arguments.profile_command != "create":
        raise NdsToolkitError("a profile subcommand is required")
    output = write_profile(
        arguments.rom.expanduser().resolve(),
        arguments.output,
        profile_id=arguments.id,
    )
    print(f"Wrote exact ROM profile: {output}")
    return 0


def _run_inventory_command(arguments: argparse.Namespace) -> int:
    if arguments.inventory_command != "summarize":
        raise NdsToolkitError("an inventory subcommand is required")
    output = write_inventory_summary(
        arguments.files.expanduser().resolve(),
        arguments.assets.expanduser().resolve(),
        arguments.output,
    )
    print(f"Wrote inventory summary: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if not args:
        parser.print_help()
        return 0
    arguments = parser.parse_args(args)
    if arguments.command is None:
        parser.print_help()
        return 0

    try:
        if arguments.command == "profile":
            return _run_profile_command(arguments)
        if arguments.command == "inventory":
            return _run_inventory_command(arguments)
        if arguments.command == "disasm":
            return disassembly_cli.run_disassembly_command(arguments)
        if arguments.command == "analyze":
            return run_analysis_command(arguments)
        if arguments.command == "project":
            return run_project_command(arguments)
        if arguments.command == "assets":
            return assets_cli.run_assets_command(arguments)
        if arguments.command == "source-patch":
            return source_patch_cli.run_source_patch_command(arguments)
        if arguments.command == "patch":
            return run_patch_command(arguments)
        if arguments.command in _ROM_COMMANDS:
            return run_rom_command(arguments)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except NdsToolkitError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 5

    parser.print_usage(sys.stderr)
    return 2
