"""Analyse Teramount topography scans.

Usage::

    py run.py --data 15_files_task_1 --name task1
    py run.py --data 15_files_task_2 --name task2
    py run.py --data path/to/other/scans          # any folder of .npy height maps
    py run.py --help                              # all options
"""

from teramount_analysis.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
