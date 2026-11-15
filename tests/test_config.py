"""Tests for the analysis configuration."""

from __future__ import annotations

import dataclasses

import pytest

from teramount_analysis.config import Config


def test_px_um_roundtrip():
    c = Config()
    assert c.px(0.252) == pytest.approx(1.0) and c.um(4.0) == pytest.approx(1.008)


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
