from __future__ import annotations

from dataclasses import dataclass

_ARM9_RAM_ADDRESS = 0x02000000


@dataclass(frozen=True)
class CombatConstant:
    name: str
    arm9_offset: int
    description: str
    confidence: str
    """"high": tied to a debug-print string naming the exact bonus in the ROM.
    "medium": the code site and effect are traced and consistent with the
    surrounding formula, but no debug string or further cross-reference
    confirms the exact trigger condition/semantic name."""


# Every entry below is a plain 8-bit-immediate ARM data-processing
# instruction (MOV/ADD/SUB #imm, rotate=0) inside the combat
# modifier/odds function at arm9 0x020897ec (Sid Meier's Civilization
# Revolution DS, US ROM, profile "civrev-usa"). The immediate occupies the
# low byte of the little-endian instruction word, so it is safe to replace
# in place with any other 0-255 value without touching the opcode,
# condition code, or registers. See analysis/combat-model.md for the full
# derivation and evidence.
COMBAT_CONSTANTS: tuple[CombatConstant, ...] = (
    CombatConstant(
        name="veteran-tier-bonus-attacker",
        arm9_offset=0x0008B72C,
        description=(
            "Percent added to the attacker's effective strength per veteran/"
            "condition tier step (clamped to one step; tied to the "
            "'Veteran +50%' debug string)"
        ),
        confidence="high",
    ),
    CombatConstant(
        name="veteran-tier-bonus-defender",
        arm9_offset=0x0008B868,
        description=(
            "Same as veteran-tier-bonus-attacker, applied on the defender's "
            "side"
        ),
        confidence="high",
    ),
    CombatConstant(
        name="fortified-in-city-bonus",
        arm9_offset=0x0008B910,
        description=(
            "Percent added to the defender's effective strength when "
            "defending in a friendly city tile (tied to the "
            "'Fortified +100%' debug string)"
        ),
        confidence="high",
    ),
    CombatConstant(
        name="fortifying-bonus",
        arm9_offset=0x0008B968,
        description=(
            "Percent added to the defender's effective strength while "
            "actively fortifying (tied to the 'Fortifying +50%' debug "
            "string)"
        ),
        confidence="high",
    ),
    CombatConstant(
        name="zone-of-control-penalty",
        arm9_offset=0x0008B564,
        description=(
            "Percent subtracted from the attacker's effective strength when "
            "one of four directional per-tile bit-combination checks "
            "matches (pattern consistent with a zone-of-control/flanking "
            "penalty; no debug string confirms the exact trigger name)"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-primary-match",
        arm9_offset=0x0008C874,
        description=(
            "Multiplier applied to the defender's effective strength for an "
            "auto-resolve/overwhelming-force threshold check, used when a "
            "per-civilization difficulty byte equals the current global "
            "difficulty value"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-primary-mismatch",
        arm9_offset=0x0008C878,
        description=(
            "Same threshold check as overwhelm-threshold-primary-match, "
            "used when the difficulty byte does not match"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-secondary-match",
        arm9_offset=0x0008BF8C,
        description=(
            "Multiplier for a second, separate auto-resolve threshold check "
            "earlier in the same function, used when a related civilization "
            "comparison matches"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-secondary-mismatch",
        arm9_offset=0x0008BF90,
        description=(
            "Same check as overwhelm-threshold-secondary-match, used when "
            "the comparison does not match"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-tertiary-match",
        arm9_offset=0x0008BFA8,
        description=(
            "A third variant of the same auto-resolve threshold pattern, "
            "used when a further condition matches"
        ),
        confidence="medium",
    ),
    CombatConstant(
        name="overwhelm-threshold-tertiary-mismatch",
        arm9_offset=0x0008BFAC,
        description=(
            "Same check as overwhelm-threshold-tertiary-match, used when "
            "the condition does not match"
        ),
        confidence="medium",
    ),
)

_CONSTANTS_BY_NAME = {constant.name: constant for constant in COMBAT_CONSTANTS}


def read_combat_constant_value(blob: bytes, constant: CombatConstant) -> int:
    if constant.arm9_offset + 4 > len(blob):
        raise ValueError(f"{constant.name} offset is outside the ARM9 image")
    word = blob[constant.arm9_offset : constant.arm9_offset + 4]
    if word[1] & 0x0F != 0:
        # rotate field (low nibble of byte 1 in the little-endian word) must
        # be zero for a plain unrotated 8-bit immediate: replacing only
        # byte 0 is only safe under that encoding.
        raise ValueError(
            f"{constant.name} is not encoded as a plain 0-255 immediate "
            "(unexpected rotate field); refusing to treat it as patchable"
        )
    return word[0]


def build_combat_patch_set(
    blob: bytes,
    *,
    profile_id: str,
    values: dict[str, int],
) -> dict[str, object]:
    if not values:
        raise ValueError("no combat constants were requested for patching")

    patches: list[dict[str, object]] = []
    for name, new_value in values.items():
        constant = _CONSTANTS_BY_NAME.get(name)
        if constant is None:
            known = ", ".join(sorted(_CONSTANTS_BY_NAME))
            raise ValueError(f"unknown combat constant {name!r}; known constants: {known}")
        if not 0 <= new_value <= 255:
            raise ValueError(f"{name} must be between 0 and 255 (got {new_value})")

        current_value = read_combat_constant_value(blob, constant)

        patches.append(
            {
                "id": f"combat-{name}",
                "type": "binary_replace",
                "target": "arm9",
                "offset": constant.arm9_offset,
                "expected": bytes([current_value]).hex(),
                "replacement": bytes([new_value]).hex(),
                "rationale": (
                    f"Set combat constant {name!r} from {current_value} to {new_value} "
                    f"({constant.description})"
                ),
            }
        )

    return {
        "format_version": 1,
        "profile_id": profile_id,
        "patches": patches,
    }
