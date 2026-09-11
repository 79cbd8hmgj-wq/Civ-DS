from __future__ import annotations

import argparse

from nds_disassembly_toolkit.analysis.runtime_cli import add_runtime_parser


def test_pinned_toolkit_exposes_melonds_runtime_probe() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_runtime_parser(subparsers)

    arguments = parser.parse_args(["runtime", "probe", "--cpu", "arm9"])

    assert arguments.command == "runtime"
    assert arguments.runtime_command == "probe"
    assert arguments.cpu.value == "arm9"
    assert arguments.host == "127.0.0.1"
    assert arguments.port is None
