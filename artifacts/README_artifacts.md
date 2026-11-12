# Artifacts Folder

This folder stores generated outputs from the transformation and experiment pipeline.

## Current Phase 1 layout (US-1.19)

The four operational files are `phase1_operational/phase1_aligned_temperature.csv`,
`phase1_operational/phase1_source_inventory.csv`, `phase1_operational/phase1_run.json`,
and the separately generated `phase1_operational/phase1_validation.json`.
Reader-facing statistics and duplicate/conflict/unmatched evidence remain under
`phase1_outputs/`. The large unmatched export and both audit populations are
retained, not considered disposable.

Run Phase 1 implementation, Phase 2 production and independent validation, Phase 3
independent validation and production, then Phase 1 independent validation.
Analysis notebooks only read saved inputs. The shared engine derives the
monitoring-cohort P90, rather than Phase 1 maintaining a second authority.
The historical Phase 2 reference retains its original path; the engine maps it
to the new input only when the aligned CSV matches the recorded old SHA-256.

The manual removal queue is the entire `phase1_archive/`, including
`us115_baseline/`, `us116_retired_sources/`, `us116_validation/`,
`us117_retired_tests/`, `us117_validation/`, `us118_retired_sources/`,
`us118_validation/`, and `us119_pre_cutover/`. The archive remains in place;
back it up externally before removing it. The US-1.19 checkpoint contains
`checkpoint_inventory.json` and `retired_files_inventory.json`, which identify
the preserved original paths and SHA-256 hashes. For rollback, verify the desired
bytes and restore only the explicitly selected original files to their recorded
paths, then restore their compatible configuration and regenerate dependent
outputs and receipts. Do not copy the whole archive over the current workspace.

Historical artifact lists and individual producer descriptions below describe
earlier layouts unless identified as current above.

## Phase 1 read-only analysis (US-1.18)

[`phase1_analyze.ipynb`](../scripts/phase1_analyze.ipynb) reads the historical
temperature aggregate, retained user-facing statistics and duplicate evidence,
and current production QC/status. It verifies historical identities and current
publication hashes rather than recreating missing inputs. Aggregate-inclusive
and source-only duplicate reports describe different populations; the notebook
links the exhaustive unmatched CSV without loading it into a dataframe.
No analysis report, chart, input or receipt is written by the notebook.

## Phase 1 independent validation (US-1.17)

`phase1_operational/phase1_validation.json` is written by the independent
[`phase1_test.ipynb`](../scripts/phase1_test.ipynb), not by the producer. It
records the executed test IDs, result, tested source/configuration/output hashes,
raw-input-tree fingerprint, baseline seal hash and the exhaustive raw duplicate
audit that was not run. In-progress or failed status is not a passing receipt.
The notebook checks current downstream receipts and full scientific evidence;
it never replaces them or rewrites Phase 1 production files.

The tests use recorded baseline identities and do not read the archive. The
baseline reference identifies the original seal; actual outputs are compared
independently against recorded scientific identities. Retired test sources are
preserved under `phase1_archive/us117_retired_tests/`, and actual executed
notebook copies and validation evidence are under `phase1_archive/us117_validation/`.
The full raw production rerun and exhaustive duplicate investigation are not
part of this notebook's default checks.

## Phase 1 publication and monitoring preparation (US-1.16)

The canonical producer is
[`phase1_implement.ipynb`](../scripts/phase1_implement.ipynb). The aligned
CSV, source inventory and consolidated run JSON are in `phase1_operational/`.
General statistics contain only the original
all-device series; the former stable-cohort row is owned by shared monitoring
preparation, with unchanged calculation/population/precision.

`phase1_operational/phase1_run.json` is a producer record, **not an independent
validation receipt**. It combines in-progress/failed/passed status, run settings,
general statistics, QC, quality gates, companion hashes, and implementation/configuration identity.
Downstream preparation rejects missing, failed, incomplete, limited, or stale
publication evidence. Limited runs use an explicit isolated directory and do
not modify production status or artifacts.

The shared engine calculates cohort P90 without writing configuration. Phase 2
stores `monitoring_preparation` in its existing summary; Phase 3 records the same
derived evidence in its operational run's experiment record and hashes it in
provenance. Phase 2's independent receipt binds the preparation-containing
summary; both phases reject stale/inconsistent evidence. The experiment
configuration stores policy/population, not derived P90 or a statistics-file
authority. Historical static references remain byte-preserved.

The retired transformation and audit sources are recoverable under
`phase1_archive/us116_retired_sources/`; current tests load tagged notebook
definitions instead. No historical large duplicate reports were removed or
regenerated. Validation evidence for this extraction is under
`phase1_archive/us116_validation/`, separate from the sealed US-1.15 baseline.

## Phase 1 recoverable baseline (US-1.15)

The local, Git-ignored [`phase1_archive/us115_baseline/`](phase1_archive/us115_baseline/)
preserves the pre-consolidation workspace. It is recovery evidence, not a new
production artifact location or a fallback for current readers.

- `original_files/` preserves 82 source, notebook, configuration, documentation,
  Phase 1 artifact, and current downstream evidence files at their original
  repository-relative paths. `checkpoint_inventory.json` records original and
  preserved paths, SHA-256 values, sizes, Git status, CSV schemas/row counts,
  notebook source/output coverage, and proposed dispositions.
- `raw_input_inventory.json` identifies all 3,475 raw-directory files by size,
  SHA-256, schema where applicable, and population role. Raw inputs remain in
  place; they are not included in the recovery copies. Preserve them separately.
- `artifact_ownership.json` distinguishes current operational data, user-readable
  evidence, historical outputs, and retired-source candidates. All large duplicate
  evidence remains current Phase 1 output, including the 1,581,628-row unmatched
  export. The archive contains recovery copies, not replacements.
- `baseline_report.json`, `environment.json`, `dependency_references.json`,
  `logs/`, and `evidence/` record actual validation, dependencies, environment,
  and deterministic comparison evidence. Read the report's status and known
  failures; the checkpoint is not an independent production validation receipt.
- `checkpoint_seal.json` hashes all companion files, including every preserved
  original and the baseline report. Verify its entries before recovery and
  preserve the seal with an external backup.

The full Phase 1 rerun reproduced its four deterministic CSVs byte-for-byte;
fresh Phase 3 production reproduced all three scientific CSVs and C0 events.
Phase 2 independent validation passed 43 tests; Phase 3 behavior/saved/replay
verification passed 121 checks. The original analysis completed all 13 code
cells and six charts in isolation. The as-found combined Phase 1/2 suite passed
51 tests but could not import the misplaced duplicate-audit module. All 16 audit
tests passed only in a separately labeled restored-path diagnostic; this does
not repair the active path or remove the cutover gate.

At US-1.15, no active artifacts had been relocated. **Do not remove this recovery baseline
from the workspace until it has been backed up externally.** A Git clone does
not recover its ignored contents.

For recovery, first verify the desired preserved file's SHA-256 against
`checkpoint_inventory.json`, then restore only that file from `original_files/`
to its recorded original path after reviewing current changes. Do not copy the
entire checkpoint over a working tree or replace current receipts with historical
ones. To reproduce checks, restore a separate workspace, provide the identified
raw inputs, use the recorded environment/commands, and keep all generated writes
inside that isolated copy. Raw data and the Python environment are not bundled.

## Current Phase 3 workflow

See the [US-3.34 output and operational layout](../scripts/README_scripts.md#us-334-phase-3-output-and-operational-layout).
User-facing results are in `phase3_outputs/`; the paired run evidence and retained
static dependencies are in `phase3_operational/`. `phase3_archive/` is removable
after the documented archive-absent verification passes.
The [project plan's controlled-results section](../Distributed_Monitoring_POC_Project_Plan.md#current-phase-3a-controlled-results)
is the current interpretation of these results and distinguishes them from
historical comparisons.
References below to the original production notebook describe historical
producers, not an active notebook or requirement to recreate old artifacts.

## Phase 2 matched baseline and checkpoint (US-2.15)

The current Phase 2 experiment is `phase3a_stable_cohort`, using sensors
A/C/D/E/F/G and 19,984 consecutive one-minute buckets. The saved matched result
records 9,159 transmissions, 467 synchronizations, and zero false-safe or
false-violated root states. The current schema-versioned summary is
`phase2_outputs/phase2_summary.json`; `phase2_outputs/phase2_matched_trace.csv`
contains the full-precision trace for all 19,984 minute buckets;
`phase2_operational/phase2_events.csv` contains the rounded
completed-synchronization rows; and `phase2_operational/phase2_validation.json`
is the separately generated receipt. The summary records the trace schema
version, ordered columns, row count, relative path, and SHA-256 of exact bytes.
The receipt binds current source, tests, inputs, summary, full trace, and events.
The trace's entry fields describe state used for that minute, event fields
describe actions during it, and exit fields describe state committed for the
next minute. Blank cells represent missing values; CSV decimal formatting
preserves the underlying full-precision values without adding precision. UTC
timestamps are ISO-8601, epochs are Unix seconds, and temperatures, means,
references, allowances, and deviations are in degrees Celsius; message counts
are logical transmissions and state/trigger flags are integer indicators.
This six-sensor two-sided matched trace is not interchangeable with the
historical eight-sensor full-dataset signed-margin export and is not a Phase 3
input. Old paths are archived and are not fallbacks for current analysis or
Phase 3. Phase 3 production was regenerated using its current receipt.
The read-only matched-results presentation and its strict saved-file/provenance
checks are in [`../scripts/phase2_analyze.ipynb`](../scripts/phase2_analyze.ipynb).

The Git-ignored `phase2_baseline_us215/` directory is the recoverable
pre-consolidation checkpoint. `checkpoint_inventory.json` records original
paths, byte sizes, SHA-256 values, source-control status, disposition, and
rationale. `original_checkpoint.zip` preserves the inventoried bytes, and
`full_matrix_evidence/phase2_behavior_baseline.csv.gz` stores all 19,984
unrounded bucket rows and states. `baseline_report.json` records the locked
experiment, comparison with the saved summary/events, notebook disposition,
workbook review, and pre-change test results. Phase 2's 43 tests passed; the
Phase 3 saved-result check failed on its existing failed/incomplete/stale
validation record. The receipt was not rewritten.

The general-dataset notebook is the revised US-3.23 two-sided workflow, not a
historical signed-margin notebook and not the current matched experiment.
The notebook and runner are preserved under `phase2_archive/scripts/`; they
require restoration to `scripts/` for their original execution paths and are
not used by current tests or matched production. No separate historical signed-margin notebook was
identified. The original signed-margin result is the independently retained
`phase3_operational/references/phase3a_phase2_baseline.json`.

The former loose root `phase2_*` reports, CSV/XLSX exports, and run logs are
preserved under `phase2_archive/`, not treated as matched outputs. The metrics JSON records negative-margin
scheduling and `all_devices_observed` at P90 24.343381. The debug log records
`non_imputed_devices_only` at P90 24.316875; two root console logs record
`non_imputed_devices_only` at P90 24.316875 and
`all_devices_including_imputed` at P90 24.315625. The current notebook writes
`phase2_two_sided_*` files instead. The XLSX package has no comments, drawing,
or external-link parts; cell-level equivalence has not been established, so
the workbook is preserved and is not declared redundant.

The historical `phase3_archive/phase3a_phase2_baseline.json` copy is byte
identical to the independently retained
`phase3_operational/references/phase3a_phase2_baseline.json`; current runtime
consumers use the operational reference, not the removable archive copy.
The current matched baseline's recorded `code_sha256` must match the active
`scripts/shared_monitoring_engine.py` file. Phase 3 rejects a stale producer identity;
regenerate the matched baseline with the implementation notebook rather than
editing its recorded hash.

The archive preserves former artifact-root files at its top level, the old
`phase2_current/` directory beneath it, repository-root console logs in
`repository_root/`, and retired workflow files in `scripts/`. Relocation checked
each file's SHA-256 before and after the move. The US-2.15 checkpoint remains at
its original path. The previous seven-file Phase 3 bundle is preserved in
`phase3_archive/us218_pre_cutover/` before regeneration.

## US-2.19 verified removal queue

The final unrounded Phase 2 trace exactly matched the US-2.15 baseline across
19,984 rows and 82 columns. The three Phase 2 notebooks and affected Phase 3
production, saved checks, replays and analysis also passed in a hash-verified
isolated copy without the Phase 2 archive and retired paths. The current Phase 3
scientific CSVs and C0 events match the preserved pre-cutover bundle byte for
byte; receipts, run IDs and timestamps are run metadata and may differ.

The manually removable Phase 2 queue is [`phase2_archive/`](phase2_archive/).
It includes **`phase2_general_dataset_archive.ipynb`** and
**`run_phase2_general_dataset_archive.py`** under `phase2_archive/scripts/`,
the former `phase2_current/`, old reports, exports, workbook and logs. Preserve
the workbook and other material externally if needed before removal. The
separate Git-ignored [`phase2_baseline_us215/`](phase2_baseline_us215/) is the
recovery checkpoint, not part of the archive queue; back it up separately
before moving it out of the workspace. Verification did not move or delete
either directory.

## Expected files
1. raw_index.csv
2. aligned_phase1_temperature.csv
3. phase1_average_statistics.csv
4. phase2_temperature_sensors.csv
5. phase2_temperature_metrics.json
6. transformation_qc_report.csv
7. Historical `transformation_decisions.md` (run records are preserved in
   [project history](../project_history.md#transformation-run-records))
8. phase3_sensor_history_events.csv
9. phase3a_phase2_baseline.json
8. phase3_sensor_history_events.csv
9. phase3a_phase2_baseline.json

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

## Phase 3A Matched Phase 2 Baseline
`phase3a_phase2_baseline.json` is the compact Phase 2 result for the fixed
A/C/D/E/F/G cohort and approved 19,984-bucket interval. It records the
`phase3a_stable_cohort` P90, message category totals, resynchronization count,
membership-change checks, evaluated bucket count, and centralized
119,904-transmission reference. The Phase 3 notebook generates it from an
in-memory run of the existing Phase 2 monitor; a duplicate row-level trace is
not persisted.

## Phase 3A Matched Phase 2 Baseline
`phase3a_phase2_baseline.json` is the compact Phase 2 result for the fixed
A/C/D/E/F/G cohort and approved 19,984-bucket interval. It records the
`phase3a_stable_cohort` P90, message category totals, resynchronization count,
membership-change checks, evaluated bucket count, and centralized
119,904-transmission reference. It is generated by the Phase 3 notebook from an
in-memory run of the existing Phase 2 monitor; the large per-row trace is not
duplicated as a separate matched-baseline artifact.

## Standalone Phase 1 duplicate audit

The production `transformation_qc_report.csv` includes
`excluded_non_source_csv_filenames`, a JSON array of present aggregate filenames
excluded during discovery. The same list appears in run JSON and the decisions
log. Production Phase 1 now reads timestamped sources without `temperature_raw.csv`;
the standalone all-files investigation below intentionally retains its original
default population.

`phase1_duplicate_qc/phase1_source_exclusion_comparison.json` records the
production rerun's QC/gates, before/after aligned-output hashes, timestamp and
availability comparisons, exact per-sensor/all-device-average changes, and
Phase 3A structural validation. The 2026-11-03 aligned output was byte-for-byte
unchanged after excluding the aggregate.

`phase1_duplicate_qc/` contains the independently generated
`qc_phase1_duplicate_summary.json` and compact
`qc_phase1_duplicate_conflicts.csv`. Generate them with
`python scripts\qc_phase1_duplicate_keys.py`; see the
[script usage](../scripts/README_scripts.md#standalone-phase-1-duplicate-key-qc)
for definitions and options. This audit reads raw sources only and does not
run the transformation or replace any existing pipeline outputs.

Run `python scripts\qc_phase1_duplicate_keys.py --exclude-temperature-raw`
for the separate `phase1_duplicate_qc/excluding_temperature_raw/` investigation.
It preserves the original reports and writes the reduced-population summary,
conflicting examples, and `qc_phase1_unmatched_records.csv` with every exact
value-and-multiplicity mismatch between the aggregate and timestamped sources.
The unmatched export is intentionally exhaustive and can be large.

## Phase 3A FMIC results

`phase3a_fmic_events.csv` contains one compact selected clustering/allocation
row per FMIC root synchronization. `phase3a_fmic_summary.json` records actual
transmission categories, correctness, provenance hashes, and the matched Phase 2
comparison. Regenerate fixed-alpha references only by explicitly calling
`run_phase3a_fmic` / `run_phase3a_smic` from `scripts.phase3_implement`.
The Phase 3 notebook's normal execution preserves these references and runs
the historical sweep. Core implementation now resides in
[`phase3_implement.py`](../scripts/phase3_implement.py); tests import it directly
without running production or extracting notebook cells.

The US-3.19 run at alpha 0.10 processes 19,984 buckets with 11,922 messages,
293 root synchronizations, and zero false-safe or false-violated buckets.
The matched Phase 2 baseline and historical Phase 2-scheduled clustering-event
artifact are preserved, not replaced by FMIC. Full sensor-minute traces are
not generated.

See [FMIC usage and methodology](../scripts/README_scripts.md#end-to-end-fmic-and-smic-us-319-us-320)
for discounted first moments, the labeled project zero-weight fallback,
both-sides distance monitoring, and separate-root communication accounting.

## Notes
1. Generated pipeline outputs may be overwritten by their owning workflows; sealed checkpoints and historical references must be preserved. Revised Phase 3 production writes to its separate output directory, not this folder's root.
2. In a source-only GitHub repository, keep this README tracked but generate the artifact files locally instead of committing them.

## US-3.27 recoverable Phase 3 baseline

[`phase3_baseline_us327/`](phase3_baseline_us327/) is an intentionally Git-ignored
local checkpoint, not a normal overwriteable pipeline output. Preserve this
directory throughout consolidation and back it up separately if needed; a Git
clone alone does not recover its generated evidence.

- `original_checkpoint.zip` and `checkpoint_inventory.json` preserve 85 original
  files with verified SHA-256 hashes, CSV headers/row counts, JSON top-level keys,
  notebook cell tags, and tracked/untracked classification.
- `baseline_report.json` records actual baseline commands, environment,
  provenance dependencies, known gaps and their resolution, and all 41
  configuration summaries, synchronization timelines, and evidence hashes.
- `full_matrix_evidence/` contains all 819,344 per-bucket decisions and 16,210
  initialization/root-synchronization events. This is one-off migration evidence,
  not a new normal sensor-history export or new scientific analysis.
- `reference_workspace/` contains the isolated validation results. Original
  checkpoint bytes remain separately preserved in the archive.
- `initial_attempt_report.json`, `initial_production_failure.log`,
  `fresh_equivalence_validation.log`, `regression_tests.log`, and
  `production_evaluation.log` retain both the pre-existing stale-notebook-hash
  failure and the successful validation that resolved it in the isolated copy.
- `verification_results.json` and `checkpoint_seal.json` verify evidence
  integrity and the unchanged original implementation/scientific files.

All controls and alpha runs passed correctness/accounting. The five current
US-3.25 scientific CSVs and US-3.24 equivalence event CSV reproduced byte-for-byte.
The original saved US-3.24 summary remains stale; only the isolated copy received
freshly executed validation metadata. No historical artifacts were overwritten.

See the [checkpoint recovery and replay instructions](../scripts/README_scripts.md#us-327-pre-consolidation-checkpoint)
before restoring files or starting implementation extraction.

## US-3.28 extraction validation

[`phase3_extraction_us328/`](phase3_extraction_us328/) is a Git-ignored local
validation copy, not a new production artifact contract. Its
`validation_report.json` records actual commands, candidate source hashes,
AST comparisons, exact full-matrix event/decision matches, and scientific CSV
byte comparisons against the sealed US-3.27 baseline. The archived one-off
`validate_us328.py` records the procedure; it is not a maintained production
entry point.

Validation passed 141 existing/new tests, fresh equivalence validation, the
revised evaluation and six independent replays, and clean-process execution of
all historical notebook code cells. All 41 configuration summaries, 819,344
decisions, and 16,210 initialization/synchronization events matched exactly.
Original scientific files and the US-3.27 checkpoint remain unchanged.

Extraction adds implementation-source provenance: revised reports use
`phase3_implementation_sha256`, and historical sweep results/reports use
`implementation_sha256`. Saved pre-extraction reports do not certify current
code and must be regenerated through real validation, not edited to match hashes.
See the [transition instructions](../scripts/README_scripts.md#us-328-importable-implementation-extraction).

## US-3.29 isolated revised production outputs

The canonical `scripts.phase3_implement` command defaults to
[`phase3_current/`](phase3_current/), not the historical artifact root.
`--output-dir` selects a separate candidate directory. Existing scientific
basenames, CSV schemas, precision, and snapshot scope remain unchanged; artifact
redesign is deferred. Since US-3.31, revised plots and detailed interpretation
are rendered by the saved-results-only analysis notebook, not production.

Run regression tests separately to produce a current validation receipt, then
pass it using `--validation-record`; see the
[current commands and provenance rules](../scripts/README_scripts.md#us-329-unified-production-execution).
Production embeds the receipt and verifies its current code/input/configuration
hashes. It does not import test modules or launch a regression suite.

C0 summary/events are reused only when passing runtime checks and all current
provenance/event hashes match. Otherwise, production regenerates genuine
Phase 2/Phase 3 equivalence in the output directory. Original stale equivalence
metadata remains unchanged. A valid original cache is copied into the candidate
directory, not updated in place. Failure diagnostics and a failed completion
record use the current run ID and selected destination; a prior successful report
does not certify a later failed run.

[`phase3_production_us329/verified/validation_report.json`](phase3_production_us329/verified/validation_report.json)
records 148 passing tests, unified production, six independent replays, current
C0 cache reuse, fresh C0 regeneration, and missing/stale validation rejection.
All 41 full summaries, 819,344 decisions, and 16,210 initialization/synchronization
events matched the sealed baseline, and six scientific CSVs were byte-identical.
Production preserved all 63 protected source/configuration/root-level artifact
files in the candidate copy. Original files and checkpoint evidence also remained
unchanged during validation.

The ignored `phase3_production_us329/` directory retains the first isolated
Windows failure and the successful final-source `verified/` workspace, logs,
receipt, reports, and archived one-off verification procedure. It is migration
evidence, not another maintained executable entry point. Back up these local
validation/checkpoint directories separately; Git does not preserve them.

## US-3.30 independent saved-output verification

Use the maintained testing script without rewriting the results:

```powershell
python -B -m scripts.phase3_test --checks saved replay --output-dir artifacts\phase3_current
```

The selected directory must contain current production CSVs, C0 summary/events,
comparison summary, completion record, and zero-failure record. Missing or stale
outputs fail explicitly. Checks reconcile configurations, finite values,
communication/check/cluster-size arithmetic, snapshots against observations,
summary tables/rankings, exact current provenance, source-derived C0 equivalence,
and fresh subprocess replays. A passing saved status alone is not validation.
Results are hash-checked before/after; temporary C0/replay and mutation work does
not overwrite historical or selected production outputs. Optional verification
reports must be outside the selected results directory.

Production now requires a schema-version-2 receipt from
`python -B -m scripts.phase3_test --record-validation <receipt.json>`.
It covers actual behavioral/replay checks and independently owned Phase 2/Phase 1
statistics tests. Earlier receipts/results remain historical, not automatically
re-certified. See the [commands and coverage map](../scripts/README_scripts.md#us-330-consolidated-testing-and-saved-output-verification).

[`phase3_testing_us330/verified/validation_report.json`](phase3_testing_us330/verified/validation_report.json)
records 155 passing tests, unified production for all 41 configurations and six
replays, separate read-only saved-output/replay verification, and explicit
mutation/missing-output/stale-receipt rejection. Six scientific CSVs reproduced
byte-for-byte; 28 scientific definitions were AST-identical. Original files and
the sealed US-3.27 evidence remained unchanged.

This ignored local directory includes the final candidate, receipts/reports/logs,
coverage evidence and archived one-off verification procedure. It also retains
the initial skipped-test serialization failure and an interrupted stricter-check
iteration. These are migration evidence, not maintained entry points or new
scientific artifacts. Back them up separately if needed.

## US-3.31 saved-only analysis and explicit presentation exports

[`scripts/phase3_analyze.ipynb`](../scripts/phase3_analyze.ipynb) reads an explicitly
selected current output directory (default `phase3_current/`) and existing
input/configuration/baseline evidence. Missing or incompatible results fail;
historical directories are never used as an automatic fallback. See the
[notebook settings and usage](../scripts/README_scripts.md#us-331-saved-results-only-analysis-notebook).

Production scientific CSVs and numeric comparisons are unchanged. Revised
comparison JSON now records a versioned `presentation` pointer instead of the
detailed interpretive narrative; `outputs.plots` is empty and
`outputs.analysis_notebook` identifies the notebook. Completion visualization
metadata points to the same saved-only presentation. Five revised charts render
inline; their former PNGs are preserved historical artifacts, not current
production outputs. The historical three-chart sweep view is separately opt-in
and keeps its historical signed-margin Phase 2 denominator.

Normal analysis leaves selected results, scientific source/configuration, and
historical artifacts unchanged. Optional PNG export requires a new separate
directory and retains the original filenames. Saving rendered notebook cells
does not invalidate the production receipt: notebook-source execution evidence
is recorded separately, not folded into scientific provenance. The substantive
independent verifier remains `scripts.phase3_test`.

[`phase3_analysis_us331/verified/validation_report.json`](phase3_analysis_us331/verified/validation_report.json)
records 159 passing tests, isolated production without revised PNG/narrative
side effects, independent saved verification, clean-kernel five/eight-chart
execution, actual artist/table reconciliation, explicit export validation and
missing/stale-input/unsafe-export rejection. Analysis preserved all protected
inputs. Six scientific CSVs reproduced byte-for-byte; 28 scientific definitions
and the relocated interpretation remained AST-identical.

This ignored local evidence includes the candidate, logs, executed notebook
copies, chart-series audits, checked PNG exports, original presentation sources,
and archived one-off procedure. The interrupted receipt-coupling iteration is
retained separately. None is another maintained analysis entry point or new
scientific experiment. Back up these local validation directories separately.

## US-3.32 final-source cutover evidence and current prerequisites

[`phase3_cutover_us332/verified/validation_report.json`](phase3_cutover_us332/verified/validation_report.json)
is the final-source retirement gate. The isolated candidate contains exactly the
three maintained Phase 3 executable files, without the original production
notebook or six facades. Evidence includes actual test/production/saved-check
logs and receipts, complete 41-configuration summaries, all raw events and
compressed per-bucket decisions, clean-kernel notebooks and real chart/table
audits. It verifies the original checkpoint archive and sealed evidence before
retirement. `pre_cutover_entry_points.zip` preserves the seven immediately
preceding files with recorded hashes; use the complete US-3.27 checkpoint for
standalone rollback, not just this supplementary archive.

The gate passed **162 tests**, all **41 configurations / 819,344 decisions /
16,210 events** exactly, all six byte-identical scientific CSVs, both real-kernel
analysis views and three expected failure cases. The
[active-checkout report](phase3_cutover_us332/verified/active_checkout_report.json)
records successful default production, independent saved/replay checks and
five-chart clean-kernel analysis after retirement. `phase3_current/` contains
the usable default result bundle, not relabeled old evidence.

At the US-3.32 cutover, `phase2_current/` held genuinely regenerated
`phase3a_phase2_two_sided_baseline.json` and
`phase3a_phase2_two_sided_events.csv` for the final Phase 2 producer code.
The old notebook-only integrity dependency is gone; monitoring algorithms are
unchanged. The event CSV must match the preserved revised Phase 2 event CSV
byte-for-byte. The baseline's source hashes/integrity inventory and validation
commands are new metadata, not changed science. Original root-level baseline,
events and historical signed-margin comparator remain unmodified.

This historical layout has been superseded by the split Phase 2 contract at the
top of this document. Current consumers reject missing or stale evidence and
do not fall back to these historical paths.
Earlier story candidates are not current production results.

These are ignored local validation/recovery/prerequisite directories, not extra
maintained scripts or an artifact redesign. Preserve a separate backup.
US-3.33 subsequently obtained approval for the artifact consolidation below.

## US-3.33 approved current artifact contract

> Historical schema-version-1 bundle documentation. Its `phase3_current` layout
> is superseded by the US-3.34 mapping and paths below.

The user approved this contract on 2026-11-11, including the requirement that
each current bundle filename starts with `phase3_`. The eleven-file US-3.32
bundle and the story-numbered formats described above are historical formats,
not extra current exports. The three maintained workflow files now use this
same **schema version 1** contract.

### Classification and old-to-new mapping

Paths below are relative to the selected current output directory, normally
`phase3_current/`. No root-level historical artifact is moved or renamed.

| Classification | Previous file(s) | Current file / section | Preservation and key |
|---|---|---|---|
| Current scientific results | `phase3a_us325_control_results.csv`, `phase3a_us325_alpha_results.csv` | `phase3_results.csv` | 3 controls + 38 clustered rows; key `(config_id, alpha_label)`; union of old columns plus `configuration_kind` |
| Current scientific diagnostics | `phase3a_us325_control_cluster_size_summary.csv`, `phase3a_us325_cluster_size_summary.csv` | `phase3_cluster_sizes.csv` | 18 + 228 rows; key `(config_id, alpha_label, cluster_size)`; retain all size 1–6 bins, including zeros |
| Selected scientific snapshots | `phase3a_us325_event_snapshots.csv` | `phase3_snapshots.csv` | Original 2,372 rows/columns/bytes; key `(config_id, alpha_label, synchronization_id)` |
| Complete C0 synchronization evidence | `phase3a_protocol_equivalence_events.csv` | `phase3_equivalence_events.csv` | Original 467 rows/columns/bytes; key `bucket_epoch`; distinct from weighted snapshots and per-bucket traces |
| Scientific comparisons + execution/provenance | `phase3a_us325_comparison_summary.json` | `phase3_run.json#/comparison` | Preserve scientific tables, minima, limits, controls and diagnostic meanings |
| Completion/validation summary | `phase3a_us326_completion_summary.json` | `phase3_run.json#/completion` | Preserve regression, integrity, grid, replay, presentation and failure-policy information |
| Durable attempt failures | `phase3a_us325_failed_configurations.json` | `phase3_run.json#/failures` | Preserve failure count, reasons, stage/configuration, metrics and integrity diagnostics |
| C0 runtime validation | `phase3a_protocol_equivalence_summary.json` | `phase3_run.json#/equivalence` | Preserve full runtime comparison, checks, truth/accounting and provenance; not a regression receipt |
| Independent external test receipt | `validation.json` and duplicate embedded receipt | `phase3_validation.json` | Actual independently executed receipt retained byte-for-byte; comparison stores only `{artifact, sha256}` reference |

Historical references comprise original root-level scientific CSV/JSON,
fixed-alpha/sweep reports, signed-margin and revised Phase 2 references, prior
story evidence directories and sealed checkpoint/recovery archives. They remain
immutable, separately identified by original paths and SHA256 hashes. Current
Phase 2 prerequisites remain separately owned in `phase2_outputs/` and
`phase2_operational/`; they are not absorbed into the six Phase 3 outputs. Derived presentations remain
inline in the analysis notebook; existing PNGs are preserved historical outputs.
Explicit separate-directory PNG export remains optional, not part of this bundle.

Redundancy removed: separate control/alpha table navigation, separate control/
alpha size-table navigation, four sibling metadata files and the duplicated
full external receipt. Substantive diagnostics are retained under namespaces,
even when an existing summary intentionally repeats numerical checks.

### Shapes, units, precision and missing values

- `phase3_results.csv` has 41 records. `configuration_kind` is exactly `control`
  or `clustered`; C0/C1/C2 are controls. Existing field names/meanings are retained.
  Control `alpha` and the five clustered-only contrast fields are empty/null;
  `alpha_label` and `alpha_status` remain `not_applicable`. Clustered alpha labels
  retain two decimal places. The five contrast fields are
  `reduction_vs_revised_phase2_percent`, `revised_phase2_message_difference`,
  `matched_singleton_message_difference`, `matched_singleton_reduction_percent`,
  and `matched_singleton_root_synchronization_difference`.
- `phase3_cluster_sizes.csv` has 246 records, including control
  `alpha_label=not_applicable`. All existing integer counters and zero-count bins
  are preserved. No counts are averaged or inferred during combination.
- CSV integers remain integer counts, not pandas-induced decimal strings.
  Finite continuous values retain round-trip precision. ISO timestamps stay UTC,
  epochs stay whole Unix seconds, observation/event ordering stays unchanged,
  and JSON-valued cells retain their original contents.
- Counters measure actual transmissions, checks, root synchronizations, sensor
  memberships or buckets as named, not bytes, latency or counterfactual avoided
  synchronization. Share/reduction fields ending in `percent` are percentages,
  not fractions. Alpha, normalized histories, scaled weights and partition
  quality are dimensionless. Temperature means, raw histories, first moments,
  allowances, conservative terms and raw moment weights use temperature units;
  SMIC second moments use squared temperature units and remain an unnormalized
  discounted central squared-deviation sum, not population/sample variance.
- Empty CSV cells mean unavailable/not applicable, never zero or an imputed
  value. FMIC second moments/conservative terms remain empty. C0's unavailable
  raw-event fingerprint remains empty, distinct from its verified equivalence
  CSV event hash. Zero-share conventions remain explicit.
- Synchronization counts and snapshots include initialization. Initialization
  is not a moment observation; histories and moments persist across subsequent
  synchronizations.

### Capture scope and comparator identities

`phase3_equivalence_events.csv` contains **all C0 initialization/root-sync
events**, with its original Phase 2/Phase 3 trigger/state/reference/allowance/
message schema. Full C0 per-bucket equivalence is checked at runtime but the
19,984 decisions are not presented as rows in this event file.

`phase3_snapshots.csv` contains **all C1/C2 synchronization snapshots**, plus
FMIC/SMIC alpha 0.10 and every tied tested-grid minimum. Currently the minimum
is 0.65 for each method: C1/C2 contribute 457 each; FMIC/SMIC at 0.10 contribute
293 each; FMIC/SMIC at 0.65 contribute 436 each. No C0 rows occur here, and
other alpha configurations do not acquire fictitious complete snapshots.
All 41 configurations remain fully represented in results and size diagnostics.

Revised two-sided Phase 2/C0 remains the **9,159-transmission / 467-sync**
primary comparator, identified by its baseline hash. Historical signed-margin
Phase 2 remains separately identified at **38,087 / 2,107**; centralized
transmissions remain **119,904**. Prespecified alpha 0.10 versus exploratory
in-sample grid minima retains its original meaning and limits.

### Run, validation and integrity contract

A successful `phase3_run.json` contains `schema_version=1`, `kind=production`,
`status=passed`, one `run_id`, `comparison`, `completion`, `failures`,
`equivalence`, `semantics` and `artifacts`. The three production sections share
the current run ID, zero failures and passing status. C0 is independently
provenance-checked runtime evidence, not falsely assigned a regression execution.

`artifacts` indexes the other five files by basename and SHA256; CSV entries also
record columns, row count and primary key. The run file does not hash itself;
its exact hash is recorded in separate migration/verification evidence.
`semantics` records the units, nulls, accounting, scope and comparator definitions.
Comparison provenance hashes the canonical JSON equivalence section using sorted
keys, compact separators and `allow_nan=False`, replacing the former sibling
summary-file hash. This retains equivalence integrity without a redundant file.

`comparison.validation` contains only the local receipt basename and its SHA256.
The loader verifies the receipt bytes and current source/input/config/reference/
test scope independently before exposing receipt data in memory to analysis.
Production copies an external receipt without editing it if needed; it does not
manufacture passing test results. Saving notebook outputs still does not change
scientific provenance.

Readers reject missing files, incompatible versions/kinds, extra legacy-format
files in a production bundle, mismatched hashes/columns/row counts, wrong
configuration/null semantics, mixed run IDs, stale receipts and substantive
scientific corruption. An inventory hash is not a substitute for independent
accounting/source/snapshot/replay verification.

Before work starts, the run becomes `in_progress`. Exceptions replace its success
identity with `status=failed` and durable failure/completion diagnostics. Old
tables may remain for diagnosis but cannot be certified by that failed attempt.
A standalone `--equivalence` run writes only `phase3_run.json` with
`kind=equivalence` plus `phase3_equivalence_events.csv`; it is runtime evidence,
not a completed six-file production bundle or regression receipt.

### Migration and recovery

Old-format output directories fail without changes; no implicit rewriting,
fallback reader or duplicate legacy-format exports are provided. Generate a
candidate in a new directory and use a newly executed validation receipt for the
final writer/test revision. Update the notebook's `OUTPUT_DIR` to that candidate
for clean-kernel analysis.

The immediately preceding current bundle was preserved, byte-for-byte, in
[`phase3_artifacts_us333/pre_migration_current.zip`](phase3_artifacts_us333/pre_migration_current.zip),
with all eleven hashes/sizes in
[`pre_migration_inventory.json`](phase3_artifacts_us333/pre_migration_inventory.json).
The US-3.32 source/evidence and US-3.27 complete checkout checkpoint remain
separate recovery points; restore only into a new empty directory.

The isolated final-source evidence is in
[`phase3_artifacts_us333/verified/phase3_validation_report.json`](phase3_artifacts_us333/verified/phase3_validation_report.json).
It records actual tests/production/replays, every field/record mapping,
byte-identical snapshot/equivalence CSVs, scientific JSON equality,
corruption rejection, clean-kernel chart/table checks and original-file hashes.
The gate passed **166 tests**, all 41 result/246 size-record field comparisons,
all 2,372 snapshot/467 event byte identities, eight corruption rejections,
five/eight-chart real-kernel analysis and three expected notebook failures.

The exact proven bundle is now in `phase3_current/`. The
[active-checkout report](phase3_artifacts_us333/verified/phase3_active_checkout_report.json)
confirms current receipt provenance, independent saved/replay checks and
five-chart clean-kernel analysis passed with unchanged published bytes.
The previous eleven-file current directory is also retained at
[`phase3_artifacts_us333/previous_current/`](phase3_artifacts_us333/previous_current/);
this is an explicit relocation of superseded current results, not a relocation
of root-level historical/reference artifacts.

The first directory-rename publication attempt hit a Windows file lock after
safely preserving the previous bundle. Its failure report/procedure are retained.
Publishing the same proven bytes into a fresh current directory, with the run
record last, succeeded and passed active checks; no scientific/provenance
acceptance condition was relaxed.

One-off procedures are archived evidence, not additional maintained scripts.
All ignored local recovery/evidence directories require a separate backup.

## US-3.34 current layout and complete migration inventory

The US-3.34 verified layout is `phase3_outputs/`, `phase3_operational/`, and
`phase3_archive/`. The archive contains 28 former root-level Phase 3 files plus
the six-file `phase3_current/` bundle, all preserved byte-for-byte. The two
root-level `phase3a_phase2_two_sided_*` files were separately owned Phase 2
outputs outside that Phase 3 cleanup; they were later moved to `phase2_archive/`.
Paths in the following tables are relative to `artifacts/` unless otherwise
stated.

### Active user-facing outputs and operational run files

The current default production has run ID
`2026-11-12T22:58:38.165659+00:00`. The three pre-existing result tables and
C0 events remain byte-identical to their pre-trace recovery copies.

| Active path | Meaning and producer / consumer | SHA-256 |
|---|---|---|
| `phase3_outputs/phase3_results.csv` | 41 user-facing control/clustered result rows; producer `scripts/phase3_implement.py`; readers `scripts/phase3_test.py` and `scripts/phase3_analyze.ipynb` | `8BFE508355FD1DE0254A5F4F17C3B65CA4E94B57ED99D7F16C79BAFE9D3B9BEF` |
| `phase3_outputs/phase3_cluster_sizes.csv` | 246 diagnostic size-bin rows, including zero bins; producer `scripts/phase3_implement.py`; readers test and analysis | `2F0CF6EDB96904DD986D2345D610CB481B6A8EA0C7761158638786BA159B4AC2` |
| `phase3_outputs/phase3_snapshots.csv` | 2,372 selected synchronization snapshots; producer `scripts/phase3_implement.py`; readers test and analysis | `B9C2C65B0EBB25BA960E8CF668F141B08E10B4BBD618E0A0DA1023B19A00AC6C` |
| `phase3_outputs/phase3_selected_trace.csv` | 119,904 selected-configuration minute rows across six configurations; 163,626,312 bytes; producer `scripts/phase3_implement.py`; validated by tests and read-only analysis | `867AB20D72FC808114BED47EC4F52E27F749C171ECE3A0A7A8254234B08F550E` |
| `phase3_outputs/phase3_summary.json` | Schema-version-1 user-readable comparison summary; producer `scripts/phase3_implement.py`; read-only analysis and saved verification | `28AB267F7253F2B58D339051D40007827FF3B8FD743CDF92BDF1B149E5AE584B` |
| `phase3_operational/phase3_run.json` | Schema-version-2 manifest with status/failure state, completion, provenance and hash inventory; written last by the producer; validated by tests and analysis | `73138B6684BBB744FEE3E64908D149F32CF9FF00705F32622276ED3B8880C4A1` |
| `phase3_operational/phase3_equivalence_events.csv` | 467 complete C0 initialization/root-sync events; producer reuses the validated reference; checked by tests/manifest and not substituted for snapshots | `FF4A89ECEC934A96456EEEFA5E154B580B6DDAC2251EF2711250380F2D489FCF` |
| `phase3_operational/phase3_validation.json` | Current, independent schema-version-2 receipt for 175 tests, including the Phase 1/Phase 2 suites; producer `scripts/phase3_test.py`; hash-referenced by the summary | `F1403947890D2C6C78BEB39446DA9EEC15BEA03EC3C9D17EBCA5A4DA2DFACDF9` |

The manifest hashes the four result CSVs, summary, and C0 events. The selected
trace is 163,626,312 bytes (about 156 MiB) for the current six-configuration
scope; the exact scope, ordered schema, row count and key are recorded in its
manifest inventory. The summary points to the independent receipt by relative
path and SHA-256; the receipt's SHA-256 is
`F1403947890D2C6C78BEB39446DA9EEC15BEA03EC3C9D17EBCA5A4DA2DFACDF9`.
Every paired file carries the same run ID; missing, stale, failed, or mixed-run
state is rejected. The read-only saved-results loader passed for this run and
its bound evidence. The successful Run-All reused the current 175-test receipt;
production took 520.648 seconds, saved-result/replay checks took 769.468 seconds,
and the complete workflow took 1,290.579 seconds. These are observed end-to-end
stage timings, not an isolated estimate of incremental trace overhead. At the
US-3.34 cutover, the independently executed receipt
replaced the archived receipt; the old receipt was not edited or reused for
the changed code and paths.

The US-3.36 one-click runner reuses a current receipt, runs production, and
verifies saved results/replays. Before replacing canonical files it retains a
per-run copy of the eight owned outputs/evidence files under
`phase3_operational/runner_recovery/<run-id>/previous/`, alongside the runner
status and per-stage subprocess logs. Recovery copies and logs are ignored
local evidence and are not deleted by the workflow.

### Operational references copied from root-level originals

Each listed original was copied to the matching path under
`phase3_operational/references/` and verified byte-identical by SHA-256 before
its root-level original was moved into the archive. The archived original keeps
its basename and original hash. Current producers do not overwrite these
immutable references.

| Original path | Operational destination | Current consumer and retained purpose | Original SHA-256 |
|---|---|---|---|
| `phase3a_alpha_results.csv` | `references/phase3a_alpha_results.csv` | `scripts/phase3_analyze.ipynb` historical sweep view; test reference | `00A8BAB5878030BCD5582462FC5DC572CF88AFAE35D328D591CAC4817E7FCC14` |
| `phase3a_comparison_summary.json` | `references/phase3a_comparison_summary.json` | Notebook historical comparison and test reference | `D8D6F02B10B491B137578C379B3DE72873760731A219D8E176CEB80ABE9AA93D` |
| `phase3a_fmic_events.csv` | `references/phase3a_fmic_events.csv` | `scripts/phase3_test.py` fixed-alpha event regression | `AD6EFA5A9EA65E728F87F95D860F4AE7FD7CFC6AACD8A074F2F79708A1DF0539` |
| `phase3a_fmic_summary.json` | `references/phase3a_fmic_summary.json` | `scripts/phase3_test.py` singleton/fixed-alpha independent reference | `60F25FED495A7DCF1D4FBFA4347FC761F413195A0177DA39629613A368F5C371` |
| `phase3a_phase2_baseline.json` | `references/phase3a_phase2_baseline.json` | `scripts/phase2_monitoring.py` and Phase 3 comparator validation; preserves the signed-margin identity | `4FCA257E651000433CAAA7B83E70B0F10CA32F77B0840E896479EEB7BC5C2127` |
| `phase3a_protocol_equivalence_events.csv` | `references/phase3a_protocol_equivalence_events.csv` | Producer/test C0 runtime-equivalence reference | `FF4A89ECEC934A96456EEEFA5E154B580B6DDAC2251EF2711250380F2D489FCF` |
| `phase3a_smic_events.csv` | `references/phase3a_smic_events.csv` | `scripts/phase3_test.py` SMIC fixed-alpha event regression | `88DBF4ABBB479C91C1B1520F93BC1448EE6E52FD7D0C07B139E8196C6AD4B97C` |
| `phase3a_smic_summary.json` | `references/phase3a_smic_summary.json` | `scripts/phase3_test.py` SMIC fixed-alpha independent reference | `8931DF37B8E3F87ADE1CE55ABFE54180E5F9819E838A711348D074222FAB0D5E` |
| `phase3a_us325_alpha_results.csv` | `references/phase3a_us325_alpha_results.csv` | `scripts/phase3_test.py` independent 38-configuration results | `E4F7B494785CAF0C7127A890A9A9A5746DE76875BFFDD053A9C7CBBF13665F1A` |
| `phase3a_us325_cluster_size_summary.csv` | `references/phase3a_us325_cluster_size_summary.csv` | Test reference for clustered size bins | `0E4F00356B58051D3BF7D76E1A30D99A4E2C8EC39E3D0A6B0FA744CFD492A8D9` |
| `phase3a_us325_control_cluster_size_summary.csv` | `references/phase3a_us325_control_cluster_size_summary.csv` | Test reference for control size bins | `7E934DA6A8060E6658B617A0DB97DFFA2087F33E79B5217FA5F2CAD9980BC90C` |
| `phase3a_us325_control_results.csv` | `references/phase3a_us325_control_results.csv` | Test reference for C0/C1/C2 control results | `644659E9A89FB61288B8C95F7B349626C4CB16A88482ED2DAB22F3BFD319014F` |
| `phase3a_us325_event_snapshots.csv` | `references/phase3a_us325_event_snapshots.csv` | Test reference for preserved selected snapshot content | `B9C2C65B0EBB25BA960E8CF668F141B08E10B4BBD618E0A0DA1023B19A00AC6C` |
| `phase3a_validation_summary.json` | `references/phase3a_validation_summary.json` | Prerequisite/validation compatibility checks in `scripts/phase3_implement.py` and tests | `E46D8243875D47C2ECB069610385A3BA0BEC248CA6F897D5A3FC87CBED69B600` |

### Superseded root-level files archived without active consumers

These are historical Phase 3 traces, plots, and metadata. Their former
producers are retired; current code, tests, receipts, and notebook do not read
them. They are preserved at the same basename directly under
`phase3_archive/`; no contents were deleted.

| Original path and archive destination | Current consumer / disposition | SHA-256 |
|---|---|---|
| `phase3_sensor_history_events.csv` | None; superseded full-history trace | `9E567F530A5363D2EA004EFB6366E9EC85FEEBACEB273ABC5DE2C8C9E415D91C` |
| `phase3a_alpha_events.csv` | None; old sweep trace, not the current selected snapshots | `3A30E63CC37BD59416D9AA9D5CAB304C6DE7A98E2F2B18E9F5C29C70CC9258AE` |
| `phase3a_clustering_vs_alpha.png` | None; prior plot, regenerable from retained data | `FA367FEE8550B8EBECB36E0BAAA3F8DE9C7ECCC92FA6B3900CCD1753AAD64E2C` |
| `phase3a_messages_vs_alpha.png` | None; prior plot, regenerable from retained data | `11EA4C79225CCBCD806055F2EF40281569B08721161B99E4BE63D0E49BC899D5` |
| `phase3a_protocol_equivalence_summary.json` | None; superseded by current schema-version-2 runtime manifest | `DC057EF44EE442CA8399483D7651D5CE48AADD48C14E4037987803103121C0D7` |
| `phase3a_synchronizations_vs_alpha.png` | None; prior plot, regenerable from retained data | `DD3CE7711038F9B6C7389A8AD1654D4861015252EF2B709004238A9FB7725E02` |
| `phase3a_us325_clustering_vs_alpha.png` | None; prior plot, regenerable from retained data | `8847154E42ECBBE2C8BB398C38569D70C7621D7E997654C74CD00CE546A6EC9C` |
| `phase3a_us325_communication_composition.png` | None; prior plot, regenerable from retained data | `D9F54CA4C5493281654327EC78BB43CFB6156C5EB23F6AF48DF2A7DBCC8C95EB` |
| `phase3a_us325_comparison_summary.json` | None; superseded by the summary/manifest split | `A9E0977B7615453AA3603B1C968A80588E20509374248EBB179467F28BEE20C7` |
| `phase3a_us325_failed_configurations.json` | None; old failure export, current failures persist in `phase3_run.json` | `9BD302513D6F9983EB3661A8EF001AE8A5C5D16D30EC91E5466FF7E11AC71BFF` |
| `phase3a_us325_messages_vs_alpha.png` | None; prior plot, regenerable from retained data | `ADBB4995A8021DBA3CF3FA6AFE1E9230641C4A5A126DF356A669A0AABE465AAC` |
| `phase3a_us325_singleton_communication_composition.png` | None; prior plot, regenerable from retained data | `502981B7BBA5342446062FAD9E96C0DE0A7E791ACCC9AAB153B4E7454E13BB2F` |
| `phase3a_us325_synchronizations_vs_alpha.png` | None; prior plot, regenerable from retained data | `E56FC8B173962343415BAC607AD3267AAFA561300020C0650A70F4016F3C8BE0` |
| `phase3a_us326_completion_summary.json` | None; superseded by the current completion section | `4F765862B671D777BC086715191873E69E26419D53C76FD6D26E4A98F8F3B074` |

### Archived `phase3_current/` six-file bundle

Every file remains at `phase3_archive/phase3_current/<original basename>`.
The result, size, snapshot, and C0 event files were byte-identical to the
verified new tables/events. The old schema-version-1 run manifest and receipt
are retained as historical evidence; a new schema-version-2 manifest and
independently executed receipt were generated rather than rewriting the old
files.

| Original archived path | New active mapping | SHA-256 |
|---|---|---|
| `phase3_current/phase3_results.csv` | `phase3_outputs/phase3_results.csv`, byte-identical | `8BFE508355FD1DE0254A5F4F17C3B65CA4E94B57ED99D7F16C79BAFE9D3B9BEF` |
| `phase3_current/phase3_cluster_sizes.csv` | `phase3_outputs/phase3_cluster_sizes.csv`, byte-identical | `2F0CF6EDB96904DD986D2345D610CB481B6A8EA0C7761158638786BA159B4AC2` |
| `phase3_current/phase3_snapshots.csv` | `phase3_outputs/phase3_snapshots.csv`, byte-identical | `B9C2C65B0EBB25BA960E8CF668F141B08E10B4BBD618E0A0DA1023B19A00AC6C` |
| `phase3_current/phase3_equivalence_events.csv` | `phase3_operational/phase3_equivalence_events.csv`, byte-identical | `FF4A89ECEC934A96456EEEFA5E154B580B6DDAC2251EF2711250380F2D489FCF` |
| `phase3_current/phase3_run.json` | Schema-version-2 `phase3_operational/phase3_run.json` plus user-readable summary; versioned split | `537ADC080ABD92195A7CD6A50E4DB996472E3820279562A537A72377327C2648` |
| `phase3_current/phase3_validation.json` | Replaced by a fresh final-source receipt; old receipt remains archived | `6B89055167FBA05FBE74E6D27569875DD3CD7BC69474D0D04A2EF190BEA44288` |

### Phase 2 ownership exception at US-3.34 (historical)

At US-3.34 these two Phase 2 outputs retained their original root locations and
hashes. Their producer is `scripts/phase2_monitoring.py`; they are not moved to
the Phase 3 archive. Phase 3 validates the separately owned current baseline
under `phase2_current/`. The current split contract at the top of this document
supersedes those paths; neither is a fallback.

| Retained Phase 2 path | SHA-256 |
|---|---|
| `phase3a_phase2_two_sided_baseline.json` | `D31496DD8FD0E76F4FC70CB62D35539B605675292E8A8C9208EB58BF5A570CA2` |
| `phase3a_phase2_two_sided_events.csv` | `446D2E0B552BA603A0815E3275F5EBA37513AC3298A63FB5129029DC3FBA1D2E` |

At US-3.34, the path-only Phase 2 historical-reference relocation changed the source
provenance hash. To avoid rewriting independently owned Phase 2 results, the
Phase 3 contract pinned the original producer hash
`bf0406cc9b6642d2caad3331be88c6540bc9d38c311f59e825d928452f276d58` while
while validating the baseline's other input/config/event provenance. The current
contract instead requires the active producer hash and independent receipt.
The full independent Phase 2 suite passed; Phase 1/Phase 2 source and current
artifact hashes remained unchanged.

### Final-source verification and removal proof

With `phase3_archive/`, `phase3_current/`, and all loose Phase 3 root files
physically outside the checkout, the final-source gate passed 166 tests with
zero skips/failures/errors, including independent Phase 1/Phase 2 suites. Fresh
default production, saved checks, and all six fresh-process replays passed.
Clean-kernel analysis passed both the isolated candidate pairing and the
default `phase3_outputs/` pairing with the optional historical view enabled:
12 displayed tables and 8 inline figures; no files were written. The archive
was then restored byte-for-byte. Users may manually back up its 34 files
elsewhere and remove `phase3_archive/`; no current workflow reads it.

Final validation receipt SHA-256:
`190F120D134FB25F6FF98A66E3301004B6DC83663F054C686E49F8C4D5ADF538`.
The final implementation, test, Phase 2 path/integrity helper, Phase 2 test,
and notebook SHA-256 values are respectively:

- `scripts/phase3_implement.py`:
  `B64CB575D2DF45D1E5AD109F6EB67AC4D47DC4C0D40305A0B392C7C7FD0713FA`
- `scripts/phase3_test.py`:
  `A965D9EA1AB457107913119C21F6F6424ACCB1374005D2B08C89B3222DDB6121`
- `scripts/phase2_monitoring.py`:
  `B9EB93A7506E48058B3512FF3C20753F3AE457681A93FA6584693CA5424263F7`
- `scripts/test_phase2_monitoring.py`:
  `A9807EA3074ABF6908FBC2675EA19A127E36ED0D8928A706AAB522EC56BF41B1`
- `scripts/phase3_analyze.ipynb`:
  `0C8E0050C1BF47F38F1834AF572ABF1C83289EE4108C5187D33981EFD76B603E`
