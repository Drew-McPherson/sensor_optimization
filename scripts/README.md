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
count, coordinator assignments, and authoritative threshold provenance. To run the full 19-value alpha
sweep for tuning, pass `alpha_values=PHASE3_ALPHA_VALUES` to
the legacy `build_phase3a_history_events` helper (not FMIC's runtime schedule).
Coordinator reporting chooses the
lexicographically greatest cohort label in each cluster as a deterministic
descriptive convention. Normal runs do not generate
`artifacts/phase3_sensor_history_trace.csv` or any sensor-by-minute history
trace. Focused tests retain the detailed mathematical and history checks.

Run the Phase 3 regression suite with:

`python -m unittest scripts.test_phase3_history -v`

### End-to-end FMIC (US-3.19)

Run all cells in `scripts/build_phase3_temperature_clustering.ipynb`.
All Phase 3 history/normalization/clustering/input definitions and the independent
FMIC allocation/monitoring engine live in clearly labeled cells in this one
notebook. The `phase3-history-implementation` and
`phase3-fmic-implementation` tags let separate automated tests execute those
definitions without running the production experiment. The former external
Phase 3 implementation modules have been removed; no duplicated core is kept.
The existing Phase 2 dependency remains for legacy helper regression coverage.
Normal execution uses only alpha 0.10. No SMIC, alpha tuning, availability
handling, full sensor-minute trace, or exhaustive merge-search export is added.

The authoritative chapter is
`Writing/Motivation/140516editor Book Chapter (Last Version).pdf`.
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
this is not Phase 2's historical same-row-resynchronization diagnostic predictor.
The primary communication comparison uses identical data and transmission
units, but explicitly different monitoring architectures and state policies.

The validated baseline-alpha run uses 11,922 messages and 293 root
synchronizations: 68.697981% fewer messages than the 38,087-message matched
Phase 2 baseline. All 19,984 buckets pass centralized-state validation,
including 1,999 violated buckets, with zero false-safe/false-violated rows.
This is a result for the fixed experiment and alpha, not a general superiority
claim or an alpha-tuning result.

Tests:
`python -B -m unittest scripts.test_phase3_monitoring scripts.test_phase3_history scripts.test_phase2_monitoring -q`
