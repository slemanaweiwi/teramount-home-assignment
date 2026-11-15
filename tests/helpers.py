"""Shared helpers that run the analysis chain up to one stage (tests only).

Each helper uses the *known* rotation ``phi`` instead of estimating it, so a
test exercises only its own stage.
"""

from __future__ import annotations

import numpy as np

from teramount_analysis.config import Config
from teramount_analysis.frame import Frame
from teramount_analysis.surface import segmentation_surface
from teramount_analysis.tilt import fit_base_plane, remove_tilt


def prepare(z: np.ndarray, phi: float, config: Config | None = None
            ) -> tuple[np.ndarray, Frame, np.ndarray, np.ndarray]:
    """Level the scan and build its canonical image and segmentation surface."""
    config = config or Config()
    z_leveled = remove_tilt(z, fit_base_plane(z, config), config)
    frame = Frame(z.shape, phi, 0)
    z_canonical = frame.canonical_image(z_leveled)
    return z_leveled, frame, z_canonical, segmentation_surface(z_canonical, config)


def seg(z: np.ndarray) -> np.ndarray:
    """Segmentation surface of an unrotated scan."""
    return prepare(z, 0.0)[3]
