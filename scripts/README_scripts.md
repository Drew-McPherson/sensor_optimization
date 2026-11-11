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

## US-2.15 Matched Phase 2 Baseline

The active Phase 2 scope is only the locked `phase3a_stable_cohort` experiment:
A/C/D/E/F/G, 19,984 consecutive 60-second buckets, the authoritative cohort
P90, and the existing shared two-sided engine. The baseline is 9,159
transmissions, 467 synchronizations, and zero false-safe/false-violated root
states. It remains at its original paths until the later workflow stories
coordinate the cutover.

Create the one-time local checkpoint with:

```powershell
py -3.13 -B -m scripts.phase2_checkpoint_us215
```

The tool refuses to overwrite an existing checkpoint. It stores the complete
SHA-256/source-control inventory and original files in
`artifacts/phase2_baseline_us215/`, together with the unrounded
19,984-bucket trace and pre-change validation report. The generated folder is
Git-ignored. Phase 2's 43 existing tests pass. At checkpoint time the Phase 3 saved-results gate failed because its validation
record was stale or incomplete; the checkpoint preserves that historical
failure. Current Phase 3 production was subsequently regenerated.

Notebook disposition:

- Original general-dataset notebook:
  `scripts/build_phase2_temperature_sensors.ipynb`
- Archived general-dataset notebook:
  `artifacts/phase2_archive/scripts/phase2_general_dataset_archive.ipynb`
- Archived runner:
  `artifacts/phase2_archive/scripts/run_phase2_general_dataset_archive.py`
- No separate historical signed-margin notebook was identified in `scripts/`.
  The original signed-margin result is the distinct
  `artifacts/phase3_operational/references/phase3a_phase2_baseline.json`.

The existing general-dataset notebook is a revised US-3.23 two-sided workflow
over the full observed-only Phase 1 dataset; it is not the matched experiment
or the historical signed-margin implementation. Its code names outputs
`phase2_two_sided_*`, while the loose root `phase2_temperature_metrics.json`
records negative-margin scheduling and the debug log reports a different
threshold/source series. Those files are mixed-generation archive material,
not current matched results. The workbook is preserved; no comments,
drawings, or external links were found, but cell-level equivalence with the CSV
has not been established. US-2.16 verified the matched entry points before
renaming the old notebook and runner. They were later moved to the artifact
archive; restore them to `scripts/` before running their original paths. They
are not the supported matched workflow or a frozen signed-margin implementation.

US-2.15 did not move or delete artifacts or change the monitoring algorithm.
The current matched notebook workflow is documented below.

## US-2.16 Matched Phase 2 Notebooks

The maintained execution and test entry points use the same import-safe engine
as Phase 3:

| Notebook | Purpose |
|---|---|
| [`phase2_implement.ipynb`](phase2_implement.ipynb) | Runs the shared engine and publishes the summary to `artifacts/phase2_outputs/` and events to `artifacts/phase2_operational/`. |
| [`phase2_test.ipynb`](phase2_test.ipynb) | Runs the Phase 2 regression suites without skips, reproduces the saved run in isolation, and writes the independent operational validation receipt without changing the summary or events. |
| [`phase2_analyze.ipynb`](phase2_analyze.ipynb) | Validates current saved summary/event provenance and presents the matched experiment, existing communication comparison, correctness, synchronization diagnostics, event-field guide, and limitations without running code that produces results or exporting files. |

Open each notebook with the project Python kernel and use **Restart Kernel and
Run All**. The implementation notebook runs only `phase3a_stable_cohort`; no
full-dataset run or second state machine is present. After implementation,
execute the test notebook; then run the analysis notebook against those saved
results. Tests report failures explicitly. Analysis requires current files and
matching provenance and never falls back to root-level or archived results. It
does not run tests, monitor data, or write project artifacts. The standard
unittest suite can also be run from the repository root:

```powershell
python -B -m unittest scripts.test_phase2_monitoring -q
```

The equivalent command-line publication and validation sequence is:

```powershell
python -B -m scripts.shared_monitoring_engine publish
python -B -m scripts.shared_monitoring_engine validate
```

The shared import-safe `scripts/shared_monitoring_engine.py` contains both the
monitoring algorithm and the Phase 2 publication/validation contract. Phase 2
and Phase 3 import the same engine; importing it does not run an experiment.
Validation is still a separate command and independently produces the receipt.
The earlier `phase2_monitoring.py` and `phase2_artifacts.py` modules were merged
into this engine; they are not current entry points.

The schema-versioned `phase2_summary.json` links relatively to
`phase2_events.csv` and `phase2_validation.json`. JSON is UTF-8 with indentation
and a trailing newline; event CSV uses LF line endings. Publication replaces
events before the summary, and the independent receipt binds the exact summary,
events, shared engine, artifact code, tests, configuration and scientific inputs.
Analysis and Phase 3 reject missing, failed, incomplete, stale or mixed evidence.
The signed-margin reference remains separately owned by Phase 3 operational
references and is not loaded from an archive. The superseded files are in `artifacts/phase2_archive/`; Phase 3 production
was regenerated with a current independent receipt after the migration.

For clean-kernel headless execution from PowerShell, use the same Python
environment as the notebook kernel. Executed notebook copies go to the
temporary directory rather than the maintained source files:

```powershell
python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --output-dir "$env:TEMP" scripts\phase2_implement.ipynb
python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --output-dir "$env:TEMP" scripts\phase2_test.ipynb
python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --output-dir "$env:TEMP" scripts\phase2_analyze.ipynb
```

The old full-dataset notebook and runner are preserved in
[`phase2_archive/scripts/`](../artifacts/phase2_archive/scripts/) for reference.
They retain their original path assumptions and must be restored to `scripts/`
before execution; current consumers and tests do not require them.

## US-2.19 Final Equivalence and Archive Independence

On 2026-11-11, the final shared engine's complete unrounded 19,984-row,
82-column trace serialized identically to the US-2.15 checkpoint, including
triggers, synchronization causes, states, reference values, allowances and
message categories. The uncompressed trace SHA-256 in both cases was
`122ce369249f2db5aa090ad7b5c11e41ab12c7d3675334ff87b036d047eb96ba`.
All 19,984 root-state evaluations passed, with 9,159 messages and 467
synchronizations. The completed-event CSV matched the checkpoint byte-for-byte.

All three Phase 2 notebooks and the Phase 3 analysis notebook passed with clean
kernels, and analysis left the artifact inventory and file hashes unchanged.
Phase 2 independent validation passed 42 tests without skips; a separately
generated Phase 3 validation receipt passed 163 tests without skips. Phase 3
production, saved-result checks, and six fresh-process replays passed. Two
additional fresh Phase 2 processes reproduced the exact saved summary and event
bytes; the regression suite also checks missing, failed, stale and mixed
evidence.

The workflow was repeated in a hash-verified isolated copy without
`phase2_archive/`, `phase2_current/`, the retired notebook/runner, or the old
root-level Phase 2 paths. Phase 2 notebooks, Phase 3 production, saved checks,
replays, and analysis passed there as well. The Phase 3 results, cluster sizes,
snapshots, and C0 events were byte-identical across the isolated run, current
workspace and preserved pre-cutover bundle. Run IDs, timestamps, receipts and
manifest metadata may change when runs are repeated.

**Manual removal queue:** `artifacts/phase2_archive/`, including
`scripts/phase2_general_dataset_archive.ipynb` and
`scripts/run_phase2_general_dataset_archive.py` relative to that archive.
Preserve anything you need before manually removing it; the workbook and
general-dataset files have mixed provenance and are not declared redundant.
The Git-ignored `artifacts/phase2_baseline_us215/` is a separate recovery
checkpoint, not part of that queue. Back it up separately before moving it out
of the workspace. No archive or checkpoint was deleted for verification.

## Phase 2 Two-Sided Monitoring (US-3.23)

The shared engine in `scripts/shared_monitoring_engine.py` now uses policy
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
python -B -m scripts.shared_monitoring_engine
python -B -m unittest scripts.test_phase2_monitoring -q
python -B -m scripts.phase3_test --checks behavior
```

The command resolves repository-relative paths by default (`--root` can point
to another complete input checkout). It validates the approved configuration:
A/C/D/E/F/G, 2022-02-24T18:50:00+00:00 through 2022-03-10T15:53:00+00:00
inclusive, 19,984 consecutive minute buckets, matching epoch timestamps, and
complete finite readings. The threshold is read at round-trip precision from
the `phase3a_stable_cohort` p90 statistics row and checked against the config;
it is not embedded in the monitoring logic.

The current contract uses three compact files:

- `artifacts/phase2_outputs/phase2_summary.json`: policy, experiment
  metadata, independent correctness counts, messages/categories, synchronization
  counts, historical comparison, commands, limitations, and SHA-256 provenance.
- `artifacts/phase2_operational/phase2_events.csv`: completed synchronization
  timestamps, causes, trigger IDs, entry/exit reference means and allowances,
  root/oracle states, and message counts. Numeric event details are displayed
  at four decimals; all decisions and correctness checks use unrounded inputs.
- `artifacts/phase2_operational/phase2_validation.json`: independent test and
  reproduction receipt, generated separately after publication.

The matched event CSV explicitly uses LF (`\n`) line endings on every operating
system (`lineterminator="\n"`), including its final newline. Its explicit column
order, synchronization-row order, values, and numeric precision are unchanged.
SHA-256 is calculated from the actual exported file, not reconstructed CSV text.

The historical `phase3a_phase2_baseline.json`, Phase 2 reports, Phase 3 code,
FMIC/SMIC results, US-3.21 validation, and US-3.22 results/plots are protected
by before/after hashes. The revised baseline is not substituted into any
published Phase 3 denominator.

### General Phase 2 notebook (archived)

The archived `phase2_archive/scripts/phase2_general_dataset_archive.ipynb` and
its runner process the general
observed-only dataset using the `all_devices_observed` p90; they are not the
matched-cohort entry point. Restore them to `scripts/` to use their original
execution paths. The notebook source applies the revised two-sided
engine and writes separately named reports:

- `artifacts/phase2_two_sided_temperature_sensors.csv`
- `artifacts/phase2_two_sided_temperature_metrics.json`
- `artifacts/phase2_two_sided_data_dictionary.csv`
- `artifacts/phase2_two_sided_sensor_reduction_analysis.csv`

The loose root-level exports and root console logs retain older names and are
not assumed to be outputs of the current notebook. The saved metrics describe
negative-margin scheduling at P90 24.343381 (`all_devices_observed`). The
available run logs instead record P90 24.316875
(`non_imputed_devices_only`) or 24.315625 (`all_devices_including_imputed`).
Keep these mixed-generation files as archive candidates until their provenance
and workbook/CSV equivalence are resolved. The original signed-margin matched
baseline remains separate under `phase3_operational/references/`; its
byte-identical `phase3_archive/` copy is not a runtime dependency.

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

## Historical Phase 2 Notebook Documentation (before US-3.23)

The remainder of this Phase 2 description records the original signed-margin
policy and historical artifact schema. It does **not** describe the current
engine, output paths, or root-state correctness semantics; use the US-3.23
instructions above for new runs. Historical output files are preserved unchanged.

### Archived notebook
- `artifacts/phase2_archive/scripts/phase2_general_dataset_archive.ipynb`

This is the revised US-3.23 general-dataset notebook preserved under its
archive name, not a recovered pre-US-3.23 signed-margin notebook. No separate
historical signed-margin notebook was identified.

### Purpose
Run deterministic Phase 2 local-deviation monitoring over aligned Phase 1 snapshots.

The Phase 2 implementation follows the definitive chapter and operational policies
in the project plan. Its tested state machine is in `scripts/shared_monitoring_engine.py`;
the notebook remains the execution/reporting entry point.

### Inputs
1. `artifacts/aligned_phase1_temperature.csv`
2. `artifacts/phase1_average_statistics.csv`

### Outputs
1. `artifacts/phase2_temperature_sensors.csv`
2. `artifacts/phase2_temperature_metrics.json`
3. `artifacts/phase2_data_dictionary.csv` (generated in notebook Stage 3)
4. `artifacts/phase2_sensor_reduction_analysis.csv` (generated in notebook Stage 3)

These historical outputs may be absent in a source-only checkout. The archive
runner is preserved in `artifacts/phase2_archive/scripts/`; restore it to
`scripts/` before execution. It does not produce the current matched results.

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

CSV-first report artifacts in this historical section were generated directly
in Stage 3 of the archived notebook from:
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
states, forced-row reporting, deliberately corrupted traces, online-only traffic,
malformed/non-finite inputs, hand-counted messages, and injected oracle defects.
They do not execute or depend on archived notebook cells. No clustering or
alternate Phase 2 run mode is introduced.
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

Validation for the archived general-dataset workflow was embedded in its
notebook as Stage 4. The current matched validation is in
[`phase2_implement.ipynb`](phase2_implement.ipynb) and
[`phase2_test.ipynb`](phase2_test.ipynb).

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

**Current execution:** use the [three-file workflow](#us-332-three-file-workflow-and-verified-cutover).
Current output formats follow the [approved six-file artifact contract](#us-333-approved-phase3-artifact-bundle);
story-numbered file inventories below describe their preserved historical formats.
The original notebook and six compatibility modules have been retired. The
US-3.18 through US-3.31 sections below retain scientific context and migration
history; archived validation/recovery commands apply only inside their restored
historical checkout. They are not additional active entry points.

`config/phase3a_experiment_config.json` is the authoritative Phase 3A definition:
it records the aligned input, fixed A/C/D/E/F/G cohort, inclusive interval,
19,984 expected buckets, 60-second sampling, baseline alpha 0.10, boundary
convention, and authoritative `phase3a_stable_cohort` P90. The P90 is generated
by `scripts/build_phase1_temperature.py` using the Phase 1 linear-interpolation
percentile rule and is retained at full precision. The historical
`all_devices_observed` statistics row remains unchanged.

[`phase3_implement.py`](phase3_implement.py) runs Phase 3A over the fixed
cohort A, C, D, E, F, and G from 2022-02-24 18:50 UTC through 2022-03-10 15:53
UTC, inclusive. The input gate requires exactly 19,984 rows, matching endpoints,
unique timestamps in their original strictly increasing order, exact 60-second
timestamp and epoch steps, and finite readings for all six sensors. Invalid
input fails explicitly; it is not sorted, imputed, or dynamically adjusted.
US-3.18 produced the matched `artifacts/phase3a_phase2_baseline.json`.
US-3.19 reads and validates that existing baseline for comparison; normal
production execution does not overwrite that historical baseline.

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

`python -B -m scripts.phase3_test --checks behavior`

The old test-module names are retired; maintained coverage is in
[`phase3_test.py`](phase3_test.py). See the
[coverage map and check selectors](#us-330-consolidated-testing-and-saved-output-verification).

### End-to-end FMIC and SMIC (US-3.19 / US-3.20)

This describes the **historical** execution path, not the current default.
The original production notebook is recoverable from the US-3.27 checkpoint,
not retained as an active entry point. For saved-result methodology, tables,
and charts use [`phase3_analyze.ipynb`](phase3_analyze.ipynb), described under
[US-3.31](#us-331-saved-results-only-analysis-notebook).
All Phase 3 history/normalization/clustering/input definitions and the independent
FMIC/SMIC allocation and shared monitoring engine now live in
[`phase3_implement.py`](phase3_implement.py). Tests use ordinary Python imports
from the same module; tagged-cell loading and transitional runners are retired.
No duplicated core is kept.
The existing Phase 2 dependency remains for legacy helper regression coverage.
The explicit `--historical-sweep` mode first runs the US-3.21 prerequisite gate and then executes
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

To regenerate the original fixed-alpha outputs explicitly, import
`run_phase3a_fmic` / `run_phase3a_smic` from `scripts.phase3_implement`
and call them with the repository root. Full notebook execution instead runs
the historical sweep and preserves the existing fixed-alpha reference files.
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
`python -B -m scripts.phase3_test --checks behavior`

Phase 2's independent suite remains `python -B -m unittest scripts.test_phase2_monitoring -q`.

### US-3.24 Phase 2 / Phase 3 protocol equivalence

Run the fixed-singleton comparison from the repository root:

```powershell
python -B -m scripts.phase3_implement --equivalence --output-dir "$env:TEMP\phase3-equivalence\phase3_outputs"
```

The command requires the passing US-3.23 revised Phase 2 baseline, validates
its input/event hashes and current `scripts/shared_monitoring_engine.py` hash, then
independently runs the unrounded Phase 2 trace and the existing Phase 3
`FMICMonitor` over the locked 19,984-bucket A/C/D/E/F/G cohort. Phase 3 uses
the `fixed_singletons_equal_allowances` callback mode; the callback fixes and
checks the partition at every synchronization and ignores moment/history
values for partitions, allowances, triggers, and costs. Its internal numeric
alpha is ignored and is reported as not applicable. The root allowance is
`abs(threshold - synchronized_mean)` and is assigned equally to all sensors.

The compatibility command forwards to `scripts.phase3_implement.equivalence_main`.
It performs runtime equivalence only, not regression-suite execution. Its output
directory defaults to `artifacts/phase3_current/`. The run writes only:

- `artifacts/phase3_current/phase3a_protocol_equivalence_summary.json`: pass/fail checks,
  the first actionable mismatch and diagnostics, expected/actual trace lengths,
  mapped message totals, independent root-state oracle results, full
  input/config/code/baseline/test hashes, and protected-artifact before/after
  hashes.
- `artifacts/phase3_current/phase3a_protocol_equivalence_events.csv`: one compact row per
  initialization, synchronization, or trigger, including trigger IDs, entry
  and post-sync snapshots, root-known states, and mapped message counts.

Regression tests run separately. The equivalence tests include synthetic
boundary/lifecycle/ledger/negative-control checks and two fresh-process
production replays whose output bytes must match. A failed comparison writes
a failed summary and exits nonzero; US-3.25 must remain blocked. The focused
equivalence suite can be run separately with:

```powershell
python -B -m unittest scripts.phase3_test.SyntheticProtocolTests scripts.phase3_test.ProductionReproducibilityTests -q
```

Phase 2's trace has an opt-in `round_output=False` return mode for exact
snapshot comparison; its existing rounded default and notebook output behavior
are unchanged. Run the existing Phase 2/Phase 3 suites as well:

```powershell
python -B -m scripts.phase3_test --record-validation artifacts\phase3_current\phase3_validation.json
```

Runtime provenance includes the current test-source hashes but does not claim
that tests ran. Unified production requires a separate current validation receipt
as described under [US-3.29](#us-329-unified-production-execution).

### US-3.25 weighting, clustering, and alpha evaluation

Run the US-3.25 workflow from the repository root:

```powershell
python -B -m scripts.phase3_test --record-validation artifacts\phase3_current\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_current\phase3_validation.json
```

The runner first verifies the separately executed canonical Phase 3 and external
Phase 1/2 validation receipt
against current code, inputs, and configuration. It validates the US-3.23
prerequisite and reuses C0 only when the US-3.24 summary and event hashes are
current; otherwise it genuinely regenerates and verifies C0 in the output
directory. It runs fresh
FMIC-weighted and SMIC-weighted singleton controls, and starts the 19-alpha
FMIC/SMIC grid only after those controls pass correctness and message-accounting
gates. Each clustered configuration uses fresh monitor state.

All evaluation files use the `phase3a_us325_` prefix in the selected output
directory (default `artifacts/phase3_current/`), leaving root-level historical
artifacts untouched. Paths below are relative to that output directory:

- `phase3a_us325_control_results.csv`: exactly C0/C1/C2, with
  alpha marked not applicable and per-control message composition.
- `phase3a_us325_alpha_results.csv`: the 38 fresh clustered runs,
  including the revised Phase 2 comparison, synchronization/check outcomes,
  repeated-check counts, and pathway message totals/shares.
- `phase3a_us325_control_cluster_size_summary.csv` and
  `phase3a_us325_cluster_size_summary.csv`: compact check outcomes
  and within-cluster transmissions grouped by checked cluster size.
- `phase3a_us325_event_snapshots.csv`: compact control, alpha=0.10,
  and exploratory minimum-alpha synchronization snapshots.
- C0's retained per-event snapshots remain available in
  `phase3a_protocol_equivalence_events.csv`; a valid root-level cache is copied
  into the selected output directory, never overwritten at its original path.
- `phase3a_us325_comparison_summary.json`: control/alpha comparisons,
  the prespecified and exploratory configuration table, provenance, focused
  test count, replay outcomes, and interpretation limits.
- Since US-3.31, the five existing charts are rendered inline by
  `phase3_analyze.ipynb`: messages, root synchronizations, mean cluster count,
  communication composition versus alpha, and singleton communication composition.
  Singleton controls remain references, not alpha-dependent runs. PNG export
  is explicit and separate; production no longer writes these PNGs.

The summary distinguishes locally resolved checks from root synchronizations
avoided and reports consecutive repeats only for adjacent buckets with
unchanged membership and no intervening synchronization. It also documents
the unchanged `abs(deviation) >= allowance` zero-allowance behavior. A fresh
process replays C1/C2 and FMIC/SMIC at alpha=0.10 and alpha=0.65, comparing
correctness, synchronization counts, seven message categories, totals, and
event fingerprints. The initial protected-artifact inventory is captured
before prerequisite checks; partial failures attempt a final integrity check
and atomically write `phase3a_us325_failed_configurations.json` in the output directory.
Successful runs explicitly replace that diagnostic with a zero-failure record.

### US-3.26 validation hardening and reporting

The US-3.25 runner rejects incomplete or failed alpha grids before exploratory
ranking, verifies the saved scientific regression fingerprints before updating
US-3.25 outputs, and records test-source hashes plus the external Phase 3/1/2
validation receipt. Its
compact completion record is
`phase3a_us326_completion_summary.json` in the output directory; it separates validation
status and unresolved issues from scientific interpretation. The singleton
communication-composition plot is now rendered in the analysis notebook from
saved validated controls.

Use the two commands above: regression validation is separate from production.
The old orchestration facade is retired; use the canonical implementation
with its independent validation receipt. Production
validates all 38 clustered configurations and fixed controls, generates compact
scientific/validation reports, and verifies all six independent fresh-process
replays. Presentation is a separate saved-results-only notebook.

### US-3.27 pre-consolidation checkpoint

The verified local baseline is in
[`artifacts/phase3_baseline_us327/`](../artifacts/phase3_baseline_us327/).
This generated directory is intentionally ignored by Git; it contains archived
copies, not additional maintained Phase 3 entry points. No production Python or
notebook implementation was changed for this story, and no files were staged or
committed.

- `original_checkpoint.zip`: 85 original source, configuration, documentation,
  and root-level artifact files, including required untracked scripts/config.
  Every archive member was checked against `checkpoint_inventory.json`.
- `reference_workspace/`: isolated copy used for validation, with freshly
  validated prerequisite/report metadata. Its code remains the archived code.
- `baseline_report.json`: Git state, selected interpreter/package versions,
  actual commands/results, dependency/provenance inventory, prerequisite issue,
  and full configuration evidence index.
- `full_matrix_evidence/`: raw initialization/synchronization event JSON and
  compressed per-bucket decision JSONL for C0/C1/C2 and all 38 clustered runs.
  Capture uses the existing monitor's observational `capture_decisions` option;
  non-C0 raw event fingerprints match saved scientific fingerprints. C0's saved
  fingerprint identifies the equivalence CSV instead, so its raw JSON hash is
  recorded separately and fresh per-bucket Phase 2 equivalence is checked.
- `verification_results.json`: independent archive, evidence, reconciliation,
  original-file integrity, and scientific CSV byte comparisons.
- `checkpoint_seal.json`: hashes of the checkpoint contents after validation.
  Verify it before using the baseline for later migration comparisons.
- `capture_us327.py` and `verify_us327.py`: archived one-off capture/verification
  procedures, not production dependencies. Capture refuses to overwrite a new
  checkpoint destination; verification can be rerun against the original root.

The six-module existing suite passed **139 tests**. Fresh US-3.24 equivalence
passed **122 tests** and the revised production runner's five-module suite passed
**135 tests**; these suites overlap and their counts must not be added as unique
coverage. All six production fresh-process replays passed. The full matrix has
41 configurations, 819,344 decisions, and 16,210 initialization/synchronization
events. Six fresh scientific CSVs (controls, alpha results, both cluster-size
summaries, selected snapshots, and equivalence events) were byte-identical to
their archived originals.

#### Pre-existing prerequisite issue

The first production attempt correctly failed because the original US-3.24
summary's notebook SHA-256 was stale. The original source and saved artifacts
were not edited to bypass this gate. Instead, the unchanged equivalence command
was run in the isolated copy, passed its comparison and regression tests, and
regenerated genuine current provenance with byte-identical scientific events.
The revised production workflow then passed without disabling any gate.
The initial failure log/report and fresh validation log are retained.

**The original working-tree US-3.24 summary remains stale.** Before running the
production workflow on a restored/current source revision, generate real current
equivalence validation; do not copy hashes into old reports. Future source
relocation will likewise require fresh provenance.

#### Recovering the baseline

Use the archive, not the mutable validation workspace, to recover the exact
original files. Its SHA-256 is
`a5a77ae0bc39d647746051333b9f919c8a4359e4064b9e9c65b28e55dfddbf03`.
Verify this digest, extract into a **new empty directory**, and verify each
extracted file against `checkpoint_inventory.json` before use. Never extract
over the active project or discard unrelated work.

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath 'artifacts\phase3_baseline_us327\original_checkpoint.zip'
# Replace the destination with a new, empty recovery directory.
Expand-Archive -LiteralPath 'artifacts\phase3_baseline_us327\original_checkpoint.zip' -DestinationPath 'C:\Temp\sensor_phase3_us327_restore'
```

The checkpoint excludes raw data, environments, caches, Git internals, and
unrelated artifact subdirectories. It includes the aligned data/statistics needed
for Phase 3 replay; it is not a raw-data/Phase 1 rebuild backup. The recorded
environment is Python 3.13.9 with NumPy 2.5.1, pandas 3.0.5, matplotlib 3.11.2,
and PyYAML 6.0.3; the full installed-package inventory is in the report.

From the recovered root, using that environment, the validation sequence is:

```powershell
python -B -m unittest scripts.phase3_testa_us325 scripts.test_phase2_monitoring scripts.phase3_test_history scripts.phase3_test_monitoring scripts.phase3_testa_protocol_equivalence scripts.test_phase1_phase3a_statistics -q
python -B -m scripts.phase3a_protocol_equivalence
python -B -m scripts.phase3a_us325
```

The last two commands write into the recovered copy only. They intentionally
refresh validation/run metadata; compare numerical/event evidence separately
from source hashes, timestamps, and path-dependent provenance. Historical
signed-margin Phase 2 (38,087 messages) remains a distinct archived comparator;
the revised two-sided Phase 2/C0 comparator is 9,159 messages.

### US-3.28 importable implementation extraction

[`phase3_implement.py`](phase3_implement.py) is the authoritative source for the
29 definitions relocated from the Phase 3 notebook: history/input validation,
normalization/clustering, moments/allocation, the shared monitoring engine,
historical fixed-alpha/sweep helpers, and legacy Phase 2-scheduled history and
baseline-summary helpers. The legacy helpers remain for regression coverage;
they are not the revised production protocol. Their existing `phase2_builder`
argument supplies controlled fixtures without editing module globals.

Importing the module loads definitions only, not configuration, datasets,
experiments, tests, charts, or output files:

```python
from scripts.phase3_implement import FMICMonitor, evaluate_alpha_clustering
```

At US-3.28 the notebook imported these definitions; it was retired at US-3.32.
The guarded module CLI requires an explicit
flag to select that historical sweep:

```powershell
python -B -m scripts.phase3_implement --help
# Historical US-3.22 sweep; explicitly overwrites its historical sweep outputs:
python -B -m scripts.phase3_implement --root . --historical-sweep
```

US-3.29 subsequently made this module the unified revised experiment entry
point; see the commands below. Tests import the module directly instead of
executing tagged notebook cells.

The US-3.24 report records `phase3_implementation_sha256`; the retired notebook
hash was removed at US-3.32. US-3.25 requires the implementation hash to match the current imported implementation,
and its reports/failure records retain it. The selected root must contain the
implementation actually imported, preventing a report from hashing one copy
while executing another. Historical sweep results/report additionally record
`implementation_sha256`. These are provenance additions, not numerical changes.

Existing saved validation metadata predates extraction and must not be relabeled
as current. The following commands describe the archived US-3.28 validation
procedure, not the current production interface:

```powershell
python -B -m unittest scripts.phase3_testa_us325 scripts.test_phase2_monitoring scripts.phase3_test_history scripts.phase3_test_monitoring scripts.phase3_testa_protocol_equivalence scripts.test_phase1_phase3a_statistics -q
python -B -m scripts.phase3a_protocol_equivalence
python -B -m scripts.phase3a_us325
```

The local, Git-ignored
[`phase3_extraction_us328/`](../artifacts/phase3_extraction_us328/) contains the
candidate copy, actual execution logs, and `validation_report.json`. All
**141 tests** passed in the six-module suite. Fresh equivalence passed its
**123-test** suite, and the revised runner passed its **137-test** suite and all
six fresh-process replays; the suites overlap.

All 41 configurations matched US-3.27 exactly on full monitor summaries, raw
events, and canonical per-bucket decisions: 819,344 decisions and 16,210
initialization/root synchronization events. Six scientific CSVs were
byte-identical. All notebook code cells also executed successfully in a clean
process. Of the 29 relocated definitions, 28 remained AST-identical; only the
historical sweep's notebook-path fallback and provenance fields changed.
Clean-process import and canonical-definition tests replace the old
notebook-residency constraint. A negative-control test rejects missing/stale
implementation hashes. Original scientific outputs and the sealed US-3.27
checkpoint were not overwritten.

### US-3.29 unified production execution

The canonical default is now the revised C0/C1/C2 controls and 38 clustered
configurations (19 approved alphas per method). From the repository root:

```powershell
# Canonical external test interface after US-3.30.
python -B -m scripts.phase3_test --record-validation artifacts\phase3_current\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_current\phase3_validation.json
```

For a separate candidate destination, keep the same independently generated
receipt and add `--output-dir artifacts\my_phase3_candidate`. Revised reports,
events, and diagnostics go to that directory. Since US-3.31, charts and detailed
interpretation are rendered separately by the analysis notebook. Artifact basenames, CSV
schemas, numeric precision, and snapshot scope are unchanged. Original artifact
roots, source/configuration directories, and checkpoint/extraction directories
are rejected as output destinations. The default destination is intentionally
different from the historical root-level artifact location.

The receipt records actual successful, non-skipped tests and hashes of the
implementation, external Phase 1/2 dependencies, the Phase 2 notebook, configuration, source
observations/statistics, selected baseline evidence, and tests.
Missing, failed, incomplete, or stale receipts fail nonzero before evaluation,
with current-run failure/completion diagnostics in the output directory.
Regenerate the receipt after changing a covered file. Production never imports
test modules or launches regression tests; its six fresh-process replays invoke
the canonical read-only replay mode and return JSON without writing artifacts.

C0 reuse requires current input/code/test provenance, passing runtime checks,
and matching event bytes. Missing or stale C0 evidence triggers genuine
Phase 2/Phase 3 singleton equivalence in the candidate destination before
weighted controls or clustered runs. Original stale reports are not rewritten
or re-certified. A failed gate blocks subsequent configurations. The production
report embeds the external receipt/hash and whether C0 was reused or regenerated;
it rechecks the validation provenance before publishing success.

The former orchestration/test facades and implementation notebook are retired.
The saved-only analysis notebook is described in US-3.31 below; test consolidation
is complete in US-3.30.
`--historical-sweep` deliberately retains the old output-overwrite behavior and
cannot be combined with revised-run output/receipt options.

The [isolated validation report](../artifacts/phase3_production_us329/verified/validation_report.json)
records **148 passing tests**, successful unified production and six independent
replays, fresh C0 regeneration and verified current-cache reuse, and missing/stale
receipt failures. All 41 full summaries, 819,344 decisions, and 16,210
initialization/synchronization events exactly matched US-3.27; six scientific
CSVs were byte-identical. Twenty-eight original scientific definitions remained
AST-identical. Original code/configuration/artifact files were unchanged during
validation, and the sealed checkpoint remained intact.

The initial isolated attempt's Windows access-denied failure is retained in
`artifacts/phase3_production_us329/`. The fix removed an unnecessary immediate
second write of the freshly generated C0 summary; it did not bypass validation.
The successful `verified/` run used the final source and a fresh external receipt.

### US-3.30 consolidated testing and saved-output verification

[`phase3_test.py`](phase3_test.py) is the maintained testing entry point.
It uses the existing `unittest` framework; no new dependencies are required.
From the repository root:

```powershell
# Algorithm, orchestration, and verifier regression checks (default selector).
python -B -m scripts.phase3_test --checks behavior

# Independent verification of existing results; never refreshes their receipt.
python -B -m scripts.phase3_test --checks saved --output-dir artifacts\phase3_current

# Saved verification plus two C0 reproductions and six weighted/control replays.
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_current

# Optional report must be outside the results being verified.
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_current --report artifacts\phase3_testing_us330\current_saved_checks.json

# Required before production: behavior + replay + external Phase 1/2 suites.
python -B -m scripts.phase3_test --record-validation artifacts\phase3_current\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_current\phase3_validation.json
```

Selectors can be combined as `--checks behavior saved replay`.
`--checks replay` without an output directory compares fresh subprocesses to
preserved numerical references and independent fresh in-process runs.
With an output directory, it also requires current saved provenance and matches
the saved counts, seven transmission categories, and raw-event fingerprints.
The C0 reproducibility test compares complete summary/event bytes from two
temporary destinations. Child processes run canonical runtime/replay commands,
never a recursive test launcher.

`--checks saved` requires an existing output directory and checks:

- Exact required CSV schemas, unique C0/C1/C2 plus all 38 method/alpha keys, the
  approved grid, control alpha semantics, finite values, and integer counts.
- Independent category/pathway/share arithmetic, check outcomes, repeated-check
  bounds, root fanout costs, complete cluster-size grids, and grouped totals.
- Full-precision threshold consumption and source-derived cohort size/global
  violation count. Phase 1 still owns statistics generation; its four tests stay
  in `test_phase1_phase3a_statistics.py` and run separately in the receipt suite.
- Snapshot capture scope/counts, partitions/coordinators, finite moments and
  weights, persistent observation counts, allowance budgets, and averages/truth
  against the original observations.
- Summary/control/table/minimum/replay reconciliation, matching completion/run
  records, embedded receipt bytes, and exact current input/configuration/code/test
  provenance. A saved `status: passed` alone is never sufficient.
- Fresh per-bucket C0/Phase 2 equivalence and byte-identical saved C0 events.
  This executes C0 checks in temporary destinations, not the weighted/grid
  production workflow.

All saved-result and replay work hashes the results before/after; reports must
be written elsewhere. Injected-failure and mutation tests use temporary copies.
Missing prerequisites, stale receipts, altered saved data, skipped tests, or
changed protected files fail explicitly and return nonzero. A verification report
records selectors, actual test IDs/counts, failures/errors/skips, external module
scope, source hashes, and integrity results. It does not update saved production
metadata or convert stale evidence into a current pass.

Only `--record-validation` runs the full required scope, including the independent
Phase 2 and Phase 1 statistics suites. It cannot be combined with selectors or a
saved-output directory. Production requires its schema-version-2 receipt, full
behavior/replay/external-module scope, actual test IDs/count, zero skips/failures,
and matching current hashes. A behavior-only or saved-output report cannot
certify production. US-3.29 receipts and old saved results are intentionally stale
for this source revision; regenerate real validation and production in a new
candidate directory rather than editing historical hashes.

#### Coverage migration map

The module's `LEGACY_COVERAGE` mapping also preserves this ownership:

| Former module | Canonical classes | Preserved responsibilities |
|---|---|---|
| `test_phase3_history.py` | `ClusteringTests`, `NormalizationTests`, `Phase3AExecutionTests` | Signed cancellation, hand-calculated merges/quality, deterministic ties/fallbacks, alpha sensitivity, history/input/cohort/baseline contracts |
| `test_phase3_monitoring.py` | `FirstMomentTests`, `SecondMomentTests`, `FMICProtocolTests`, `SMICProtocolTests`, `ProductionIntegrationTests` | Source moments/allocations, hand-counted ledgers, boundary/lifecycle/zero-weight/crossing checks, persistent state, inherited FMIC cases for SMIC, canonical imports and historical exports |
| `test_phase3a_protocol_equivalence.py` | `SyntheticProtocolTests`, `ProductionReproducibilityTests` | Independent Phase 2 comparison, dropped-decision/stale-reference/status/peer defect injection, complete C0 reproducibility bytes |
| `test_phase3a_us325.py` | `CompositionTests`, `ControlAndDiagnosticTests` | Pathway arithmetic, weighting/partition contrasts, order independence, complete grids, repeated checks, isolated failures, cache/receipt gates, production/test separation |
| New verifier coverage | `SavedOutputValidationTests`, `WeightedProductionReplayTests` and CLI check functions | Saved schema/count/share/provenance/snapshot mutations, missing outputs, full-precision consumption, report-path safety, six weighted/control subprocess replays |

All **102 legacy Phase 3 cases** were retained in the canonical module.
The four former forwarding files were retired at US-3.32. Cutover replaces the
obsolete notebook architecture assertion with an exact three-file surface check
and routes runtime equivalence through the canonical CLI; scientific test
scenarios are unchanged.
SMIC still inherits the FMIC scenarios rather than copying or dropping them.
Use the canonical module, not the former module names, for discovery.

The [isolated validation report](../artifacts/phase3_testing_us330/verified/validation_report.json)
records **155 passing tests**: 107 behavioral/verifier cases, two replay checks,
42 external Phase 2 tests, and four external Phase 1 statistics tests. Production
passed all three controls, 38 clustered runs, and six subprocess replays.
The separate saved-output/replay command passed its three checks read-only;
summary-count, snapshot, missing-configuration, and stale-provenance mutations
failed. Missing outputs and old receipts failed nonzero. Six scientific CSVs
remained byte-identical to US-3.27; 28 scientific definitions remained
AST-identical. Original files and sealed evidence were preserved.

The ignored `phase3_testing_us330/` directory retains the final candidate,
reports/logs, original-class AST mapping and one-off verification procedure,
the initial skipped-test diagnostic serialization failure, and an interrupted
run superseded by stricter snapshot checks. Skipped tests now persist readable
test-ID/reason diagnostics and remain failures, not passing validation.

### US-3.31 saved-results-only analysis notebook

> Historical layout note: this section describes the pre-US-3.34 `phase3_current`
> directory. Use [US-3.34](#us-334-phase3-output-and-operational-layout) for
> active paths and commands.

Open [`phase3_analyze.ipynb`](phase3_analyze.ipynb), select the project's Python
kernel, set `OUTPUT_DIR` in the settings cell, and run all cells from a clean
kernel. The default is `artifacts/phase3_current`; it does not fall back to
historical or archived results. Run the existing independent validation and
production commands above first if no current outputs exist.

In VS Code, editing the notebook's settings cell is the simplest way to select
another candidate. Environment overrides are also supported when inherited by
the kernel at launch:

| Setting | Default | Purpose |
|---|---|---|
| `PHASE3_REPO_ROOT` | Current directory or its parent containing the implementation | Complete checkout whose source/input hashes must match the saved run |
| `PHASE3_OUTPUT_DIR` | `artifacts/phase3_current` under that checkout | Explicit saved-result directory; relative paths resolve from the checkout |
| `PHASE3_SHOW_HISTORICAL` | `0` | Set to `1` for the preserved three historical sweep charts, separately labeled with the signed-margin Phase 2 comparator |
| `PHASE3_ANALYSIS_EXPORT_DIR` | Unset | Optional **new** separate PNG directory; existing directories, selected results, source, artifact roots and migration-evidence directories are rejected |

The notebook contains:

1. Locked cohort/interval/full-precision threshold and actual saved validation
   provenance, with the selected directory/run ID visible.
2. The relocated source explanations, first/second-moment recurrences, hand
   calculations, initialization/zero-weight conventions, signed clustering
   history, shared protocol and actual-transmission accounting.
3. Historical signed-margin Phase 2 versus revised two-sided Phase 2/C0 versus
   the centralized reference, without changing denominators or re-certifying
   historical code.
4. C0 equivalence, C0/C1/C2 weighting-only contrasts, conditional matched
   clustering contrasts, equal-alpha complete-method differences, prespecified
   alpha 0.10 and separately labeled exploratory in-sample minima.
5. The existing detailed interpretation, alpha sensitivity charts, pathway
   composition, singleton bar chart, check/repeated-check/cluster-size tables
   and retained synchronization snapshots.
6. Existing scientific cautions and explicit analytical gaps deferred to separate
   research: no new experiments, metrics, tuning, statistical claims, or causal
   conclusions are added.

The notebook imports only the read-only `load_phase3_analysis_results` API from
the import-safe implementation. That loader checks required saved schemas,
unique controls/alpha grid, finite values and category/pathway/check/cluster-size
accounting, snapshot/source reconciliation, summary/table/minimum/comparison
consistency, matching run/completion/failure records, embedded receipt bytes,
and exact current production/input/configuration/test provenance. Missing,
failed, mixed-run, or stale inputs fail before scientific presentation. It
does not import the testing script, run tests, construct a monitor, or replay
experiments. Use the independent testing script for substantive behavioral and
saved-output/replay verification; normal analysis is not a new validation receipt.

The detailed `_interpretation` function was relocated AST-identically into the
notebook; revised plotting now reads saved rows and displays inline. Production
retains numerical comparisons, configuration tables, minima and limits but no
longer computes the detailed narrative or generates five revised PNGs.
This intentional presentation change is marked by `presentation.schema_version=1`,
`outputs.plots=[]`, an `outputs.analysis_notebook` reference, and notebook-oriented
completion visualization metadata. The former private `_plot_results` and
`_interpretation` compatibility exports were removed; no runner extracts notebook
definitions. Scientific CSV basenames/schemas/precision/capture scope are unchanged.

Default execution performs no pipeline artifact or PNG writes. It hashes its
saved inputs before/after presentation. Existing PNGs remain historical files;
they are neither deleted nor silently regenerated. Optional exports retain the
five revised filenames and, when requested, the three historical filenames in
the new export directory. The explicit implementation `--historical-sweep` option
retains its old export behavior for isolated recovery; do not run it to analyze
saved results.

The analysis notebook is deliberately **not** a production-receipt input:
saving execution counts/cell images must not stale scientific validation. Its
exact source hash and clean-kernel outcome are recorded separately in the
analysis validation report. Canonical notebook source is stored without outputs;
executed evidence copies are kept outside the maintained script surface.
Jupyter/IPython is required to run the notebook. The one-off headless validation
also uses `nbclient`/`nbformat`; those are validation tools, not new production
dependencies.

The [isolated validation report](../artifacts/phase3_analysis_us331/verified/validation_report.json)
records **159 passing tests**, successful revised production with three controls,
38 clustered runs and six fresh-process replays, and a passing independent
saved-output check. Clean real kernels rendered five default revised charts and
eight with the historical view/export enabled. Actual Matplotlib line, stacked
area and bar values and displayed table values reconciled with saved data.
Missing/stale results and unsafe exports failed explicitly. Instrumented kernels
blocked monitor/production/replay calls and CSV writes; no project testing modules
were imported. All source/configuration/production/historical inputs were unchanged
by analysis. Six scientific CSVs were byte-identical to US-3.27; 28 scientific
definitions remained AST-identical.

The ignored `phase3_analysis_us331/` directory retains the successful candidate,
actual logs, executed notebooks, artist/data audits, explicit export check,
original relocated presentation source and one-off procedure. It also retains
the interrupted raw-notebook-receipt coupling iteration, superseded before final
validation. No reference hashes were patched or historical outputs overwritten.
US-3.32 completes the retirement and full-matrix cutover below.

### US-3.32 three-file workflow and verified cutover

> Historical cutover record. Its `phase3_current` paths and seven-file recovery
> instructions are superseded by [US-3.34](#us-334-phase3-output-and-operational-layout).

The maintained Phase 3 executable surface is exactly:

| File | Role |
|---|---|
| [`phase3_implement.py`](phase3_implement.py) | Import-safe scientific algorithms; revised C0/C1/C2 plus 38 clustered runs; runtime equivalence and read-only replays |
| [`phase3_test.py`](phase3_test.py) | Independent behavior, saved-output and fresh-process verification; external validation receipt |
| [`phase3_analyze.ipynb`](phase3_analyze.ipynb) | Existing saved-only tables, charts, Markdown interpretation and limitations |

Phase 1/2 dependencies remain independently owned; their notebooks/modules/tests
are not additional Phase 3 entry points. Configuration and output schemas are
unchanged. No tagged-cell loaders, compatibility launchers or production notebook
are required. The former module commands are available only in restored
historical checkouts, not in this checkout.

#### Prerequisites and normal execution

Use the project Python environment with `requirements.txt` dependencies installed.
Keep the aligned Phase 1 observations, full-precision statistics, approved
configuration, historical matched baseline, existing US-3.21 evidence and
original scientific reference tables in their documented locations. Jupyter and
an IPython kernel are needed for interactive analysis; `nbclient`/`nbformat` are
only needed for automated clean-kernel execution.

From the repository root in PowerShell:

```powershell
# Once for the current Phase 2 producer revision; regenerate if that code changes.
# This genuinely reruns Phase 2; never patch an old baseline's code hash.
python -B -m scripts.shared_monitoring_engine publish
python -B -m scripts.shared_monitoring_engine validate

# Independent full-scope validation, then production of the revised 41-run matrix.
python -B -m scripts.phase3_test --record-validation artifacts\phase3_operational\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_operational\phase3_validation.json

# Verify the saved bundle and fresh-process reproductions without rewriting it.
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_outputs
```

Current Phase 2 prerequisites are the split summary, events and independent
receipt described above. Missing or stale evidence fails without a historical
fallback. The monitoring engine, threshold, rows, precision and transmissions
are unchanged.

For isolated candidate production use a `phase3_outputs` directory outside
`artifacts/`, for example `"$env:TEMP\phase3-candidate\phase3_outputs"`, and use
that directory for saved checks and analysis. Regenerate the validation
receipt after changing any covered code/test/dependency/input/config/reference.
Old receipts and prior-story outputs remain historical, not re-certified.
Saving analysis notebook output cells is still not a scientific receipt change;
its source/execution is separately verified.

Open [`phase3_analyze.ipynb`](phase3_analyze.ipynb), select the project kernel,
set `OUTPUT_DIR` if needed in its settings cell and **Restart Kernel and Run All**.
The default is `artifacts/phase3_outputs`; normal execution writes no scientific
results or PNGs. See [settings and optional historical/export views](#us-331-saved-results-only-analysis-notebook).

Additional check modes:

```powershell
python -B -m scripts.phase3_test --checks behavior
python -B -m scripts.phase3_test --checks replay
# Runtime singleton equivalence only: no tests, no weighted/grid evaluation.
python -B -m scripts.phase3_implement --equivalence --output-dir "$env:TEMP\phase3-equivalence\phase3_outputs"
# Read-only JSON stdout; no files or validation receipt are written.
python -B -m scripts.phase3_implement --replay --method FMIC --alpha 0.10
```

The explicit `--historical-sweep` implementation option remains for original
helper regression/recovery. It is not the normal workflow and retains historical
output-overwrite behavior; use it only in a separate recovery copy. The retired
production notebook and its facades are not retained to expose this option.

#### Equivalence evidence and recovery

The [final-source gate report](../artifacts/phase3_cutover_us332/verified/validation_report.json)
records executed commands, source hashes, full-scope tests, revised production,
independent saved checks, clean-kernel chart/table audits and negative notebook
cases. Its full-matrix evidence compares every summary field, raw event and
per-bucket decision, including partitions, histories/moments/allowances,
root-known truth, trigger schedules, all seven transmission categories and
check/pathway metrics. All 41 configurations require exact agreement; no
continuous tolerance is used to conceal a discrete difference.

The final gate passed **162 tests**, exact equality for **41 configurations,
819,344 decisions and 16,210 events**, all six byte-identical scientific CSVs,
and both clean-kernel presentation views plus three expected rejection cases.
The [active-checkout report](../artifacts/phase3_cutover_us332/verified/active_checkout_report.json)
also records successful default production, independent saved/replay checks and
five-chart clean-kernel analysis after retirement. The current Phase 2
prerequisites were genuinely regenerated and matched the proven candidate byte
for byte; the actual full-scope receipt was reused only after verifying every
covered source/reference hash, without modifying its bytes. The default
`artifacts/phase3_current/` bundle is ready to open in analysis.

Expected metadata differences are final code/test hashes, removal of obsolete
notebook/facade hashes, the fresh Phase 2 source-integrity inventory, selected
paths, commands, timestamps, run IDs and receipts. The six unchanged-contract
scientific CSVs require byte identity. No artifact schema redesign or new
scientific analysis was included. US-3.33 subsequently obtained artifact-contract
approval and changed only the output organization described below.

Before removing the seven old files, the gate verifies all US-3.27 sealed files
and all 85 original checkpoint archive members, and writes a hash-verified
[`pre_cutover_entry_points.zip`](../artifacts/phase3_cutover_us332/verified/pre_cutover_entry_points.zip)
containing the exact immediately preceding notebook/facades. This small archive
is supplementary; it is **not** a standalone rollback checkout.

For complete rollback follow the [US-3.27 isolated recovery procedure](#us-327-pre-consolidation-checkpoint).
The original archive SHA256 remains
`a5a77ae0bc39d647746051333b9f919c8a4359e4064b9e9c65b28e55dfddbf03`.
Restore into a new empty directory, verify each member against the inventory,
use the recorded environment and run the archived commands there. Never restore
over active work or replace old hashes to make validation pass. For the
immediately pre-cutover revision, the verified candidate from US-3.31 plus the
seven-file archive supplies the transition context. All ignored local baseline,
candidate and recovery evidence needs a separate backup; Git does not preserve it.

### US-3.33 approved phase3_ artifact bundle

> Historical schema-version-1 bundle. Its six-file layout and `phase3_current`
> commands are superseded by [US-3.34](#us-334-phase3-output-and-operational-layout).

The user-approved current output contract is **six files**, all prefixed
`phase3_`. The three executable workflow files remain unchanged in responsibility.
The [versioned mapping, keys, units, nullability and capture scope](../artifacts/README_artifacts.md#us-333-approved-current-artifact-contract)
is authoritative; earlier story-numbered inventories in this guide are historical.

| File in the selected output directory | Contents |
|---|---|
| `phase3_results.csv` | All 41 control/clustered configurations, explicit `configuration_kind`, original metrics and applicable contrasts |
| `phase3_cluster_sizes.csv` | All 246 size-bin records with explicit control/clustered alpha identity |
| `phase3_snapshots.csv` | Unchanged C1/C2 plus selected-alpha synchronization snapshots; not the entire alpha grid |
| `phase3_equivalence_events.csv` | Unchanged complete C0 initialization/root-sync events, with its own distinct schema |
| `phase3_run.json` | Schema/version, comparison, completion, failures, runtime equivalence, provenance, semantics and artifact inventory/hashes |
| `phase3_validation.json` | Actual independently executed full-scope regression receipt; hash-referenced, not embedded again |

#### Normal execution and isolated candidates

After prerequisites are present, run from the repository root:

```powershell
python -B -m scripts.phase3_test --record-validation artifacts\phase3_current\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_current\phase3_validation.json
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_current
```

For a new isolated candidate:

```powershell
python -B -m scripts.phase3_test --record-validation artifacts\my_phase3_candidate\phase3_validation.json
python -B -m scripts.phase3_implement --output-dir artifacts\my_phase3_candidate --validation-record artifacts\my_phase3_candidate\phase3_validation.json
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\my_phase3_candidate
```

An externally stored receipt may also be supplied; production copies its exact
bytes into `phase3_validation.json`. Keep optional verification reports outside
the selected bundle, for example `--report artifacts\phase3_checks\phase3_verification.json`.
An old eleven-file output destination is rejected without modifying it.
Preserve it separately and select a new candidate directory; do not combine
old exports with the six-file bundle or patch old receipts.

Open [`phase3_analyze.ipynb`](phase3_analyze.ipynb), select the project kernel and
**Restart Kernel and Run All**. `OUTPUT_DIR` still defaults to
`artifacts/phase3_current`; candidate selection and optional historical/export
settings are unchanged. The notebook reads the same versioned bundle and
hash-checked receipt as the independent verifier, with no production/test/replay
execution and no normal scientific/PNG writes.

#### Integrity, failure and scope rules

Successful production publishes `phase3_run.json` last, with passing consistent
run identities and hashes/columns/row counts/keys for the other five files.
The independent test receipt is not a production-generated test result. Readers
resolve its reference only after verifying bytes and current source provenance.
Scientific accounting/source/snapshot/replay checks remain required even if
inventory hashes match.

In-progress and failed attempts cannot certify remaining tables from an older
run. Failures persist in `phase3_run.json#/failures`, with current stage,
configuration, reason, available metrics and protected-file integrity.
Standalone `--equivalence --output-dir <separate-dir>` writes the two runtime
evidence files only (`phase3_run.json` with `kind=equivalence` and
`phase3_equivalence_events.csv`); it is deliberately not a full production
bundle or a regression receipt. Read-only `--replay` still writes JSON stdout,
not files.

The revised/historical/centralized comparators, initial synchronization versus
moment-sample accounting, integer transmissions, null versus zero, snapshot
coverage and numerical precision are unchanged. No new experiments,
interpretation or artifact-format compatibility exports are added.

#### Evidence and recovery

The [US-3.33 final-source report](../artifacts/phase3_artifacts_us333/verified/phase3_validation_report.json)
records executed tests/production/replays, every field/record comparison against
the prior current bundle, snapshot/C0 event byte identities, scientific JSON
equality, corruption rejection and real clean-kernel chart/table audits.
It also verifies original artifacts, Phase 2 prerequisites and sealed evidence.
The gate passed **166 tests**, complete result/size-record preservation,
byte-identical snapshot/equivalence CSVs, all six fresh-process replays, and
five/eight-chart clean-kernel analysis. The
[active-checkout verification](../artifacts/phase3_artifacts_us333/verified/phase3_active_checkout_report.json)
also passed saved/replay checks and five-chart analysis against the exact
published bytes. `artifacts/phase3_current/` is ready to use.

The prior eleven-file current bundle is in the hash-verified
[`pre_migration_current.zip`](../artifacts/phase3_artifacts_us333/pre_migration_current.zip),
with [`pre_migration_inventory.json`](../artifacts/phase3_artifacts_us333/pre_migration_inventory.json).
Its complete directory is also preserved at
[`previous_current/`](../artifacts/phase3_artifacts_us333/previous_current/).
US-3.32 retains the previous reader/source revision; US-3.27 retains the complete
original workflow checkpoint. Restore historical formats only in a separate
recovery copy with their corresponding source/environment. Do not silently
re-certify historical results with new hashes.

Migration procedures live only in ignored evidence, not the maintained script
surface. Existing root-level scientific/historical artifacts and PNGs are not
renamed, moved or deleted. Back up ignored evidence separately.

### US-3.34 Phase 3 output and operational layout

The active layout separates user-facing results, workflow dependencies, and
user-removable history:

| Location | Contents |
|---|---|
| `artifacts/phase3_outputs/` | `phase3_results.csv`, `phase3_cluster_sizes.csv`, `phase3_snapshots.csv`, and `phase3_summary.json` |
| `artifacts/phase3_operational/` | `phase3_run.json`, `phase3_equivalence_events.csv`, `phase3_validation.json`, plus preserved static references in `references/` |
| `artifacts/phase3_archive/` | Superseded root-level Phase 3 artifacts and the original `phase3_current/` bundle; not used as current data |

The former root-level and `phase2_current/` matched artifacts are historical.
Current Phase 3 consumes the separately owned split Phase 2 contract and its
independent receipt.

`phase3_summary.json` is the schema-version-1 user-readable comparison summary.
The schema-version-2 operational `phase3_run.json` owns in-progress/failure
state, completion diagnostics, runtime equivalence, provenance, and hashes.
It hashes the three result CSVs, summary, and C0 event file; the summary points
to the paired operational receipt by relative path and SHA256. Every component
must carry the same `run_id`. The manifest is written last, so a failed run
cannot certify leftover tables.

The historical six-file bundle is mapped as follows: results, cluster sizes,
and snapshots moved byte-for-byte into outputs; C0 events moved byte-for-byte
into operational; the old mixed-purpose `phase3_run.json` was replaced by the
schema-version-2 manifest plus the schema-version-1 user summary; and the stale
old validation receipt was archived and replaced by a fresh independent receipt.
The complete original-path/hash/consumer inventory is in
[`README_artifacts.md`](../artifacts/README_artifacts.md#us-334-current-layout-and-complete-migration-inventory).

The default pair is `phase3_outputs/` and its sibling `phase3_operational/`.
For an isolated candidate, name the selected result directory `phase3_outputs`;
the script resolves its sibling `phase3_operational` automatically. For a
custom-named output directory, its paired operational directory is the
`phase3_operational/` child. Candidate runs read static references from the
selected checkout's `artifacts/phase3_operational/references/`; their receipt,
manifest, and runtime C0 events remain in the candidate pair and cannot be
mixed with another run's output.

Run the independently executed gate and default production from the repository
root:

```powershell
python -B -m scripts.phase3_test --record-validation artifacts\phase3_operational\phase3_validation.json
python -B -m scripts.phase3_implement --validation-record artifacts\phase3_operational\phase3_validation.json
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_outputs
```

The receipt covers behavioral tests, fresh-process replays, and the independent
Phase 1/Phase 2 suites. To build an isolated pair, use a temporary root outside
`artifacts/`; pass its `phase3_outputs` path to both production and saved checks,
and supply the separately executed receipt above. For example:

```powershell
$candidate = Join-Path $env:TEMP "phase3-candidate"
python -B -m scripts.phase3_implement --output-dir "$candidate\phase3_outputs" --validation-record artifacts\phase3_operational\phase3_validation.json
python -B -m scripts.phase3_test --checks saved replay --output-dir "$candidate\phase3_outputs"
```

Analysis remains saved-results-only. `PHASE3_OUTPUT_DIR` defaults to
`artifacts/phase3_outputs`; for candidates, select the candidate's
`phase3_outputs` directory. `PHASE3_SHOW_HISTORICAL=1` reads the separately
identified historical sweep under `phase3_operational/references/`, never the
archive. Exports must remain outside outputs, operational evidence, and archive.

`phase3_archive/` is a removal queue, not a recovery dependency. Once the
full-scope tests, fresh production, saved checks/replays, and clean-kernel
analysis pass with `phase3_archive/`, `phase3_current/`, and all loose root-level
Phase 3 files physically unavailable, users may manually back up its contents
elsewhere and remove the folder. The workflow never deletes it automatically.
Phase 2's owned output and operational folders and Phase 1 inputs remain
outside this cleanup.
