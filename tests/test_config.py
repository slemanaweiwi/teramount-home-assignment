"""Tests for the analysis configuration."""

from __future__ import annotations

import dataclasses

import pytest

from teramount_analysis.config import Config


def test_px_um_roundtrip():
    c = Config()
    assert c.px(0.252) == pytest.approx(1.0) and c.um(4.0) == pytest.approx(1.008)


def test_only_sub_pixel_settings_are_in_pixels():
    # Sizes of features and filters must scale with the pixel size; only the
    # straight-edge residual (a sub-pixel precision limit) is in pixels.
    pixel_fields = {f.name for f in dataclasses.fields(Config) if f.name.endswith("_px")}
    assert pixel_fields == {"rotation_max_line_rms_px"}


@pytest.mark.parametrize("um, pixel_um, expected", [(1.26, 0.252, 5), (0.756, 0.252, 3),
                                                     (0.756, 0.5, 1), (1.26, 0.5, 3)])
def test_filter_sizes_are_odd_pixel_counts(um, pixel_um, expected):
    assert Config(pixel_size_um=pixel_um).odd_px(um) == expected


def test_config_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Config().pixel_size_um = 1.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "overrides",
    [
        {"pixel_size_um": 0},
        {"pixel_size_um": -0.1},
        {"z_scale": 0},
        {"xpander_aperture_fraction": 0.0},
        {"xpander_aperture_fraction": 1.5},
        {"cross_polarity": "sideways"},
    ],
)
def test_invalid_config_rejected(overrides):
    with pytest.raises(ValueError):
        Config(**overrides)
