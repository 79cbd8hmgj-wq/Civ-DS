from __future__ import annotations

from civds.cli import build_parser


def test_parser_exposes_toolkit_runtime_probe() -> None:
    parser = build_parser()

    arguments = parser.parse_args(["runtime", "probe", "--cpu", "arm9"])

    assert arguments.command == "runtime"
    assert arguments.runtime_command == "probe"
