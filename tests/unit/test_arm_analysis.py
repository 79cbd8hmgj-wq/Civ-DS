import struct
from civds.analysis.arm import discover_arm_calls, discover_arm_functions


def test_discovers_arm_prologue_and_signed_bl() -> None:
    data = struct.pack("<III", 0xE92D4010, 0xEB000001, 0xEBFFFFFC)
    functions = discover_arm_functions(data, 0x02000000)
    assert [(x.runtime_address, x.binary_offset) for x in functions] == [(0x02000000, 0)]
    calls = discover_arm_calls(data, 0x02000000)
    assert calls[0].target_address == 0x02000010
    assert calls[1].target_address == 0x02000000
