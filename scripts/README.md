# Transformation Script Usage

## Script
- `scripts/build_phase1_temperature.py`

## Purpose
Build the Phase 1 (temperature-only) aligned dataset with explicit audit artifacts, quality metrics, and gate checks.

## Inputs
1. Config: `config/transformation_defaults.yaml`
2. Data directory: `Data/files_csv`

Source discovery explicitly excludes the aggregate `temperature_raw.csv`
(case-insensitive filename match) before applying `--limit-files`. Timestamped
source CSVs retain their existing ordering; other discovery, parsing, first-wins
deduplication, and alignment rules are unchanged. The QC CSV records
`excluded_non_source_csv_filenames` as a JSON array, also exposed as a list in
stdout JSON and recorded in the decisions log. Only excluded files actually
present in the input directory are listed.

The 2026-11-03 gate-enforced rerun processed 9,909,343 temperature rows,
9,899,253 unique keys, and 10,090 excess duplicate rows (0.101823%, passing
the 0.5% gate). Its 218,148-row aligned output was byte-for-byte identical
to the previous aggregate-inclusive output: no timestamp, sensor availability,
temperature, or average changes. The quantitative comparison is in
`artifacts/phase1_duplicate_qc/phase1_source_exclusion_comparison.json`.

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

## Standalone Phase 1 Duplicate-Key QC

Run `python scripts\qc_phase1_duplicate_keys.py` to investigate the raw temperature
keys without running or changing the transformation pipeline. Defaults are
repository-relative; optional arguments are `--data-dir`, `--out-dir`, and
`--max-examples` (default 100, zero writes a header-only examples CSV).

Outputs are isolated in `artifacts/phase1_duplicate_qc/`:
- `qc_phase1_duplicate_summary.json`: counts, multiplicity distribution, exact
  value agreement/conflicts, conflicting-key spreads, source-file statistics,
  top 20 overlapping file pairs, and cross-file versus within-file attribution.
- `qc_phase1_duplicate_conflicts.csv`: conflicting keys ordered by decreasing
  spread, with per-file values/counts/first record numbers and the first value
  that Phase 1 would retain.

The stdlib-only script mirrors Phase 1 file ordering and schema validation,
including `int(float(Time))`, unmodified device IDs, and exact
`Sensor == "Temperature"`. Unlike transformation discovery, the standalone
audit's default intentionally includes the aggregate so the original all-files
investigation remains available. `rows_temperature` counts valid rows before
deduplication; raw/invalid temperature counts are separate. A duplicate key is
`(Time, DeviceId, Sensor)` and duplicate rows means occurrences beyond the first.
Identical/conflicting percentages use all duplicate keys as the denominator.
Conflicting-key difference is `max(Value) - min(Value)`; its mean is unweighted.
The secondary `1e-9` spread count never changes exact conflict classification.

Cross-file excess rows are `sum(distinct_files - 1)`; within-file excess rows
are `sum(multiplicity - distinct_files)`. They sum to all duplicate rows.
Keys that have both kinds are reported explicitly. "Primarily" means strictly
more than 50%, reported separately by duplicate keys and excess rows; cross-file
identical-key counts distinguish repeated observations from conflicting readings.

Zero-denominator metrics are JSON null. Phase 1 accepts non-finite float values;
this audit counts them explicitly, treats NaN as unequal, and reports/excludes
undefined or overflowing spreads instead of emitting invalid JSON. Non-finite
example values are strings. Temporary SQLite storage is cleaned on exit and
bounds memory for multi-gigabyte inputs; allow several GB of temporary disk.
Existing pipeline artifacts are never overwritten by the default command.

Validation: `python -B -m unittest scripts.test_qc_phase1_duplicate_keys -q`.

### Excluding the aggregate and checking record equivalence

Run `python scripts\qc_phase1_duplicate_keys.py --exclude-temperature-raw`.
The original all-files audit remains the default. The exclusion mode writes
three files under `artifacts/phase1_duplicate_qc/excluding_temperature_raw/`
without overwriting the original reports:
- `qc_phase1_duplicate_summary.json`: all duplicate statistics after excluding
  exactly `temperature_raw.csv`, conflicting-key spread bins and strict
  exceedance counts at 1e-9, 1e-6, 0.001, 0.01, 0.05, and 0.1 degrees C,
  gate evaluation, file inventory, and aggregate/source reconciliation.
- `qc_phase1_duplicate_conflicts.csv`: the capped conflicting examples for the
  reduced population, preserving exact parsed-float values and file provenance.
- `qc_phase1_unmatched_records.csv`: all unmatched full-record groups in both
  directions, with per-side counts, excess occurrences, aggregate record numbers,
  and timestamped-source file provenance. It is not capped by `--max-examples`
  and can be large; it is header-only when the record multisets match.

The duplicate-row rate is `100 * excess duplicate rows / valid temperature rows`.
The mode reads the gate from `config/transformation_defaults.yaml` (override
with `--config`) using the project's existing PyYAML dependency. It reports both
strictly below the configured threshold and Phase 1's actual rule:
round the rate to six decimals, then compare with `<=`. Empty temperature
populations have null gate results rather than being presented as passing.

Reconciliation compares exact parsed `(Time, DeviceId, Sensor, Value)` occurrence
counts between the aggregate and the union of timestamped source files; neither
side is deduplicated and no tolerance is applied. Timestamp recognition uses
Phase 1's filename parser. Other non-aggregate CSVs, if present, remain in the
duplicate statistics but are listed separately and excluded from reconciliation.
The inventory explicitly identifies all timestamped files. NaN never matches;
same-sign infinities match and are counted as non-finite. Invalid temperature
rows or invalid file schemas prevent a complete-equivalence conclusion.
Unmatched provenance describes all observations in a record group, not an
arbitrary choice of which identical occurrence is excess.

The 2026-11-03 full run found 9,909,343 temperature rows and 10,090 excess
duplicate rows (0.101823%, below the 0.5% gate). Exact record equivalence did
not hold: 9,118,190 occurrences matched, with 791,153 unmatched occurrences
in each direction. Inspect the JSON and unmatched CSV for details; matching
total row counts or key coverage alone does not establish value equivalence.

## Phase 2 Two-Sided Monitoring (US-3.23)

The shared engine in `scripts/phase2_monitoring.py` now uses policy
`two_sided_absolute_distance_equal_allowances`. At synchronization it stores
`abs(threshold - synchronized_mean)` as every participating sensor's allowance.
Sensors retain signed deviations for audit but trigger on
`abs(current_value - reference_value) >= allowance`. All simultaneous triggers
are counted and batched into one root collection. The separate root counts
one request, one response, and one state update per participating sensor.

The last synchronized root-known `SAFE`/`VIOLATED` state persists between
synchronizations. Equality with the global threshold is `VIOLATED`; zero
allowance conservatively triggers even on unchanged readings in the following
bucket. New references and allowances apply on the next bucket. An already
violated state no longer schedules a forced synchronization. Initialization,
membership-change/deferred synchronization, online-only fanout, and undefined
zero-observation buckets are retained.

### Required matched experiment

From the repository root:

```powershell
python -B -m scripts.phase2_monitoring
python -B -m unittest scripts.test_phase2_monitoring scripts.test_phase3_history scripts.test_phase3_monitoring -q
```

The command resolves repository-relative paths by default (`--root` can point
to another complete input checkout). It validates the approved configuration:
A/C/D/E/F/G, 2022-02-24T18:50:00+00:00 through 2022-03-10T15:53:00+00:00
inclusive, 19,984 consecutive minute buckets, matching epoch timestamps, and
complete finite readings. The threshold is read at round-trip precision from
the `phase3a_stable_cohort` p90 statistics row and checked against the config;
it is not embedded in the monitoring logic.

Only two compact files are written:

- `artifacts/phase3a_phase2_two_sided_baseline.json`: policy, experiment
  metadata, independent correctness counts, messages/categories, synchronization
  counts, historical comparison, commands, limitations, and SHA-256 provenance.
- `artifacts/phase3a_phase2_two_sided_events.csv`: completed synchronization
  timestamps, causes, trigger IDs, entry/exit reference means and allowances,
  root/oracle states, and message counts. Numeric event details are displayed
  at four decimals; all decisions and correctness checks use unrounded inputs.

The matched event CSV explicitly uses LF (`\n`) line endings on every operating
system (`lineterminator="\n"`), including its final newline. Its explicit column
order, synchronization-row order, values, and numeric precision are unchanged.
SHA-256 is calculated from the actual exported file, not reconstructed CSV text.

The historical `phase3a_phase2_baseline.json`, Phase 2 reports, Phase 3 code,
FMIC/SMIC results, US-3.21 validation, and US-3.22 results/plots are protected
by before/after hashes. The revised baseline is not substituted into any
published Phase 3 denominator.

### General Phase 2 notebook

`scripts/build_phase2_temperature_sensors.ipynb` and
`python scripts\run_phase2_notebook.py` still process the general observed-only
dataset using the `all_devices_observed` p90; they are not the matched-cohort
entry point. They now write separate reports:

- `artifacts/phase2_two_sided_temperature_sensors.csv`
- `artifacts/phase2_two_sided_temperature_metrics.json`
- `artifacts/phase2_two_sided_data_dictionary.csv`
- `artifacts/phase2_two_sided_sensor_reduction_analysis.csv`

### Schema and correctness migration

| Historical field | Revised field or interpretation |
|---|---|
| `entry_delta_global`, `exit_delta_global_if_resync` | `entry_root_allowance`, `exit_root_allowance_if_resync`: nonnegative absolute distance |
| `entry_{sensor}_local_margin` | `entry_{sensor}_local_allowance`: equal geometric allowance |
| `event_{sensor}_margin_proximity_score` | `event_{sensor}_allowance_remaining = allowance - abs(signed_deviation)`; zero reaches the trigger |
| `event_exit_delta_negative`, `event_resync_consumed_from_prior_row` | Removed; negative-margin cause/priority/scheduling is removed |
| `exit_resync_scheduled_next_row`, pending-cause fields | Only deferred initialization/membership causes; never scheduled by threshold state |
| Old synchronization-based `false_safe` | `legacy_event_false_negative`; not a root-state error |
| `false_alert`, `violation_detection_delay_buckets` | `legacy_event_false_alert`, `legacy_event_sync_delay_buckets` |
| Confusion/precision/recall/window-delay metrics | Explicit `legacy_event_*` metrics, separate from root-state correctness |

`root_known_state` is checked after bucket protocol actions against the
independent `oracle_global_state`, calculated from raw observations. The
`false_safe` and `false_violated` fields now mean actual root-state mismatches,
not the presence/absence of a same-minute synchronization. A quiet, correctly
known `VIOLATED` bucket is not an error. The matched runner stops on either
mismatch, missing root knowledge, input/membership failures, or unreconciled
messages. The oracle never controls communication. With no observations,
root/oracle output states are `UNDEFINED` and mismatch fields are blank.

Validation combines three complementary checks:

- **Consistency replay:** `check_trace_invariants()` reconstructs expected trace
  fields and state transitions from raw observations. It does not call the
  production builder or trust its synchronization flags, but reconstructs
  substantial parts of the same state machine. Replay checks (including those
  described in historical sections below) are not independent mathematical
  proof of algorithm correctness.
- **Independent correctness oracle:** `evaluate_root_states()` compares the
  root-known threshold state with the true centralized threshold state from raw
  observations, offline and without influencing monitoring or communication.
- **Synthetic regression tests:** independently specified fixtures, threshold
  boundaries, hand-counted transmissions, and deliberately injected defects
  check expected behavior and validator sensitivity.

### Validated outcome (2026-11-10)

The revised matched run has **9,159 messages** (753 triggers and 2,802 each of
requests, responses, and updates), **467 synchronizations**, 1,999 violated
buckets, and zero false-safe/false-violated states over all 19,984 buckets.
The historical signed-margin benchmark remains **38,087 messages / 2,107
synchronizations**. The aggregate changes are -28,928 messages and -1,640
synchronizations; these do not isolate the effect of removing scheduling from
the consequential absolute-trigger and synchronization-timeline changes.

The existing Phase 3 results are historical context only, not a fully controlled
clustering comparison with this revised baseline: moment-based allowances and
coordinator/cluster protocols remain potential confounders. No new Phase 3
experiment or universal performance claim is introduced.

Validation passed **104 Phase 2/Phase 3 tests**, including all Phase 2 notebook
code cells on synthetic inputs, root-state defect injection in both directions,
and protected-output checks. The fresh-process reproducibility check is automated:

```powershell
python -B -m unittest scripts.test_phase2_monitoring.MatchedProductionTests.test_fresh_process_reproducibility_and_lf_events -v
```

It invokes the existing matched-run CLI twice in separate Python subprocesses
with isolated temporary directories and identical deterministic synthetic inputs,
config, and threshold. The required 19,984-bucket grid uses constant violated/safe
segments, not a second production-data replay. Both executions must produce
byte-identical baseline JSON and LF-only event CSV, identical actual SHA-256
hashes, and the expected numerical/correctness results and hand-counted 42
transmissions / two synchronizations. Every input and historical/Phase 3 sentinel
is checked for preservation. No metadata fields are excluded from comparisons.
Cross-platform LF policy applies to the event CSV; complete baseline provenance
also includes platform-dependent relative path separators and input/code hashes.

One production replay confirmed that the maintenance change preserved every
numerical result above and all 23 protected file hashes. The exported events
equal the previous bytes with only CRLF replaced by LF (468 line endings).
The intentional event SHA-256 change is:

- Before (CRLF):
  `881cbd6d225533c2194372a470d9bf66969ae74a4e6eabaf9f60dcf386114fea`
- After (LF):
  `446d2e0b552ba603a0815e3275f5eba37513ac3298a63fb5129029dc3fba1d2e`

This is serialization normalization, not an algorithm regression. Monitoring
policy, synchronization logic, message accounting, and numerical experiment
results are unchanged. The regenerated baseline records the new event/code hashes
and unchanged protected before/after hashes.

## Historical Phase 2 Notebook (before US-3.23)

The remainder of this Phase 2 description records the original signed-margin
policy and historical artifact schema. It does **not** describe the current
engine, output paths, or root-state correctness semantics; use the US-3.23
instructions above for new runs. Historical output files are preserved unchanged.

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
6. Forced rows (initialization, membership changes, or pending negative-margin syncs) suppress operational triggers and keep all `event_{sensor}_resync_requested` bits at `0`. Local deviations/constraint comparisons are still calculated against valid entry references for reporting only.
7. Forced rows must report `trigger_message_count = 0`; only request/response/broadcast fanout is counted for that row's synchronization.
8. Logic uses unrounded values; exported numeric values are rounded to 4 decimal places for reporting.
9. The notebook-integrated report generation applies the 4-decimal reporting convention consistently to exported numeric columns in the row trace and report artifacts.
10. Correctness metrics use implemented row-local synchronization (`event_resync_performed`) rather than request generation (`event_any_sensor_requested_resync`).
11. Undefined global rows have blank `global_violation`, `false_safe`, and `false_alert`, with `UNDEFINED` constraint-state labels; they are excluded from confusion counts and break detection windows.
12. Synchronization is an operational action, not proof of a global threshold violation. Availability changes/startup may legitimately increase diagnostic false alerts.
13. `distributed_constraint_state` is `VIOLATING` if any online sensor has `local_deviation >= entry local allowance`. It is `FEASIBLE` only when all online sensors are comparable and none violates, `NOT_EVALUABLE` when comparison coverage is incomplete with no known violation, and `UNDEFINED` with no observations.
14. Local constraints use unrounded values even on reporting-only forced rows. The redundant `distributed_alert` column has been removed; use `event_resync_performed` for synchronization.

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
3. `distributed_constraint_state` reports sensor-local allowance violations, not synchronization or a root-confirmed global warning. Forced rows can report `VIOLATING` with zero emitted local triggers.
4. `false_safe` means the centralized system was violating and no re-sync was implemented on that same row.
5. `false_alert` means a re-sync was implemented on a row where the centralized system remained feasible.

### Metrics Output Highlights
`artifacts/phase2_temperature_metrics.json` includes:
1. Policy metadata (`boundary_policy`, `trigger_policy`), `threshold_source`, and `p90_threshold_full_precision` (the unrounded computational threshold). The existing `p90_threshold` remains a four-decimal presentation value.
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
7. The headline comparison is `communication_reduction_ratio_observed`, identified by `headline_reduction_metric` and `headline_baseline_definition`. Its baseline, `centralized_observed_sensor_messages`, counts one transmission per valid observed sensor per bucket; the ratio is undefined when no readings exist.
8. `centralized_sensor_messages` and `communication_reduction_ratio_primary` retain their existing configured-all-sensors counterfactual definitions for compatibility, not as the headline. The trigger-only legacy ratio is also unchanged.

Input validation:
- Phase 1 CSV empty fields are missing observations. Nonempty text (including `NA`, `NaN`, and whitespace), nonnumeric values, and infinities are rejected with the column and bucket rather than silently converted into departures.
- The existing monitoring module normalizes sensor and aggregate temperature columns; genuine in-memory missing values remain missing. No imputation or local floating-point comparison changes are introduced.

Metric interpretation note:
1. `false_negative_count` now counts violating rows with no implemented re-sync on the same row.
2. `false_positive_count` now counts implemented re-sync rows whose centralized state remained feasible.
3. These metrics are intentionally distinct from request-only warning counts.
4. Confusion counts, precision/recall, `false_safe`/`false_alert`, and detection delay retain their synchronization-based definitions for comparability. They are not actual global-warning accuracy metrics; delay is to the first synchronization in a global-violation window.
5. The corrected local-constraint state is not substituted as the diagnostic predictor. No separate root-warning subsystem or duplicate reason column is introduced.

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
	- First row: `reduction_percent_observed`, the headline observed-availability reduction, computed from message counts rather than a rounded ratio; undefined with no readings.
	- Supporting configured-sensor counterfactual baseline: `rows * sensor_count`.
	- Actual POC communications: `distributed_total_messages`.
	- Configured-sensor difference and compatibility reduction ratio/percent, explicitly labeled as non-headline.
	- Supporting communication breakdown by message type.
	- Observed-only baseline, reduction ratio/difference, initialization/membership attribution, and undefined-row counts.

### Membership regression tests
Approach A is the agreed Phase 2/FMIC/SMIC comparison protocol: keep the selected
cohort fixed while synchronizing on every change in observed contributors. Phase 3
reclusters at each completed synchronization. The existing Phase 2 engine already
implements this baseline; its `dynamic_observed_only` metadata describes changing
availability within the selected cohort, not a separate experimental variant.
Use identical cohort columns, readings, timestamps, threshold, and availability
rules in each algorithm. Do not disable availability synchronization or add
duplicate fixed/dynamic modes. Report savings under this shared policy and
availability costs by cause, not as an availability-free causal effect.

Run from the repository root using the selected Python environment:

```powershell
python -m unittest scripts.test_phase2_monitoring -v
```

Tests exercise startup, every departure/return, coinciding causes, next-row state,
all-offline/leading-empty buckets, unrounded boundary rules, signed/partial
cancellation, simultaneous triggers, cooling recovery, unequal three/four-sensor
states, forced-row reporting, deliberately corrupted traces, online-only traffic, and the
notebook's report generation and integrated validation. No clustering or alternate
Phase 2 run mode is introduced.
Specific denominator regressions verify that departure of a low-valued sensor
can raise the global mean above threshold without any remaining sensor warming,
and that a returning sensor changes the mean and receives a fresh next-row reference.

### Full trace validation

The existing monitoring module's `check_trace_invariants` independently replays
reference state from the original observations and threshold; it does not call
the production builder or advance state from its exported synchronization flags.
The builder validates unrounded values before four-decimal reporting. Notebook
Stage 4 validates the CSV against the same original inputs, allowing only the
four-decimal reporting tolerance for numeric fields. Exact trigger/threshold
decisions are recomputed from unrounded inputs, never inferred from rounded CSV
values. Errors identify the bucket and field/sensor. Checks cover reference and
allowance continuity, synchronized means, membership sets, local-state coverage,
causes/pending state, emitted triggers, and message totals.

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

## Phase 3A Stable-Cohort History and Clustering

`config/phase3a_experiment_config.json` is the authoritative Phase 3A definition:
it records the aligned input, fixed A/C/D/E/F/G cohort, inclusive interval,
19,984 expected buckets, 60-second sampling, baseline alpha 0.10, boundary
convention, and authoritative `phase3a_stable_cohort` P90. The P90 is generated
by `scripts/build_phase1_temperature.py` using the Phase 1 linear-interpolation
percentile rule and is retained at full precision. The historical
`all_devices_observed` statistics row remains unchanged.

`scripts/build_phase3_temperature_clustering.ipynb` runs Phase 3A over the fixed
cohort A, C, D, E, F, and G from 2022-02-24 18:50 UTC through 2022-03-10 15:53
UTC, inclusive. The input gate requires exactly 19,984 rows, matching endpoints,
unique timestamps in their original strictly increasing order, exact 60-second
timestamp and epoch steps, and finite readings for all six sensors. Invalid
input fails explicitly; it is not sorted, imputed, or dynamically adjusted.
US-3.18 produced the matched `artifacts/phase3a_phase2_baseline.json`.
US-3.19 reads and validates that existing baseline for comparison; normal
notebook execution no longer runs Phase 2 or overwrites the baseline.

At initialization and each completed FMIC synchronization, histories update
against the reference active on row entry, retain their accumulated value across
synchronizations, and use signed deviations. Normalization preserves signs and
uses the maximum history magnitude. The all-zero singleton fallback and the
source-aligned quality/greedy-selection rules remain unchanged. The full internal
candidate search is calculated as needed, but normal outputs retain only the
selected result.

The preserved `artifacts/phase3_sensor_history_events.csv` contains one row per clustering
event at the baseline `alpha=0.10`, including event/time/cause, raw and
normalized histories, fallback status, selected partition and quality, cluster
count, coordinator assignments, and authoritative threshold provenance. The
legacy `build_phase3a_history_events` helper also accepts `alpha_values` for
clustering-only regression coverage; it is not the production FMIC/SMIC alpha
sweep.
Coordinator reporting chooses the
lexicographically greatest cohort label in each cluster as a deterministic
descriptive convention. Normal runs do not generate
`artifacts/phase3_sensor_history_trace.csv` or any sensor-by-minute history
trace. Focused tests retain the detailed mathematical and history checks.

Run the Phase 3 regression suite with:

`python -m unittest scripts.test_phase3_history -v`

### End-to-end FMIC and SMIC (US-3.19 / US-3.20)

Run all cells in `scripts/build_phase3_temperature_clustering.ipynb`.
All Phase 3 history/normalization/clustering/input definitions and the independent
FMIC/SMIC allocation and shared monitoring engine live in clearly labeled cells in this one
notebook. The `phase3-history-implementation` and
`phase3-fmic-implementation` tags let separate automated tests execute those
definitions without running the production experiment. The former external
Phase 3 implementation modules have been removed; no duplicated core is kept.
The existing Phase 2 dependency remains for legacy helper regression coverage.
Normal execution first runs the US-3.21 prerequisite gate and then executes
the complete US-3.22 production sweep: 19 fresh full-length runs per method at alpha 0.05 through
0.95 in increments of 0.05. Each run uses the locked six-sensor cohort,
19,984 buckets, and authoritative full-precision P90. The sweep writes
`artifacts/phase3a_alpha_results.csv`,
`artifacts/phase3a_alpha_events.csv`, and
`artifacts/phase3a_comparison_summary.json`, plus three PNG comparisons for
messages, root synchronizations, and mean cluster count versus alpha.

The consolidated event file retains compact synchronization-level partitions
and monitor state. Cluster metrics include initialization consistently; mean
cluster size is total sensor memberships across all selected partitions
divided by total clusters across those events. Mean cluster count is the
arithmetic mean of the per-event counts. Alpha 0.10 is checked against the
existing FMIC/SMIC message categories, synchronization counts, correctness,
and event fingerprints; the existing fixed-alpha event and summary files are
never overwritten. The shared runner still defaults to alpha 0.10 for an
explicit original fixed-alpha run. Only correctness-passing results are eligible
for descriptive minimum-message alpha reporting. The single-dataset sweep is
not a statistical or out-of-sample tuning evaluation.

Plot generation requires `matplotlib` (included in `requirements.txt`). No
availability handling, full sensor-minute trace, or exhaustive merge-search
export is added.

The authoritative chapter is
[Clustering for Monitoring Distributed Data Streams](../Writing/Motivation/140516editor%20Book%20Chapter%20%28Last%20Version%29.pdf#page=14).
Section 1.4, printed p.10 (PDF p.14), defines the arithmetic mean of discounted
raw observations, not the signed clustering history:

```
S_n(m) = 0.5 * S_n(m-1) + v_n(t_m)
mu_n(m) = S_n(m) / m
W_n = abs(mu_n)                  # FMIC: first moment only (section 1.5.2)
w_n = N * W_n / sum(W)
delta_node(n) = w_n * delta_root
delta_coordinator(cluster) = mean(member node allowances)
```

Here `m` counts every post-initialization bucket, starting at t1 as in the
source's vector set, not just synchronization events. Moments persist across
synchronization. At initialization there are no post-initialization samples.
Specifically, the source vector set is
`V'_n(m) = {2^(-(m-i)) * v_n(t_i) : i=1,...,m}`. Summing that set gives the
recurrence above algebraically; the divisor is `m`, not `sum(2^(-(m-i)))`.
Thus this is not a weight-normalized EMA. Every post-t0 observation contributes,
including synchronization rows. Before any such observation, zero means are a
project initialization convention, not an arithmetic mean of an empty source set.

The notebook's **First-moment provenance and recurrence** cell preserves the
source location, derivation, and a three-observation hand table. For A readings
`[2,4,6]`, the final discounted vector set is `[0.5,2,6]`, sum `8.5`, mean
`8.5/3`; for B `[-4,2,3]` it is `[-1,1,3]`, sum `3`, mean `1`.
`FirstMomentTests.test_discounted_arithmetic_mean_is_not_history_or_ema`
checks the explicit vectors, discounted sums, sample counts, and means at each
step (mean tolerance 1e-12). The existing synchronization-persistence test
independently checks that samples and accumulated state survive synchronization.
Clustering instead uses reference-relative `h(t)=0.5*h(t-1)+(v(t)-reference)`;
that state is never substituted for `mu_n`.

If all weights are zero, use `w_n=1` for every sensor: this is an explicitly
labeled **project fallback**, not a source-defined formula. Individual zero
weights otherwise remain zero; no epsilon, floors, or tolerance reclassification
is used.

Use `delta_root = abs(threshold - synchronized_mean)` and absolute local
deviations; a coordinator takes the absolute value *after* averaging signed
member deviations, preserving cancellation. Local/coordinator equality triggers
checks (`>=`), matching the project's boundary convention. Root state is safe
below P90 and violated at/above P90; distance monitoring works on either side.
At exact P90, zero allowances cause checks on the following bucket. No Phase 2
negative-margin forced synchronization schedule is imported. Centralized truth
is a per-bucket validation oracle only, never a hidden communication trigger.
A false-safe is blocking and raises before successful artifacts are written.

Communication protocol:
- Root is a separate component, consistent with the matched Phase 2 baseline;
  coordinators remain sensors, chosen as the lexicographically highest member.
- All triggering non-coordinators report their reading once. Each triggered
  cluster is checked once per bucket; its coordinator requests/responses only
  from peers not already reporting. The coordinator's own reading is free.
- Every violating coordinator sends one alert to root. Multiple alerts in the
  same bucket cause one root synchronization. Alerts deliberately carry no raw
  readings, so root requests/retrieves all six sensor states, then sends one
  bundled monitoring-state update per sensor. Requests and responses are
  distinct transmissions; there is no self-transmission or hidden broadcast
  discount. This is actual project transmission accounting, not the chapter's
  sensor-as-root Appendix 2 broadcast approximation.
- References, partition, weights, and allowances remain fixed until sync.
  The synchronization row updates history against entry references before
  installing new references for the following row.

Outputs:
- `artifacts/phase3a_fmic_events.csv`: one compact row per FMIC synchronization,
  with history, normalization, selected partition/quality/coordinators,
  first moments, weights, node/coordinator/root allowances, and threshold.
- `artifacts/phase3a_fmic_summary.json`: configuration/input/baseline/event
  hashes, seven message-category totals, synchronizations, triggers/checks,
  cluster-size summaries, centralized violations, root-state correctness,
  and comparisons against matched Phase 2 and centralized transmissions.

FMIC correctness uses the root-known global state versus centralized truth;
`correctness_status` is `passed` only when both `false_safe_count` and
`false_violated_count` are zero. Either mismatch direction makes it `failed`.
This is not Phase 2's historical same-row-resynchronization diagnostic predictor.
The primary communication comparison uses identical data and transmission
units, but explicitly different monitoring architectures and state policies.

The validated baseline-alpha run uses 11,922 messages and 293 root
synchronizations: 68.697981% fewer messages than the 38,087-message matched
Phase 2 baseline. All 19,984 buckets pass centralized-state validation,
including 1,999 violated buckets, with zero false-safe/false-violated rows.
This is a result for the fixed experiment and alpha, not a general superiority
claim or an alpha-tuning result.

#### SMIC source interpretation and implementation

The **rendered original PDF** was checked, including
[Appendix 1, printed p.22/PDF p.26](../Writing/Motivation/140516editor%20Book%20Chapter%20%28Last%20Version%29.pdf#page=26)
and [its recurrence on printed p.24/PDF p.28](../Writing/Motivation/140516editor%20Book%20Chapter%20%28Last%20Version%29.pdf#page=28).
The chapter's `sigma^2` is the **unnormalized sum of squared deviations** of the
discounted observation vectors, not conventional population or sample variance.
Appendix 1 explicitly indexes `i=1..m`, resolving section 1.4's inconsistent
`i=0..m` notation. There is **no division by m or m-1**:

```
sigma_squared = sum((discounted_observation_i - mu)**2, i=1..m)
# k is the previous count; mu_old precedes the unchanged first-moment update.
sigma_squared_new = 0.25 * sigma_squared_old + k/(k+1) * (reading - 0.5*mu_old)**2
W_n = abs(mu_n) + sqrt(((m-1)/m) * sigma_squared_n)
```

`DiscountedSecondMoment` extends the existing first-moment implementation,
using the same raw observations, count, discount, and synchronization persistence.
The stable central-sum recurrence has only nonnegative terms; it does not
subtract accumulated squared sums or clamp negative values. Nonfinite/negative
states fail explicitly. No floating-point correction is required by this update.
At initialization (`m=0`), zero moments and equal weights remain a labeled
**project convention**; at `m=1` the central sum and second-moment contribution
are zero. The existing all-zero-total fallback and individual-zero rule apply.

The hand example A=`[2,4,6]` yields discounted central sums `0`, `9/2`, `97/6`,
and SMIC weights `2`, `4`, `17/6 + sqrt(97/9)`. Tests list the discounted
vectors, individual squared deviations, sums, conservative terms, and weights.
They also compare a longer independent explicit-vector calculation with the
constant-size running state.

`FMICMonitor` keeps its existing name/API for compatibility but now accepts
`weight_method="FMIC"` (default) or `"SMIC"`. It remains **one** node/coordinator/root
lifecycle; only the moment/weight strategy differs. The optional
`allocation_strategy(moment, partition, root_allowance)` hook permits controlled
same-allocation protocol equivalence tests. No separate SMIC protocol is kept.
Sensor moments or weights fit in existing root-sync responses; allocated
allowances fit in existing bundled updates, so no extra exchanges are charged.
This project counts transmissions, not scalar payload fields or bytes.
The global mean uses `math.fsum` to preserve the established FMIC/SMIC
arithmetic. The US-3.24 checker allows an absolute difference up to `1e-12`
for continuous snapshots only; synchronization flags, trigger sets,
threshold-state classifications, message counts, and synchronization timelines
remain exact, so a numerical tolerance cannot hide a decision change.
`capture_decisions=True` optionally retains a compact in-memory,
per-bucket trace of entry references/allowances/state, triggering sensor IDs,
synchronization decisions, post-sync state, and message counts. It is disabled
by default and does not write or alter production artifacts.

Execute all notebook cells to generate both outputs, or load its definition cells
and call `run_phase3a_fmic(REPO_ROOT)` / `run_phase3a_smic(REPO_ROOT)` separately.
Both use the authoritative config, input validation, p90 verification, matched
Phase 2 baseline, and their **own** event-driven schedules.

Additional compact outputs:
- `artifacts/phase3a_smic_events.csv`: one row per SMIC root synchronization,
  retaining the FMIC fields and adding second moments and conservative terms.
- `artifacts/phase3a_smic_summary.json`: the matched identity/accounting/correctness
  fields plus second-moment provenance/numerics, payload policy, and a clearly
  labeled preliminary Phase 2 comparison.

The validated SMIC alpha-0.10 run processes all **19,984** buckets, including
**1,999** centralized violated buckets, with **zero false-safe and false-violated**
counts. It uses **11,902 transmissions**, **293 synchronizations** (including
initialization), **3,514 coordinator checks**, and **420 escalations**.
This is **68.750492% fewer transmissions than matched Phase 2**, and **20 fewer
than FMIC** for this one experiment, not a final algorithm ranking.
Despite equal synchronization counts, each method has two synchronization
timestamps absent from the other method's schedule.
Full notebook execution preserves the existing FMIC events and summary
byte-for-byte, as well as the Phase 2 baseline, Phase 1 inputs/statistics/script,
and experiment config. No Phase 1/2 transformation, alpha sweep, or availability
handling changes are part of SMIC.
Validation passed 87 FMIC/SMIC/history/Phase 2 tests. A separate raw-input replay
confirmed all SMIC synchronization decisions, message categories, root-known
states, moment/weight/allowance snapshots, and counts; its independent
discounted-square-sum calculation differed from the stable central sum by at
most `2.274e-13`.

Tests:
`python -B -m unittest scripts.test_phase3_monitoring scripts.test_phase3_history scripts.test_phase2_monitoring -q`

### US-3.24 Phase 2 / Phase 3 protocol equivalence

Run the fixed-singleton comparison from the repository root:

```powershell
python -B -m scripts.phase3a_protocol_equivalence
```

The command requires the passing US-3.23 revised Phase 2 baseline, validates
its input/event hashes and current `scripts/phase2_monitoring.py` hash, then
independently runs the unrounded Phase 2 trace and the existing Phase 3
`FMICMonitor` over the locked 19,984-bucket A/C/D/E/F/G cohort. Phase 3 uses
the `fixed_singletons_equal_allowances` callback mode; the callback fixes and
checks the partition at every synchronization and ignores moment/history
values for partitions, allowances, triggers, and costs. Its internal numeric
alpha is ignored and is reported as not applicable. The root allowance is
`abs(threshold - synchronized_mean)` and is assigned equally to all sensors.

The run writes only:

- `artifacts/phase3a_protocol_equivalence_summary.json`: pass/fail checks,
  the first actionable mismatch and diagnostics, expected/actual trace lengths,
  mapped message totals, independent root-state oracle results, full
  input/config/code/baseline/test hashes, and protected-artifact before/after
  hashes.
- `artifacts/phase3a_protocol_equivalence_events.csv`: one compact row per
  initialization, synchronization, or trigger, including trigger IDs, entry
  and post-sync snapshots, root-known states, and mapped message counts.

The production command runs the equivalence, Phase 2, Phase 3 history, and
Phase 3 monitor suites. The equivalence tests include synthetic
boundary/lifecycle/ledger/negative-control checks and two fresh-process
production replays whose output bytes must match. A failed comparison writes
a failed summary and exits nonzero; US-3.25 must remain blocked. The focused
equivalence suite can be run separately with:

```powershell
python -B -m unittest scripts.test_phase3a_protocol_equivalence -q
```

Phase 2's trace has an opt-in `round_output=False` return mode for exact
snapshot comparison; its existing rounded default and notebook output behavior
are unchanged. Run the existing Phase 2/Phase 3 suites as well:

```powershell
python -B -m unittest scripts.test_phase2_monitoring scripts.test_phase3_history scripts.test_phase3_monitoring -q
```

The generated provenance includes every test module run by the production
command, with the executed test count and suite result recorded after the
regression run.

### US-3.25 weighting, clustering, and alpha evaluation

Run the US-3.25 workflow from the repository root:

```powershell
python -B -m unittest scripts.test_phase3a_us325 -q
python -B -m scripts.phase3a_us325
```

The runner first verifies the US-3.23/3.24 prerequisite artifacts and runs the
focused US-3.25, Phase 2, Phase 3 history/monitoring, and US-3.24 equivalence
regression suites. It reuses the saved, passing US-3.24 C0 result, runs fresh
FMIC-weighted and SMIC-weighted singleton controls, and starts the 19-alpha
FMIC/SMIC grid only after those controls pass correctness and message-accounting
gates. Each clustered configuration uses fresh monitor state.

All new files use the `phase3a_us325_` prefix, leaving historical Phase 2,
FMIC/SMIC, US-3.21, and US-3.22 outputs untouched:

- `artifacts/phase3a_us325_control_results.csv`: exactly C0/C1/C2, with
  alpha marked not applicable and per-control message composition.
- `artifacts/phase3a_us325_alpha_results.csv`: the 38 fresh clustered runs,
  including the revised Phase 2 comparison, synchronization/check outcomes,
  repeated-check counts, and pathway message totals/shares.
- `artifacts/phase3a_us325_control_cluster_size_summary.csv` and
  `artifacts/phase3a_us325_cluster_size_summary.csv`: compact check outcomes
  and within-cluster transmissions grouped by checked cluster size.
- `artifacts/phase3a_us325_event_snapshots.csv`: compact control, alpha=0.10,
  and exploratory minimum-alpha synchronization snapshots.
- C0's retained per-event snapshots remain available in
  `artifacts/phase3a_protocol_equivalence_events.csv`; the summary records this
  reused source rather than copying the validated C0 event history.
- `artifacts/phase3a_us325_comparison_summary.json`: control/alpha comparisons,
  the prespecified and exploratory configuration table, provenance, focused
  test count, replay outcomes, and interpretation limits.
- Four plots: messages, root synchronizations, mean cluster count, and
  communication composition versus alpha. Singleton controls are references,
  not alpha-dependent runs.

The summary distinguishes locally resolved checks from root synchronizations
avoided and reports consecutive repeats only for adjacent buckets with
unchanged membership and no intervening synchronization. It also documents
the unchanged `abs(deviation) >= allowance` zero-allowance behavior. A fresh
process replays FMIC and SMIC at alpha=0.10 and compares their event
fingerprints; prerequisite and historical artifact hashes are checked before
and after the workflow.
