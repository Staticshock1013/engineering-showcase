import numpy as np
import pytest

from terratrend.mod11a2 import Mod11A2ValidationError
from terratrend.mod13a2 import (
    NDVI_SCALE_DIVISOR,
    NDVI_VALID_RANGE,
    _validate_ndvi_metadata,
    good_ndvi_qc,
)
from terratrend.nasa import MOD13A2_V061


def test_mod13a2_product_definition_preserves_documented_semantics():
    assert MOD13A2_V061.short_name == "MOD13A2"
    assert MOD13A2_V061.version == "061"
    assert MOD13A2_V061.temporal_composite_days == 16
    assert MOD13A2_V061.scale_factor == 0.0001


def test_ndvi_qc_requires_good_detailed_and_summary_quality():
    detailed = np.array([0b0000, 0b0001, 0b0000, 0b0010], dtype=np.uint16)
    reliability = np.array([0, 0, 1, 0], dtype=np.int8)

    assert good_ndvi_qc(detailed, reliability).tolist() == [True, False, False, False]


def test_ndvi_metadata_uses_documented_scale_and_file_divisor():
    attributes = {
        "scale_factor": NDVI_SCALE_DIVISOR,
        "add_offset": 0.0,
        "_FillValue": -3000,
        "valid_range": list(NDVI_VALID_RANGE),
        "units": "NDVI",
    }

    _validate_ndvi_metadata(attributes)

    with pytest.raises(Mod11A2ValidationError, match="scale divisor"):
        _validate_ndvi_metadata({**attributes, "scale_factor": 1.0})
