"""Shared pytest fixtures.

Test modules import the synthetic-scan generator and helpers directly
(``from synthetic import make_scan``); pytest puts this folder on ``sys.path``.
"""

from __future__ import annotations

import pytest

from teramount_analysis.config import Config


@pytest.fixture
def config() -> Config:
    """Default analysis configuration."""
    return Config()
