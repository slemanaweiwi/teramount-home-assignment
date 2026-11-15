"""Discovering and loading topography scans (``.npy`` height maps)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .errors import ScanLoadError

MIN_SIDE_PX = 64  # smaller scans cannot contain a channel structure


def natural_key(path: Path) -> tuple:
    """Sort key that orders ``2.npy`` before ``10.npy``."""
    parts = re.split(r"(\d+)", path.name)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def discover_scans(path: Path | str) -> list[Path]:
    """List the scans to analyse.

    Parameters
    ----------
    path
        A single ``.npy`` file, or a folder whose ``*.npy`` files are used.

    Returns
    -------
    list of Path
        Files in natural order (``1.npy, 2.npy, 10.npy``).

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ScanLoadError
        If ``path`` is not a ``.npy`` file or the folder contains none.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"data path not found: {path}")
    if path.is_file():
        if path.suffix.lower() != ".npy":
            raise ScanLoadError(f"not a .npy file: {path}")
        return [path]
    files = sorted((p for p in path.glob("*.npy") if p.is_file()), key=natural_key)
    if not files:
        raise ScanLoadError(f"no .npy files found in {path}")
    return files


def load_scan(path: Path | str, z_scale: float = 1.0) -> np.ndarray:
    """Load one height map as a float64 array in µm.

    Parameters
    ----------
    path
        ``.npy`` file holding a 2-D array of heights.
    z_scale
        Factor converting the stored heights to µm.

    Returns
    -------
    numpy.ndarray
        A new float64 array (rows = y, columns = x).

    Raises
    ------
    ScanLoadError
        If the file cannot be read (pickled objects are refused for safety), is
        not 2-D, is smaller than 64 px on a side, or holds no finite value.
    """
    path = Path(path)
    try:
        raw = np.load(path, allow_pickle=False)
    except (OSError, ValueError, EOFError) as exc:
        raise ScanLoadError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(raw, np.ndarray):
        raise ScanLoadError(f"{path.name} does not contain a single array")
    return check_height_map(raw, path.name) * z_scale


def check_height_map(z: object, name: str = "scan") -> np.ndarray:
    """Validate a height map and return it as a new float64 array.

    Used for files (:func:`load_scan`) and for arrays passed to the Python API
    directly, so both get the same clear error messages.

    Raises
    ------
    ScanLoadError
        If ``z`` is not a numeric 2-D array with at least ``MIN_SIDE_PX`` pixels
        on each side and at least one finite value.
    """
    try:
        arr = np.asarray(z)
    except ValueError as exc:  # e.g. a ragged nested list
        raise ScanLoadError(f"{name}: not a rectangular array of heights") from exc
    if arr.ndim != 2:
        raise ScanLoadError(f"{name}: expected a 2-D height map, got shape {arr.shape}")
    if min(arr.shape) < MIN_SIDE_PX:
        raise ScanLoadError(
            f"{name}: scan too small {arr.shape}, need >= {MIN_SIDE_PX} px per side"
        )
    try:
        out = np.array(arr, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ScanLoadError(f"{name}: heights are not numeric ({arr.dtype})") from exc
    if not np.isfinite(out).any():
        raise ScanLoadError(f"{name}: contains no finite height values")
    return out
