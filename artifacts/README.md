# Artifacts Folder

This folder stores generated outputs from the transformation and experiment pipeline.

## Expected files
1. raw_index.csv
2. aligned_phase1_temperature.csv
3. phase1_average_statistics.csv
4. phase2_temperature_sensors.csv
5. phase2_temperature_metrics.json
6. transformation_qc_report.csv
7. transformation_decisions.md

## phase1_average_statistics.csv
Summary statistics for Phase 1 average columns using only rows where
`snapshot_confidence > 0.75`.

Key columns:
1. `series_name`
2. `source_column`
3. `confidence_filter`
4. `filtered_snapshot_count`
5. `non_null_value_count`
6. `mean`
7. `std_dev`
8. `p05` to `p95` in 5-point increments

## Notes
1. Files in this folder are generated artifacts and may be overwritten between runs.
2. In a source-only GitHub repository, keep this README tracked but generate the artifact files locally instead of committing them.
