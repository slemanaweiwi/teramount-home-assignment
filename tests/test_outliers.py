"""Tests for classifying the pixels a robust fit dropped."""

from __future__ import annotations

import numpy as np

from teramount_analysis.outliers import classify_outliers

P = 0.252


def _grid(shape=(200, 200)):
    rows, cols = np.indices(shape)
    return rows.ravel(), cols.ravel()


def test_isolated_spikes_are_neither_features_nor_lines():
    rows, cols = _grid()
    dropped = np.zeros(rows.size, dtype=bool)
    dropped[np.random.default_rng(0).choice(rows.size, 60, replace=False)] = True
    c = classify_outliers(rows, cols, dropped, P, min_um2=1.0, margin_um=3.0)
    assert c.feature_um2 == 0.0 and c.n_lines == 0 and not c.exclude.any()


def test_a_compact_blob_is_a_feature_and_is_excluded_with_a_margin():
    rows, cols = _grid()
    blob = (rows - 100) ** 2 + (cols - 100) ** 2 <= 16  # radius 4 px = 1 um: 3.2 um2
    c = classify_outliers(rows, cols, blob, P, min_um2=1.0, margin_um=3.0)
    assert c.feature_um2 == np.count_nonzero(blob) * P**2
    excluded_radius = np.sqrt(((rows - 100) ** 2 + (cols - 100) ** 2)[c.exclude].max()) * P
    assert 3.5 < excluded_radius < 4.5  # blob radius 1 um + 3 um margin
    assert c.n_lines == 0


def test_a_long_thin_cluster_is_a_scan_line_not_a_feature():
    rows, cols = _grid()
    line = (rows == 50) & (cols > 20) & (cols < 180)
    c = classify_outliers(rows, cols, line, P, min_um2=1.0, margin_um=3.0)
    assert c.n_lines == 1 and c.feature_um2 == 0.0 and not c.exclude.any()


def test_no_dropped_pixels():
    rows, cols = _grid((10, 10))
    c = classify_outliers(rows, cols, np.zeros(rows.size, dtype=bool), P, 1.0, 3.0)
    assert c.feature_um2 == 0.0 and c.n_lines == 0 and c.exclude.shape == rows.shape


def test_clusters_touching_the_region_edge_can_be_ignored():
    rows, cols = _grid()
    edge_blob = (rows - 2) ** 2 + (cols - 100) ** 2 <= 16  # at the region's top edge
    kept = classify_outliers(rows, cols, edge_blob, P, 1.0, 3.0)
    ignored = classify_outliers(rows, cols, edge_blob, P, 1.0, 3.0, ignore_edge=True)
    assert kept.feature_um2 > 0 and ignored.feature_um2 == 0.0 and not ignored.exclude.any()


def test_a_thin_strip_along_the_region_edge_is_not_a_scan_line():
    rows, cols = _grid()
    strip = (rows == 1) & (cols > 20) & (cols < 180)  # along the top edge
    inner = (rows == 100) & (cols > 20) & (cols < 180)  # across the interior
    assert classify_outliers(rows, cols, strip, P, 1.0, 3.0, ignore_edge=True).n_lines == 0
    assert classify_outliers(rows, cols, inner, P, 1.0, 3.0, ignore_edge=True).n_lines == 1
