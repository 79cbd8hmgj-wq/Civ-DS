"""Functional reconstruction of the symmetric relationship-state setter."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field

NetworkEmitter = Callable[[int, int, int], None]


@dataclass
class RelationshipMatrix:
    """Six-by-six signed 32-bit states matching ARM9 global 0x0219fb54."""

    values: list[list[int]] = field(default_factory=lambda: [[0] * 6 for _ in range(6)])
    network_enabled: bool = False
    emit_network: NetworkEmitter | None = None

    def set_symmetric(
        self, civilization_a: int, civilization_b: int, value: int, propagate: bool
    ) -> None:
        if not 0 <= civilization_a < 6 or not 0 <= civilization_b < 6:
            raise IndexError("civilization index outside confirmed six-entry matrix")
        current = self.values[civilization_a][civilization_b]
        if current == value and value != 0:
            return
        if not self.network_enabled or not propagate:
            self.values[civilization_a][civilization_b] = value
            self.values[civilization_b][civilization_a] = value
            return
        if self.emit_network is None:
            raise RuntimeError("network propagation requested without emitter")
        self.emit_network(civilization_a, civilization_b, value)
