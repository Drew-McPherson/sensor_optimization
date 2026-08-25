from pathlib import Path
import re

import pandas as pd


def main() -> None:
    root = Path(".")
    aligned_path = root / "artifacts/aligned_phase1_temperature.csv"
    stats_path = root / "artifacts/phase1_average_statistics.csv"
    phase2_path = root / "artifacts/phase2_temperature_sensors.csv"

    print("aligned_exists", aligned_path.exists())
    print("stats_exists", stats_path.exists())
    print("phase2_exists", phase2_path.exists())

    df = pd.read_csv(aligned_path, nrows=5)
    sensor_cols = [
        c
        for c in df.columns
        if c.endswith("_temperature")
        and c != "average_temperature_all_devices"
        and c != "average_temperature_non_imputed_devices"
    ]
    print("sample_rows", len(df))
    print("sensor_cols", len(sensor_cols))

    if not phase2_path.exists():
        return

    phase2_df = pd.read_csv(phase2_path, nrows=5)
    phase2_columns = list(phase2_df.columns)

    local_margin_columns = [
        column for column in phase2_columns if re.match(r"^entry_.+_local_margin$", column)
    ]
    margin_score_columns = [
        column for column in phase2_columns if re.match(r"^event_.+_margin_proximity_score$", column)
    ]

    print("phase2_local_margin_cols", len(local_margin_columns))
    print("phase2_margin_proximity_cols", len(margin_score_columns))

    if local_margin_columns:
        raise ValueError("Phase 2 output still includes entry_*_local_margin columns")
    if not margin_score_columns:
        raise ValueError("Phase 2 output is missing event_*_margin_proximity_score columns")


if __name__ == "__main__":
    main()
