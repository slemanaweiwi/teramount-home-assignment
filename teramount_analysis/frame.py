"""Coordinate frame linking the original scan and its canonical orientation.

The *canonical* frame is the scan with its rotation undone: the fine rotation
``angle_deg`` (a few degrees, measured from straight edges) is reversed about
the array centre, then ``quarter_turns`` counter-clockwise 90° turns bring the
channel into the standard orientation (Pivot ramp pointing up, Xpander above).

Coordinates: ``x`` = column, ``y`` = row in the original scan; ``u``, ``v`` the
same in the canonical image; origin = centre of the top-left pixel. The fine
rotation follows ``scipy.ndimage.rotate``: a scan that ``rotate(chip, +a)``
would produce has ``angle_deg = +a`` (counter-clockwise as displayed).

Resampled canonical images are used only to *find* things. Measurements take
original pixels and transform their coordinates with :meth:`Frame.to_canonical`
(see :meth:`Frame.canonical_coordinates` and :meth:`Frame.pull_back`), so no
interpolation ever smooths the measured heights.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np
from scipy import ndimage

from .surface import fill_invalid


@dataclass(frozen=True)
class Frame:
    """Rotation state of a scan: fine angle plus quarter turns."""

    shape: tuple[int, int]  # original (rows, cols)
    angle_deg: float = 0.0  # fine rotation phi [deg], counter-clockwise positive
    quarter_turns: int = 0  # k: np.rot90(., k) applied after undoing phi

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", (int(self.shape[0]), int(self.shape[1])))
        object.__setattr__(self, "quarter_turns", int(self.quarter_turns) % 4)

    @property
    def canonical_shape(self) -> tuple[int, int]:
        """Shape of the canonical image (rows and cols swap on odd turns)."""
        h, w = self.shape
        return (h, w) if self.quarter_turns % 2 == 0 else (w, h)

    @property
    def rotation_deg(self) -> float:
        """Total rotation of the chip in the scan, normalised to (-180, 180]."""
        r = self.angle_deg - 90.0 * self.quarter_turns
        return float(r - 360.0 * np.ceil((r - 180.0) / 360.0))

    def _centre(self) -> tuple[float, float]:
        h, w = self.shape
        return (w - 1) / 2.0, (h - 1) / 2.0

    def _cos_sin(self) -> tuple[float, float]:
        a = np.deg2rad(self.angle_deg)
        return float(np.cos(a)), float(np.sin(a))

    def to_canonical(self, x: np.ndarray | float, y: np.ndarray | float
                     ) -> tuple[np.ndarray, np.ndarray]:
        """Map original pixel coordinates to canonical ones."""
        x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        cx, cy = self._centre()
        cos, sin = self._cos_sin()
        dx, dy = x - cx, y - cy
        u, v = cx + cos * dx - sin * dy, cy + sin * dx + cos * dy  # c + M^T (p - c)
        h, w = self.shape
        for _ in range(self.quarter_turns):  # np.rot90(., 1): (x, y) -> (y, w - 1 - x)
            u, v = v, w - 1 - u
            h, w = w, h
        return u, v

    def to_original(self, u: np.ndarray | float, v: np.ndarray | float
                    ) -> tuple[np.ndarray, np.ndarray]:
        """Map canonical pixel coordinates back to the original scan."""
        u, v = np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64)
        shapes = [self.shape]
        for _ in range(self.quarter_turns):
            shapes.append((shapes[-1][1], shapes[-1][0]))
        for _h, w in reversed(shapes[:-1]):  # undo each quarter turn, last one first
            u, v = w - 1 - v, u
        cx, cy = self._centre()
        cos, sin = self._cos_sin()
        du, dv = u - cx, v - cy
        return cx + cos * du + sin * dv, cy - sin * du + cos * dv  # c + M (f - c)

    def canonical_image(self, z: np.ndarray, order: int = 1) -> np.ndarray:
        """Resample a scan into the canonical frame (for segmentation only).

        NaNs are filled with their nearest valid neighbour first; borders use
        the nearest edge value.
        """
        out = fill_invalid(z)[0]
        if self.angle_deg:
            out = ndimage.rotate(out, -self.angle_deg, reshape=False, order=order,
                                 mode="nearest")
        return np.ascontiguousarray(np.rot90(out, self.quarter_turns))

    @cached_property
    def _canonical_grid(self) -> tuple[np.ndarray, np.ndarray]:
        rows, cols = np.indices(self.shape, dtype=np.float64)
        return self.to_canonical(cols, rows)

    def canonical_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """Canonical ``(U, V)`` of every original pixel (cached), shape ``self.shape``."""
        return self._canonical_grid

    def pull_back(self, mask_canonical: np.ndarray) -> np.ndarray:
        """Original pixels whose canonical position falls on a True mask pixel.

        Raises
        ------
        ValueError
            If the mask does not have the canonical shape.
        """
        mask_canonical = np.asarray(mask_canonical, dtype=bool)
        if mask_canonical.shape != self.canonical_shape:
            raise ValueError(f"mask shape {mask_canonical.shape} != canonical shape "
                             f"{self.canonical_shape}")
        u, v = self.canonical_coordinates()
        ui, vi = np.rint(u).astype(np.intp), np.rint(v).astype(np.intp)
        hc, wc = self.canonical_shape
        inside = (ui >= 0) & (ui < wc) & (vi >= 0) & (vi < hc)
        out = np.zeros(self.shape, dtype=bool)
        out[inside] = mask_canonical[vi[inside], ui[inside]]
        return out
