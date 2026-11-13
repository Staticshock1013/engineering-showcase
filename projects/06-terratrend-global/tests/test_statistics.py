from terratrend.data import load_observations
from terratrend.statistics import indicator_summary, regional_means, summarize


def test_summarize_returns_deterministic_descriptives():
    assert summarize([0.42, 0.48, 0.71, 0.68, 0.36, 0.39]) == {
        "count": 6,
        "mean": 0.5067,
        "median": 0.45,
        "minimum": 0.36,
        "maximum": 0.71,
    }


def test_summarize_empty_series_is_explicit():
    assert summarize([]) == {
        "count": 0,
        "mean": None,
        "median": None,
        "minimum": None,
        "maximum": None,
    }


def test_indicator_summary_and_regional_means_are_stable():
    observations = load_observations()

    assert indicator_summary(observations, "precipitation_anomaly")["mean"] == -9.6667
    assert regional_means(observations, "surface_temperature_anomaly") == [
        {"region": "Amazon Basin", "mean_value": 0.45},
        {"region": "Sahel", "mean_value": 0.695},
        {"region": "Southeast Asia", "mean_value": 0.375},
    ]
