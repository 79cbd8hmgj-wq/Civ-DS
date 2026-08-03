"""Conservative ARM-state function and direct-call candidate discovery."""

from __future__ import annotations
from dataclasses import asdict, dataclass
import struct


@dataclass(frozen=True)
class FunctionCandidate:
    runtime_address: int
    binary_offset: int
    prologue_word: int
    confidence: str = "candidate"


@dataclass(frozen=True)
class DirectCall:
    caller_instruction: int
    caller_offset: int
    target_address: int
    internal: bool


def discover_arm_functions(
    data: bytes, base: int, executable_start: int = 0
) -> list[FunctionCandidate]:
    output: list[FunctionCandidate] = []
    for offset in range(executable_start, len(data) - 3, 4):
        word = struct.unpack_from("<I", data, offset)[0]
        if word & 0xFFFF4000 == 0xE92D4000 and word & 0x3FFF:
            output.append(FunctionCandidate(base + offset, offset, word))
    return output


def discover_arm_calls(data: bytes, base: int, executable_start: int = 0) -> list[DirectCall]:
    output: list[DirectCall] = []
    end = base + len(data)
    for offset in range(executable_start, len(data) - 3, 4):
        word = struct.unpack_from("<I", data, offset)[0]
        if word >> 24 == 0xEB:
            displacement = word & 0xFFFFFF
            if displacement & 0x800000:
                displacement -= 0x1000000
            address = base + offset
            target = address + 8 + (displacement << 2)
            output.append(DirectCall(address, offset, target, base <= target < end))
    return output


def report(data: bytes, base: int, executable_start: int = 0) -> dict[str, object]:
    functions = discover_arm_functions(data, base, executable_start)
    calls = discover_arm_calls(data, base, executable_start)
    return {
        "base_runtime_address": f"0x{base:08x}",
        "binary_size": len(data),
        "function_candidates": [asdict(item) for item in functions],
        "direct_calls": [asdict(item) for item in calls],
        "limitations": [
            "ARM-state prologue heuristic only",
            "Thumb functions and tail calls are not enumerated",
            "Candidates are not semantic confirmations",
        ],
    }
