from terratrend.data import load_observations


def test_fixture_is_labeled_and_has_known_indicators():
    observations = load_observations()

    assert len(observations) == 18
    assert {row["label"] for row in observations} == {
        "SYNTHETIC — NOT REAL EARTH OBSERVATION DATA"
    }
    assert {row["indicator"] for row in observations} == {
        "surface_temperature_anomaly",
        "vegetation_index_anomaly",
        "precipitation_anomaly",
    }
