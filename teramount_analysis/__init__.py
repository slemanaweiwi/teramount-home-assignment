"""Labeling and metrology of Pivot and Xpander elements in 3D topography scans.

Typical use::

    from teramount_analysis import Config, analyse_file
    result = analyse_file("15_files_task_2/3.npy", Config())
    print(result.status, result.metrics(Config())["xpander_rx_um"])
"""

from __future__ import annotations

from .config import Config
from .pipeline import analyse_dataset, analyse_file, analyse_scan
from .results import ScanResult

__version__ = "1.0.0"

__all__ = ["Config", "ScanResult", "__version__", "analyse_dataset", "analyse_file",
           "analyse_scan"]
