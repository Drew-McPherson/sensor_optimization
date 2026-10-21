# Transformation Script Usage

## Script
- `scripts/build_phase1_temperature.py`

## Purpose
Build the Phase 1 (temperature-only) aligned dataset with explicit audit artifacts, quality metrics, and gate checks.

## Inputs
1. Config: `config/transformation_defaults.yaml`
2. Data directory: `Data/files_csv`

## Outputs
1. `artifacts/raw_index.csv`
2. `artifacts/aligned_phase1_temperature.csv`
3. `artifacts/phase1_average_statistics.csv`
4. `artifacts/transformation_qc_report.csv`
5. `artifacts/transformation_decisions.md`

For a source-only repository, these outputs are generated locally and may be absent until you run the pipeline.

## Key Columns In `aligned_phase1_temperature.csv`
1. `average_temperature_all_devices`
	- Mean temperature across all observed per-device values that remain in the row after staleness filtering.
	- Missing device values stay blank rather than being filled by carry-forward or other synthetic values.
2. `average_temperature_all_devices_count`
	- Number of device values included in `average_temperature_all_devices` for that bucket.
	- Added for auditability so reviewers can see the sample size behind each average.

## Phase 1 Average Statistics Artifact
`artifacts/phase1_average_statistics.csv` is generated from aligned Phase 1 rows
using a strict filter of `snapshot_confidence > 0.75`.

Rules:
1. The statistics are unweighted; `snapshot_confidence` is only used as a cutoff.
2. Metrics include mean, standard deviation, and percentiles every 5 points
   from `p05` through `p95`.
3. The artifact includes the observed-only all-device series:
	- all-device observed average (`average_temperature_all_devices`)

## Run Commands
### Smoke test (small subset)
`python scripts/build_phase1_temperature.py --limit-files 5`

### Full run (no gate enforcement)
`python scripts/build_phase1_temperature.py`

### Full run with gate enforcement (non-zero exit on failure)
`python scripts/build_phase1_temperature.py --enforce-gates`

## Notes
1. The script logs JSON summary to stdout for machine review.
2. The decisions log is append-only and records run metadata and gate results.
3. Install dependency if needed: `pip install pyyaml`

## Phase 2 Notebook

### Notebook
- `scripts/build_phase2_temperature_sensors.ipynb`

### Purpose
Run deterministic Phase 2 local-deviation monitoring over aligned Phase 1 snapshots.

The Phase 2 implementation follows the definitive chapter and operational policies
in the project plan. Its tested state machine is in `scripts/phase2_monitoring.py`;
the notebook remains the execution/reporting entry point.

### Inputs
1. `artifacts/aligned_phase1_temperature.csv`
2. `artifacts/phase1_average_statistics.csv`

### Outputs
1. `artifacts/phase2_temperature_sensors.csv`
2. `artifacts/phase2_temperature_metrics.json`
3. `artifacts/phase2_data_dictionary.csv` (generated in notebook Stage 3)
4. `artifacts/phase2_sensor_reduction_analysis.csv` (generated in notebook Stage 3)

For a source-only repository, these outputs are generated locally and may be absent until you run the notebook or `scripts/run_phase2_notebook.py`.

### Logic Summary
1. Read p90 from `phase1_average_statistics.csv` each run using the all-devices observed series `all_devices_observed`.
2. Count initial synchronization on the first bucket with valid observations; leading empty buckets remain undefined without look-ahead.
3. Compute the row-level observed global average for each minute as the arithmetic mean of the current row's observed sensor readings.
4. Detect every departure/return from the current versus previous online set, at the first missing/returning bucket after Phase 1 freshness filtering. Status detection costs no messages.
5. Initialization, membership changes, and pending negative-margin causes force one combined synchronization and suppress local-trigger evaluation. Negative-margin cause has primary precedence; all causes are retained.
6. Otherwise compute `delta_v_i(t) = v_i(t) - v_i(t0_i)` and evaluate local trigger per online sensor using `local_deviation >= local_margin`.
7. Perform one re-sync event for the minute when any local trigger fires.
8. Count N requests, N responses, and N threshold updates for N currently online sensors, including startup. Offline sensors generate zero traffic.
9. Apply updated synchronized state starting next row.
10. If global margin after synchronization is negative, schedule re-sync for the next row.
11. Use canonical boundary policy for aligned outputs: safe `<` boundary, violated `>=` boundary.
12. Export per-row trace plus diagnostic metrics.
13. Generate integrated report artifacts (`phase2_data_dictionary.csv` and `phase2_sensor_reduction_analysis.csv`) in Stage 3 from the final row/metrics artifacts.
14. Run integrated Stage 4 validation checks inside the notebook for smoke and export-policy invariants.
15. With no online sensors, global state/threshold labels are undefined, no traffic is generated, and synchronization remains pending until valid readings return. There is no minimum online count.

### Canonical Policies
1. Global violation label in aligned output: `observed_global_average >= p90_threshold`.
2. The Phase 2 implementation uses the strict all-devices p90 threshold source while computing the row-level observed global average directly from the current minute's sensor readings.
3. Local trigger rule: `event_{sensor}_local_deviation >= entry_{sensor}_local_margin`.
4. Exported row trace includes `event_{sensor}_margin_proximity_score = entry_delta_global - event_{sensor}_local_deviation`; positive is acceptable and negative is violating.
5. Trigger evaluation always uses `entry_*` state; any resulting state update is emitted as `exit_*` and applied on the next row.
6. Forced rows (initialization, membership changes, or pending negative-margin syncs) do not run local trigger evaluation and must keep all `event_{sensor}_resync_requested` bits at `0`.
7. Forced rows must report `trigger_message_count = 0`; only request/response/broadcast fanout is counted for that row's synchronization.
8. Logic uses unrounded values; exported numeric values are rounded to 4 decimal places for reporting.
9. The notebook-integrated report generation applies the 4-decimal reporting convention consistently to exported numeric columns in the row trace and report artifacts.
10. Correctness metrics use implemented row-local synchronization (`event_resync_performed`) rather than request generation (`event_any_sensor_requested_resync`).
11. Undefined global rows have blank `global_violation`, `false_safe`, and `false_alert`, with `UNDEFINED` constraint-state labels; they are excluded from confusion counts and break detection windows.
12. Synchronization is an operational action, not proof of a global threshold violation. Availability changes/startup may legitimately increase diagnostic false alerts.

### Phase 2 Row Invariants
1. `entry_*` fields are the state used to evaluate the current row.
2. `observed_*` fields are the current minute-bucket values.
3. `event_*` fields record what happened during the current minute.
4. `exit_*` fields describe the state that leaves the row and becomes the next row's `entry_*` state.
5. `transition_summary` is a compact audit field placed near the front of the row.

### Phase 2 Output Highlights
`artifacts/phase2_temperature_sensors.csv` includes:
1. Global and transition fields:
	- `transition_summary`
	- `observed_global_average`
	- `entry_xbar_t0`
	- `entry_delta_global`
	- `exit_xbar_t0_if_resync`
	- `exit_delta_global_if_resync`
2. Per-sensor fields for each sensor (for example A-H):
	- `observed_{sensor}_temperature`
	- `entry_{sensor}_reference_value`
	- `event_{sensor}_local_deviation`
	- `entry_{sensor}_local_margin`
	- `event_{sensor}_margin_proximity_score`
	- `event_{sensor}_resync_requested`
3. Re-sync control and reason fields:
	- `event_triggering_sensor_names`
	- `event_resync_request_count`
	- `event_any_sensor_requested_resync`
	- `event_resync_performed`
	- `event_resync_reason`
	- `event_exit_delta_negative`
	- `exit_resync_scheduled_next_row`
4. Communication fields:
	- `trigger_message_count`
	- `request_message_count`
	- `response_message_count`
	- `broadcast_message_count`
	- `total_message_count`
5. Correctness observability fields:
	- `centralized_constraint_state`
	- `distributed_constraint_state`
	- `distributed_alert`
	- `false_safe`
	- `false_alert`
	- `violation_detection_delay_buckets`
6. Membership and pending-state fields:
	- `observed_online_sensor_names`, `observed_online_sensor_count`
	- `event_departing_sensor_names`, `event_returning_sensor_names`, `event_membership_changed`
	- `event_resync_causes`, `event_resync_triggered_by_membership_change`, `event_initialization_performed`
	- `exit_resync_pending`, `exit_resync_pending_causes`, `global_state_evaluable`
7. Cause attribution: `membership_resync_message_count`, `initialization_message_count`. Causes may overlap; these counters are not added to transmission totals.

Correctness interpretation:
1. `event_any_sensor_requested_resync` remains the request-generation trace for local sensor warnings.
2. `event_resync_performed` is the canonical implemented-mitigation trace for the current minute.
3. `distributed_alert` mirrors `event_resync_performed` for row-level correctness reporting.
4. `false_safe` means the centralized system was violating and no re-sync was implemented on that same row.
5. `false_alert` means a re-sync was implemented on a row where the centralized system remained feasible.

### Metrics Output Highlights
`artifacts/phase2_temperature_metrics.json` includes:
1. Policy metadata (`boundary_policy`, `trigger_policy`).
2. Confusion matrix plus diagnostic recall and precision, using `event_resync_performed` as the predicted-positive rule.
3. Communication totals by category and two reduction ratios:
	- primary ratio using `distributed_total_messages`
	- legacy comparator using `distributed_trigger_messages`
4. Re-sync event counters and detection delay by actual-positive windows.
5. Observability aliases and counters:
	- `false_negative_count` (alias of confusion `fn`)
	- `false_positive_count` (alias of confusion `fp`)
	- `false_safe_count` (sum of row-level `false_safe`)
	- `false_alert_count` (sum of row-level `false_alert`)
6. Membership policy metadata, evaluable/undefined row counts, initialization/membership synchronization counts, and cause-attributed traffic.
7. `centralized_sensor_messages` remains the `rows * configured_sensor_count` counterfactual. `centralized_observed_sensor_messages` counts only online observations and supplies `communication_reduction_ratio_observed`; the ratio is undefined when no readings exist.

Metric interpretation note:
1. `false_negative_count` now counts violating rows with no implemented re-sync on the same row.
2. `false_positive_count` now counts implemented re-sync rows whose centralized state remained feasible.
3. These metrics are intentionally distinct from request-only warning counts.

Observability note:
1. These correctness fields are reporting-only in the current phase.
2. The run is not failed when false-safe or false-alert rows are present.

## Phase 2 Integrated Report Generation

CSV-first report artifacts are generated directly in Stage 3 of
`scripts/build_phase2_temperature_sensors.ipynb` from:
1. `artifacts/phase2_temperature_sensors.csv`
2. `artifacts/phase2_temperature_metrics.json`

Generated report artifacts:
1. `artifacts/phase2_data_dictionary.csv`
2. `artifacts/phase2_sensor_reduction_analysis.csv`

Output content:
1. `phase2_data_dictionary.csv`
	- One row per raw Phase 2 field.
	- Explains what each field measures and how it is calculated.
2. `phase2_sensor_reduction_analysis.csv`
	- Baseline if sensors communicated every minute: `rows * sensor_count`.
	- Actual POC communications: `distributed_total_messages`.
	- Difference and primary reduction ratio/percent.
	- Supporting communication breakdown by message type.
	- Observed-only baseline, reduction ratio/difference, initialization/membership attribution, and undefined-row counts.

### Membership regression tests
Run from the repository root using the selected Python environment:

```powershell
python -m unittest scripts.test_phase2_monitoring -v
```

Tests exercise startup, every departure/return, coinciding causes, next-row state,
all-offline/leading-empty buckets, boundary rules, online-only traffic, and the
notebook's report generation and integrated validation. No clustering or alternate
Phase 2 run mode is introduced.

## Phase 2 Integrated Validation

Validation is now embedded directly in `scripts/build_phase2_temperature_sensors.ipynb` as Stage 4.

Stage 4 checks:
1. Required Phase 1 and Phase 2 artifact presence.
2. Required schema families and ordering in `phase2_temperature_sensors.csv`.
3. 4-decimal numeric reporting policy checks.
4. Required metrics policy keys.
5. Required report artifacts exist (`phase2_data_dictionary.csv`, `phase2_sensor_reduction_analysis.csv`).
6. `phase2_data_dictionary.csv` field coverage and schema checks.
7. `phase2_sensor_reduction_analysis.csv` schema and minimum-metric checks.
8. Cross-artifact consistency checks between exported rows and metrics totals.
9. Public-schema enforcement that prevents internal control fields from appearing in exported row outputs.
