from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(".")
    aligned_path = root / "artifacts/aligned_phase1_temperature.csv"
    stats_path = root / "artifacts/phase1_average_statistics.csv"

    print("aligned_exists", aligned_path.exists())
    print("stats_exists", stats_path.exists())

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


if __name__ == "__main__":
    main()
