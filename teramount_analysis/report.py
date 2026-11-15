"""Results table (CSV) and console summary."""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .results import METRIC_COLUMNS, FaultReport, ScanResult

CSV_COLUMNS: tuple[str, ...] = (
    "file", "status", "error", "warnings", *METRIC_COLUMNS,
    "geometric_flags", "nominal_flags", "statistical_flags", "faulty",
)


def _cell(value: object) -> str:
    """Floats with up to 6 significant digits; NaN as an empty cell."""
    if isinstance(value, float):
        return f"{value:.6g}" if math.isfinite(value) else ""
    return str(value)


def write_csv(results: Sequence[ScanResult], path: Path, config: Config) -> None:
    """Write one row per scan with the columns of :data:`CSV_COLUMNS`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for r in results:
            metrics = r.metrics(config)
            faults = r.faults or FaultReport()
            faulty = "" if r.status == "failed" else ("yes" if faults.faulty else "no")
            writer.writerow([
                r.file, r.status, r.error, ";".join(r.warnings),
                *(_cell(metrics[c]) for c in METRIC_COLUMNS),
                ";".join(faults.geometric), ";".join(faults.nominal),
                ";".join(faults.statistical), faulty,
            ])


def summary_table(results: Sequence[ScanResult], config: Config | None = None) -> str:
    """Fixed-width table of the key numbers, one line per scan."""
    config = config or Config()

    def num(value: float, fmt: str) -> str:
        return format(value, fmt) if math.isfinite(value) else "-"

    header = (f"{'file':<14}{'status':<9}{'step um':>9}{'Rx um':>9}{'Ry um':>9}"
              f"{'rot deg':>9}{'tilt deg':>10}  flags")
    lines = [header, "-" * len(header)]
    for r in results:
        m = r.metrics(config)
        faults = r.faults or FaultReport()
        flags = ", ".join(faults.geometric + faults.nominal + faults.statistical
                          + tuple(f"warning: {w}" for w in r.warnings))
        lines.append(
            f"{r.file:<14}{r.status:<9}{num(m['pivot_height_diff_um'], '9.3f')}"
            f"{num(m['xpander_rx_um'], '9.1f')}{num(m['xpander_ry_um'], '9.1f')}"
            f"{num(m['rotation_deg'], '9.3f')}{num(m['tilt_total_deg'], '10.4f')}  {flags}")
    return "\n".join(lines)
