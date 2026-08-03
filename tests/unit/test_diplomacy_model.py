from civds.models.diplomacy import RelationshipMatrix


def test_relationship_setter_is_symmetric_and_suppresses_nonzero_repeat() -> None:
    state = RelationshipMatrix()
    state.set_symmetric(1, 4, 3, False)
    assert state.values[1][4] == state.values[4][1] == 3
    sent = []
    state.network_enabled = True
    state.emit_network = lambda a, b, v: sent.append((a, b, v))
    state.set_symmetric(1, 4, 3, True)
    assert sent == []
    state.set_symmetric(1, 4, 0, True)
    assert sent == [(1, 4, 0)]


def test_direct_zero_write_is_not_suppressed() -> None:
    state = RelationshipMatrix()
    state.set_symmetric(2, 3, 0, False)
    assert state.values[2][3] == state.values[3][2] == 0
