"""What the pixels dropped by a robust fit were.

A robust fit (Pivot planes, Xpander dome) drops pixels that do not follow the
surface. Their layout tells what they were:

* **isolated pixels**: spikes (dust glints, bad pixels); harmless once dropped;
* **long, 1-2 px thin clusters**: a scan line recorded at the wrong height;
* **compact clusters** larger than ``min_um2``: a *local feature*, a bump or a
  pit, which is dust or a real defect. Height data alone cannot tell the two
  apart, so a feature is reported, never silently ignored. Its pixels and a
  ``margin_um`` ring around it are excluded from the fit, so the feature's
  low shoulders cannot bias the result either.

Clustering runs on the pixels' positions in the original scan, where scan
lines are rows or columns.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

_EIGHT = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True, eq=False)
class OutlierClasses:
    """Classification of a fit's dropped pixels."""

    exclude: np.ndarray  # per point: inside a local feature or its margin
    feature_um2: float  # area of the largest local feature [µm²], 0 if none
    n_lines: int  # number of scan-line-shaped clusters


def classify_outliers(rows: np.ndarray, cols: np.ndarray, dropped: np.ndarray,
                      pixel_size_um: float, min_um2: float, margin_um: float,
                      ignore_edge: bool = False) -> OutlierClasses:
    """Sort the dropped pixels of a fit into spikes, scan lines and local features.

    Parameters
    ----------
    rows, cols
        Original-scan pixel indices of every point the fit considered.
    dropped
        True for the points the fit dropped.
    min_um2
        Smallest cluster counted as a local feature.
    margin_um
        Width of the ring excluded around each local feature.
    ignore_edge
        Do not count clusters touching the edge of the region (the points
        given): where a plane meets a wall its own edge rounding looks the
        same as a feature. Such pixels are still dropped by the fit.
    """
    rows = np.asarray(rows)
    cols = np.asarray(cols)
    exclude = np.zeros(rows.size, dtype=bool)
    if not np.any(dropped):
        return OutlierClasses(exclude, 0.0, 0)
    margin_px = int(np.ceil(margin_um / pixel_size_um))
    r0, c0 = rows.min() - margin_px, cols.min() - margin_px
    shape = (rows.max() - r0 + margin_px + 1, cols.max() - c0 + margin_px + 1)
    image = np.zeros(shape, dtype=bool)
    image[rows[dropped] - r0, cols[dropped] - c0] = True
    labels, n = ndimage.label(image, structure=_EIGHT)
    edge = np.zeros(shape, dtype=bool)
    if ignore_edge:
        region = np.zeros(shape, dtype=bool)
        region[rows - r0, cols - c0] = True
        edge = region & ~ndimage.binary_erosion(region, iterations=2)
    min_px = min_um2 / pixel_size_um**2
    features = np.zeros(shape, dtype=bool)
    largest, n_lines = 0, 0
    for k, sl in enumerate(ndimage.find_objects(labels), start=1):
        size = int(np.count_nonzero(labels[sl] == k))
        if size < min_px:
            continue
        height, width = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        on_edge = np.count_nonzero((labels[sl] == k) & edge[sl])
        if min(height, width) <= 2 and max(height, width) >= 10 * min(height, width):
            if on_edge <= size / 2:  # across the region, not a strip along its edge
                n_lines += 1  # one or two scan lines recorded at the wrong height
            continue
        if on_edge:
            continue  # touches the region edge: the plane's own edge rounding
        features[sl] |= labels[sl] == k
        largest = max(largest, size)
    if largest:
        yy, xx = np.ogrid[-margin_px:margin_px + 1, -margin_px:margin_px + 1]
        disk = xx**2 + yy**2 <= margin_px**2
        grown = ndimage.binary_dilation(features, structure=disk)
        exclude = grown[rows - r0, cols - c0]
    return OutlierClasses(exclude, largest * pixel_size_um**2, n_lines)
