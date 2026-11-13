from terratrend.availability import CityAvailability
from terratrend.dashboard import load_lst_availability_state, load_verified_cache_state


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


def test_lst_availability_state_marks_ready_cities():
    city = CityAvailability(
        city="São Paulo",
        status="verified",
        latitude=-23.55,
        longitude=-46.625,
        bounding_box=(-46.75, -23.65, -46.50, -23.45),
        product_key="mod11a2_v061_daytime_lst",
        shared_window_status="verified",
        period_start="2024-06-25T00:00:00.000Z",
        period_end="2024-07-02T23:59:59.000Z",
        cache_path="mod11a2_sao_paulo_2024-06-25.json",
        reason=None,
        mean_celsius=20.015,
        valid_pixel_count=4,
        selected_pixel_count=662,
    )

    state = load_lst_availability_state(lambda: [city])

    assert state.status == "ready"
    assert state.cities[0].city == "São Paulo"


def test_lst_availability_state_fails_closed():
    state = load_lst_availability_state(loader=lambda: (_ for _ in ()).throw(OSError("disk")))

    assert state.status == "unavailable"
    assert state.cities == []
