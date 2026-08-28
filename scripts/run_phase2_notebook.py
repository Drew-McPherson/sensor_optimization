#!/usr/bin/env python3
"""Run all code cells from build_phase2_temperature_sensors.ipynb."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def _missing_modules(modules: list[str]) -> list[str]:
    return [name for name in modules if importlib.util.find_spec(name) is None]


def _ensure_dependencies(repo_root: Path) -> None:
    required_modules = ["numpy", "pandas"]
    missing = _missing_modules(required_modules)
    if not missing:
        return

    requirements_path = repo_root / "requirements.txt"
    if not requirements_path.exists():
        raise RuntimeError(
            "Missing Python packages: "
            + ", ".join(missing)
            + "\nrequirements.txt not found at: "
            + str(requirements_path)
            + "\nInterpreter in use: "
            + sys.executable
        )

    print(
        "Missing dependencies detected: "
        + ", ".join(missing)
        + "\nAttempting install from requirements.txt..."
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
        check=True,
    )

    still_missing = _missing_modules(required_modules)
    if still_missing:
        raise RuntimeError(
            "Dependencies still missing after installation: "
            + ", ".join(still_missing)
            + "\nInterpreter in use: "
            + sys.executable
            + "\nTry running manually:\n"
            + f"{sys.executable} -m pip install -r {requirements_path}"
        )


def _preflight(repo_root: Path, notebook_path: Path) -> None:
    related_docs = [
        "Distributed_Monitoring_POC_Project_Plan.md",
        "scripts/README.md",
        "instructions/PYTHON_ENV_SETUP_GUIDE.md",
        "instructions/distributed_monitoring_notebook_required_changes.md",
    ]
    print("Related documentation:")
    for doc in related_docs:
        print(f"- {repo_root / doc}")

    missing = []
    for rel_path in [
        Path("artifacts/aligned_phase1_temperature.csv"),
        Path("artifacts/phase1_average_statistics.csv"),
    ]:
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            missing.append(str(abs_path))

    if missing:
        raise FileNotFoundError(
            "Missing required input artifact(s):\n- " + "\n- ".join(missing)
        )

    if not notebook_path.exists():
        raise FileNotFoundError(f"Notebook not found: {notebook_path}")

    aligned_required_columns = {"bucket_epoch", "bucket_time_utc", "average_temperature_all_devices"}
    stats_required_columns = {"series_name", "p90"}

    aligned_path = repo_root / "artifacts/aligned_phase1_temperature.csv"
    stats_path = repo_root / "artifacts/phase1_average_statistics.csv"

    with aligned_path.open("r", encoding="utf-8", newline="") as f:
        aligned_columns = set(next(csv.reader(f), []))
    with stats_path.open("r", encoding="utf-8", newline="") as f:
        stats_columns = set(next(csv.reader(f), []))

    missing_aligned = sorted(aligned_required_columns - aligned_columns)
    missing_stats = sorted(stats_required_columns - stats_columns)

    if missing_aligned:
        raise ValueError(
            "aligned_phase1_temperature.csv is missing required columns: "
            + ", ".join(missing_aligned)
        )
    if missing_stats:
        raise ValueError(
            "phase1_average_statistics.csv is missing required columns: "
            + ", ".join(missing_stats)
        )

    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [c for c in data.get("cells", []) if c.get("cell_type") == "code"]
    if not code_cells:
        raise ValueError(f"Notebook has no code cells: {notebook_path}")


def _run_notebook_cells(repo_root: Path, notebook_path: Path) -> int:
    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    cells = [c for c in data.get("cells", []) if c.get("cell_type") == "code"]

    namespace = {"__name__": "__main__"}

    # Ensure notebook code resolves artifact paths from repository root.
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(repo_root)
        for idx, cell in enumerate(cells):
            code = "".join(cell.get("source", []))
            if not code.strip():
                continue
            try:
                exec(
                    compile(code, f"<phase2-notebook-cell-{idx}>", "exec"),
                    namespace,
                    namespace,
                )
            except Exception as exc:  # pragma: no cover - diagnostic path
                first_line = ""
                for line in code.splitlines():
                    if line.strip():
                        first_line = line.strip()
                        break
                raise RuntimeError(
                    "Phase 2 notebook execution failed at code cell "
                    + str(idx + 1)
                    + (
                        f" (starts with: {first_line[:120]})"
                        if first_line
                        else ""
                    )
                ) from exc
    finally:
        os.chdir(original_cwd)

    print(f"Executed {len(cells)} notebook code cells from {notebook_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run or preflight-check Phase 2 notebook execution."
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate dependencies and required inputs without executing notebook cells.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    notebook_path = repo_root / "scripts" / "build_phase2_temperature_sensors.ipynb"

    _ensure_dependencies(repo_root)
    _preflight(repo_root, notebook_path)
    print("Phase 2 preflight passed.")

    if args.preflight_only:
        return 0

    return _run_notebook_cells(repo_root, notebook_path)


if __name__ == "__main__":
    raise SystemExit(main())
