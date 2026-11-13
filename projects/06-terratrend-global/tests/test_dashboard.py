from terratrend.dashboard import load_verified_cache_state


def test_verified_cache_state_marks_available_data_ready():
    state = load_verified_cache_state(lambda: [{"composite": {"city": "London"}}])

    assert state.status == "ready"
    assert state.entries[0]["composite"]["city"] == "London"


def test_verified_cache_state_marks_no_cache_empty():
    assert load_verified_cache_state(lambda: []).status == "empty"


def test_verified_cache_state_fails_closed_for_invalid_cache():
    def invalid_cache():
        raise ValueError("bad cache")

    state = load_verified_cache_state(invalid_cache)

    assert state.status == "unavailable"
    assert state.entries == []
