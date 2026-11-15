"""Command-line interface.

Example::

    py run.py --data 15_files_task_2 --name task2

writes ``results/task2_results.csv`` and one diagnostic figure per scan in
``results/figures/task2/``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .errors import ScanLoadError
from .figures import save_scan_figure
from .io import discover_scans
from .pipeline import analyse_dataset
from .report import summary_table, write_csv
from .results import ScanResult

_DEFAULTS = Config()


def build_parser() -> argparse.ArgumentParser:
    """Argument parser of ``run.py``."""
    p = argparse.ArgumentParser(
        prog="run.py",
        description="Label the Pivot and Xpander in 3D topography scans (.npy height maps), "
                    "correct tilt and rotation, and measure them.",
    )
    p.add_argument("--data", required=True, type=Path,
                   help="folder of .npy scans (all are analysed, in natural order) or one .npy")
    p.add_argument("--out", type=Path, default=Path("results"),
                   help="output folder (default: results)")
    p.add_argument("--name", help="name used for the outputs (default: the data folder's name)")
    p.add_argument("--pixel-size", type=float, default=_DEFAULTS.pixel_size_um, metavar="UM",
                   help=f"lateral pixel size in µm (default: {_DEFAULTS.pixel_size_um})")
    p.add_argument("--z-scale", type=float, default=_DEFAULTS.z_scale, metavar="F",
                   help="factor converting stored heights to µm (default: 1)")
    p.add_argument("--no-tilt-correction", action="store_true",
                   help="remove only a constant height offset, not the tilt")
    p.add_argument("--no-rotation-correction", action="store_true",
                   help="do not measure or undo the in-plane rotation")
    p.add_argument("--no-figures", action="store_true", help="skip the diagnostic figures")
    p.add_argument("--nominal-step", type=float, metavar="UM",
                   help=f"nominal Pivot step (default: {_DEFAULTS.nominal_pivot_step_um})")
    p.add_argument("--nominal-radius", type=float, metavar="UM",
                   help=f"nominal Xpander radius (default: {_DEFAULTS.nominal_radius_um})")
    p.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING"), default="INFO",
                   help="console logging detail (default: INFO)")
    return p


def config_from_args(args: argparse.Namespace) -> Config:
    """Build the analysis configuration from parsed arguments."""
    overrides: dict[str, object] = {
        "pixel_size_um": args.pixel_size,
        "z_scale": args.z_scale,
        "correct_tilt": not args.no_tilt_correction,
        "correct_rotation": not args.no_rotation_correction,
    }
    if args.nominal_step is not None:
        overrides["nominal_pivot_step_um"] = args.nominal_step
    if args.nominal_radius is not None:
        overrides["nominal_radius_um"] = args.nominal_radius
    return Config(**overrides)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the analysis. Exit code 0 = done, 1 = every scan failed, 2 = bad input."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    try:
        config = config_from_args(args)
        paths = discover_scans(args.data)
    except (ValueError, FileNotFoundError, ScanLoadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    data = Path(args.data)
    name = args.name or (data.stem if data.is_file() else data.resolve().name)
    figure_dir = args.out / "figures" / name

    def draw(result: ScanResult) -> None:
        save_scan_figure(result, figure_dir / f"{Path(result.file).stem}.png", config)

    results = analyse_dataset(paths, config, on_scan=None if args.no_figures else draw)
    csv_path = args.out / f"{name}_results.csv"
    write_csv(results, csv_path, config)

    print(summary_table(results, config))
    print(f"\nresults: {csv_path}")
    if not args.no_figures:
        print(f"figures: {figure_dir}")
    return 1 if all(r.status == "failed" for r in results) else 0
