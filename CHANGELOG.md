# Change Log

This file tracks implemented changes in this repository.

## Logging Policy

## 2026-08-28

### 3. Consolidated CSV report export into the Phase 2 notebook and retired standalone exporter scripts
- Summary:
  - Merged CSV report generation logic into `scripts/build_phase2_temperature_sensors.ipynb` so a single notebook run now writes both report artifacts directly.
  - Removed standalone exporter scripts `scripts/export_phase2_report_csvs.py` and `scripts/export_phase2_to_excel.py` from active workflow.
  - Tightened notebook-integrated validation to require `phase2_data_dictionary.csv` and `phase2_sensor_reduction_analysis.csv` and validate their schema/coverage invariants.
  - Updated task and documentation references to remove separate report-export execution.
  - Explicitly preserved `artifacts/phase2_temperature_sensors.xlsx` as a stakeholder-owned analysis file (not generated/overwritten by this migration).
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - scripts/export_phase2_report_csvs.py (deleted)
  - scripts/export_phase2_to_excel.py (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Reduces drift risk by keeping report generation and validation in the same execution path as Phase 2 artifact generation.
  - Removes duplicate exporter maintenance surfaces and simplifies operation to one canonical command path (`scripts/run_phase2_notebook.py`).
  - Preserves stakeholder-managed Excel analysis output while avoiding pipeline coupling to Excel tooling.

### 2. Removed duplicate Phase 2 raw-row CSV export artifact
- Summary:
  - Removed generation of `artifacts/phase2_raw_row_results.csv` from the Phase 2 CSV report exporter so the report pipeline now emits only the data dictionary and reduction-analysis outputs.
  - Removed the exporter CLI flag `--raw-output` and the corresponding return payload key.
  - Added a Windows-safe fallback in CSV writing so temporary file rename lock conflicts can fall back to direct overwrite and continue successfully.
  - Deleted stale local `artifacts/phase2_raw_row_results.csv` and `artifacts/phase2_raw_row_results.csv.tmp` artifacts from the active workspace.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - README.md
  - artifacts/phase2_raw_row_results.csv (deleted)
  - artifacts/phase2_raw_row_results.csv.tmp (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Removes a duplicate row-level output that provided no additional data beyond `artifacts/phase2_temperature_sensors.csv`.
  - Reduces storage pressure and avoids unnecessary copy operations.
  - Keeps the export contract simpler and more reliable on Windows-hosted workspaces.

### 1. Consolidated Phase 2 smoke and export-policy validation into notebook Stage 4
- Summary:
  - Added a new Stage 4 validation section inside the Phase 2 notebook that runs smoke-style checks and export-policy checks as part of notebook execution.
  - Retired standalone validation scripts by removing `scripts/phase2_smoke_check.py` and `scripts/validate_phase2_export_policy.py`.
  - Updated VS Code task wiring and documentation so notebook execution is now the primary path for Phase 2 validation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - .vscode/tasks.json
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - scripts/phase2_smoke_check.py (deleted)
  - scripts/validate_phase2_export_policy.py (deleted)
  - CHANGELOG.md
- Rationale and impact:
  - Reduces script sprawl and keeps Phase 2 build/validate behavior in one execution flow.
  - Notebook runs now emit integrated validation output and fail in the same process when required invariants are violated.
  - The reduction-analysis `bucket_epoch` check is performed when `artifacts/phase2_sensor_reduction_analysis.csv` is present; if absent, the notebook reports a skip for that artifact-specific check.

## 2026-08-25

### 2. Restored exported local margin fields while retaining proximity score fields
- Summary:
  - Restored exported `entry_{sensor}_local_margin` columns in the Phase 2 row output.
  - Kept `event_{sensor}_margin_proximity_score` columns so both threshold state and proximity state are available in outputs.
  - Kept trigger/state-machine semantics unchanged (`event_{sensor}_local_deviation >= entry_{sensor}_local_margin`).
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/validate_phase2_export_policy.py
  - scripts/phase2_smoke_check.py
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Restores explicit local-threshold visibility needed for auditability and compatibility with prior schema consumers.
  - Preserves proximity score reporting for distance-to-constraint analysis without changing trigger behavior.

### 1. Replaced exported local margin columns with per-sensor margin proximity scores
- Summary:
  - Updated the Phase 2 row export schema to remove exported `entry_{sensor}_local_margin` columns and add `event_{sensor}_margin_proximity_score` columns for each sensor.
  - The new score is calculated as `entry_delta_global - event_{sensor}_local_deviation`, where positive values are acceptable and negative values indicate violation.
  - Preserved the existing trigger/state-machine behavior (`local_deviation >= local_margin`) so this change is output-schema focused and does not alter core resync semantics.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/validate_phase2_export_policy.py
  - scripts/phase2_smoke_check.py
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - artifacts/phase2_data_dictionary.csv (regenerated)
  - artifacts/phase2_sensor_reduction_analysis.csv (regenerated)
  - artifacts/phase2_raw_row_results.csv (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Removes duplicated margin information from exported outputs while preserving equivalent local-trigger observability through a single proximity score.
  - Strengthens export and smoke validations so future regressions on this schema are caught automatically.

## 2026-08-24

### 1. Hid redundant internal resync booleans from exported Phase 2 output
- Summary:
  - Kept the internal `event_resync_consumed_from_prior_row` and `event_resync_triggered_by_local_violation` flags available to the calculation path, but removed them from the exported row schema so the public Phase 2 output only exposes the canonical `event_resync_reason` cause field.
  - Left the state-machine timing, branching, and behavior unchanged while preserving all downstream metrics and communication totals.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - The exported Phase 2 row output no longer contains the duplicated resync booleans, while internal calculations still use them to preserve the original state-machine logic.

## 2026-08-24

### 1. Added recovery-aware resync handling for sensors returning after offline gaps
- Summary:
  - Updated the Phase 2 notebook state machine to detect sensors that were absent in the prior synchronized baseline and force a re-sync when they return with valid readings.
  - Set the canonical reason precedence for `event_resync_reason` to:
    - `negative_delta_from_prior_row`
    - `local_constraint_violation`
    - `sensor_recovered_after_offline`
  - Kept the final export schema unchanged while documenting the recovery case through the existing resync reason field instead of creating a separate final-output column.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Prevents stale local reference and margin state from masking real offline-sensor recovery events.
  - The algorithm now resets the baseline state when a sensor returns after an outage so the resumed sensor cannot remain falsely safe due to an outdated local reference.

## 2026-08-07

### 1. Reordered Phase 2 row output columns for resync state fields
- Summary:
  - Updated the Phase 2 row output schema so `exit_xbar_t0_if_resync` appears immediately after `entry_xbar_t0`, `exit_delta_global_if_resync` appears immediately after `entry_delta_global`, and the standalone `exit_delta_global` column is removed.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv
  - artifacts/phase2_raw_row_results.csv
- Behavior change:
  - Generated Phase 2 row exports now present the resync-state columns in the requested order without the legacy `exit_delta_global` field.

### 2. Removed bucket_epoch from Phase 2 reduction-analysis exports
- Summary:
  - Hardened the Phase 2 CSV report export so the reduction-analysis output does not include a `bucket_epoch` column even if a future upstream change introduces it.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - artifacts/phase2_sensor_reduction_analysis.csv
- Behavior change:
  - The generated reduction-analysis CSV continues to expose only the metric summary columns and no longer carries a bucket epoch field.

### 3. Standardized Phase 2 export rounding to 4 decimal places
- Summary:
  - Updated the Phase 2 CSV report exporter to round exported numeric values to 4 decimal places consistently at the reporting boundary.
  - Added a lightweight validation script to check the exported schema and rounding policy for the Phase 2 artifacts.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - scripts/validate_phase2_export_policy.py
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - The exported row-trace and reduction-analysis CSVs now follow the same 4-decimal reporting convention without introducing a shared rounding helper abstraction.

### 4. Switched Phase 2 observed-global-average to the current row's sensor mean
- Summary:
  - Updated the Phase 2 notebook logic to derive `observed_global_average` from the arithmetic mean of the current row's sensor readings rather than the Phase 1 global-average column.
  - Updated the Phase 2 documentation to reflect the new row-level semantics for the observed global average.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - CHANGELOG.md
- Behavior change:
  - Generated Phase 2 row outputs now report the observed global average based on the same minute's sensor values that the state machine is evaluating.

### 4. Switched Phase 2 to the strict all-devices policy
- Summary:
  - Updated Phase 2 notebook logic to use `average_temperature_all_devices` as the global observation source.
  - Updated Phase 2 p90 selection to use the `all_devices_including_imputed` row from `phase1_average_statistics.csv`.
  - Updated Phase 2 documentation and generated metadata to reflect the new all-devices policy.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - scripts/export_phase2_report_csvs.py
  - scripts/export_phase2_to_excel.py
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - artifacts/phase2_data_dictionary.csv (regenerated)
  - artifacts/phase2_raw_row_results.csv (regenerated)
- Behavior change:
  - Phase 2 now uses the all-devices average and all-devices p90 threshold as the strict policy source.

1. Record every implemented code or documentation change in this file.
2. Add entries in chronological order.
3. Include affected files and a short rationale.
4. Note output/schema changes when artifacts are affected.

## 2026-07-12 to 2026-07-15

### 1. Added per-sensor local deviation outputs in Phase 2
- Summary:
  - Added per-sensor local deviation columns to Phase 2 output.
  - Initial formula was aligned to synchronized reference usage in the active state-machine implementation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)

### 2. Standardized Phase 2 numeric output precision
- Summary:
  - Applied 4-decimal output formatting for Phase 2 exported values.
  - Updated metrics JSON formatting to 4-decimal reporting where applicable.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 3. Reworked Project Plan to prioritize Distributed_Data_Streams alignment
- Summary:
  - Added explicit precedence rule: if conflicts exist, Distributed_Data_Streams takes precedence.
  - Updated locked decisions and Phase 2 semantics toward local-deviation/margin framing.
  - Added category-level communication accounting requirements.
  - Clarified canonical boundary semantics and d=1 bridge to multivariate formulation.
- Affected files:
  - Distributed_Monitoring_POC_Project_Plan.md

### 4. Rebuilt active Phase 2 notebook state machine to match revised plan
- Summary:
  - Implemented explicit synchronized per-sensor reference state.
  - Added scheduled next-row re-sync behavior for negative delta.
  - Added communication-category fields (trigger/request/response/broadcast/total).
  - Added richer event/state fields and diagnostics metadata.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 5. Updated script documentation for new Phase 2 behavior
- Summary:
  - Documented new state machine, policy definitions, and output schema highlights.
- Affected files:
  - scripts/README.md

### 6. Changed local trigger policy to warming-only
- Summary:
  - Updated trigger semantics from absolute-deviation style to warming-only:
    - local_deviation >= local_margin
  - Cooling deviations no longer trigger local re-sync requests.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Writing/Markdowns/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 7. Removed duplicate/legacy state columns and renamed margin fields
- Summary:
  - Consolidated duplicate global state fields by keeping preferred names:
    - kept: prior_xbar_t0, prior_delta_global
    - removed from output: reference_global_average_before, global_delta_before
  - Renamed per-sensor margin columns:
    - from: {sensor}_local_delta
    - to: {sensor}_local_margin
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - Writing/Markdowns/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)

### 8. Removed actual_positive_global output field
- Summary:
  - Removed actual_positive_global from Phase 2 row output.
  - Metrics now use global_violation as the canonical actual label.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 9. Consolidated predicted/count aliases to keep re-sync naming
- Summary:
  - Consolidated predicted_positive_any_sensor into resync_requested_any.
  - Consolidated triggering_sensor_count into resync_requested_count.
  - Updated metrics logic to use resync_requested_any as predicted signal.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 10. Restored sensor request semantics on scheduled re-sync rows
- Summary:
  - Scheduled re-sync rows now still compute local deviation and per-sensor request flags.
  - resync_requested_any now reflects sensor-request activity rather than any system-performed re-sync.
  - This preserves the distinction between sensor requests and scheduled/system resync actions.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

### 11. Keep local evaluation active during negative-delta scheduled rows
- Summary:
  - Scheduled re-sync rows now evaluate local deviations and re-sync request flags instead of blanking them.
  - Sensor requests and system-performed re-syncs remain separate concepts in the output schema.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)

## 2026-07-31

### 12. Enforced changelog-first workflow for all future changes
- Summary:
  - Added a repository-level agent policy that requires `CHANGELOG.md` updates for every implemented change.
  - Added a validation script to check that changelog entries include a required date token and optional text tokens.
  - Added VS Code tasks to run changelog checks quickly during workflow.
- Affected files:
  - AGENTS.md
  - scripts/check_changelog_entry.py
  - .vscode/tasks.json
  - CHANGELOG.md

## 2026-08-05

### 13. Renamed Phase 2 row fields to explicit timing scopes and added transition summary
- Summary:
  - Renamed the Phase 2 row schema to use explicit `entry_*`, `observed_*`, `event_*`, and `exit_*` timing semantics.
  - Added `transition_summary` near the front of each Phase 2 row for compact audit readability.
  - Split overloaded re-sync fields into distinct event-consumption, event-trigger, event-performed, and exit-scheduling fields while preserving the underlying state-machine behavior.
  - Hardened notebook path resolution so direct notebook execution falls back from `Path.cwd()` to the repository root when run from the `scripts` directory.
  - Updated the notebook metrics bindings and repository documentation to match the renamed schema and row invariants.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - Distributed_Monitoring_POC_Project_Plan.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - artifacts/phase2_temperature_sensors.csv (regenerated)
  - artifacts/phase2_temperature_metrics.json (regenerated)
  - CHANGELOG.md
- Rationale and impact:
  - Makes each minute row easier to audit in isolation without changing trigger timing or re-sync timing semantics.
  - Introduces a deliberate breaking schema change by replacing the old Phase 2 column names immediately rather than emitting compatibility aliases.

### 14. Prepared the repository for source-only GitHub publication
- Summary:
  - Added a root `.gitignore` for local environments, raw data, generated artifacts, archives, and temporary files.
  - Replaced machine-specific interpreter paths in VS Code task and launch configurations with interpreter-selection variables.
  - Rewrote setup and repository documentation so GitHub-facing guidance no longer depends on a personal Dropbox path or committed generated outputs.
  - Cleared saved outputs and execution counts from the active Phase 2 notebook and normalized its publish-facing kernel metadata.
- Affected files:
  - .gitignore
  - .vscode/tasks.json
  - .vscode/launch.json
  - instructions/PYTHON_ENV_SETUP_GUIDE.md
  - README.md
  - scripts/README.md
  - artifacts/README.md
  - scripts/build_phase2_temperature_sensors.ipynb
  - CHANGELOG.md
- Rationale and impact:
  - Removes the main machine-specific publication leaks while keeping the executable workflow and documentation intact.
  - Establishes a clear source-only repository boundary so collaborators regenerate raw outputs locally rather than pulling them from Git history.

### 15. Corrected forced re-sync row semantics to prevent false local trigger traffic
- Summary:
  - Refactored the Phase 2 state-machine row loop so rows that consume a scheduled re-sync from the prior row are treated as forced synchronization events.
  - Forced rows now skip local trigger evaluation against prior entry margins, set all per-sensor `event_{sensor}_resync_requested` values to `0`, and keep `trigger_message_count = 0`.
  - Preserved forced re-sync fanout counting (`request/response/broadcast`) and added invariant assertions to guard forced-row semantics.
  - Removed same-row forced+local dual-cause labeling behavior for the current model.
  - Updated Phase 2 documentation and implementation guidance to reflect the corrected forced-row policy and acceptance checks.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/README.md
  - instructions/distributed_monitoring_notebook_required_changes.md
  - CHANGELOG.md
- Rationale and impact:
  - Prevents negative-margin forced rows from generating spurious local trigger messages.
  - Makes communication totals and classification-style diagnostics reflect distinct forced synchronization vs local-trigger events.

### 16. Fixed phase2-smoke-check task quoting for PowerShell execution
- Summary:
  - Replaced the inline `python -c` smoke-check command with a script-backed task that executes `scripts/phase2_smoke_check.py`.
  - Removed shell-dependent quoting complexity that caused inline command parsing failures in PowerShell.
- Affected files:
  - .vscode/tasks.json
  - scripts/phase2_smoke_check.py
  - CHANGELOG.md
- Rationale and impact:
  - Restores one-command smoke validation in VS Code tasks for Windows PowerShell environments.
  - Makes the smoke check easier to maintain and portable across shells.

### 17. Added Phase 2 multi-tab Excel report export
- Summary:
  - Added a dedicated Phase 2 report exporter that writes a three-tab Excel workbook for inclusion-ready reporting.
  - Implemented `Data Dictionary`, `Sensor Reduction Analysis`, and `Raw Row Results` sheets in a fixed order.
  - Defined analysis tab calculations for baseline every-minute communication, actual POC communication, absolute difference, and primary reduction ratio/percent.
  - Added a VS Code task for one-command workbook generation and updated repository documentation.
- Affected files:
  - scripts/export_phase2_to_excel.py
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - requirements.txt
  - CHANGELOG.md
- Rationale and impact:
  - Provides a shareable Excel deliverable without changing Phase 2 state-machine behavior.
  - Improves stakeholder communication by combining metric interpretation and raw traceability in one workbook.

### 18. Switched reporting workflow to CSV-first Phase 2 exports
- Summary:
  - Added a dedicated CSV-first exporter that generates three report artifacts: data dictionary, sensor reduction analysis, and raw row results.
  - Updated the VS Code task to run CSV export directly and removed the Excel dependency from required packages.
  - Updated repository and script documentation to describe CSV outputs and defer workbook stitching to a later step.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - .vscode/tasks.json
  - scripts/README.md
  - README.md
  - requirements.txt
  - CHANGELOG.md
- Rationale and impact:
  - Reduces failure risk from large workbook writes while preserving the full reporting content.
  - Keeps outputs easy to validate, diff, and package later into workbook tabs when needed.

## 2026-08-06

### 19. Added Phase 2 correctness observability fields and alias metrics (non-gating)
- Summary:
  - Added row-level centralized-vs-distributed observability fields to Phase 2 output: `centralized_constraint_state`, `distributed_constraint_state`, `distributed_alert`, `false_safe`, `false_alert`, and `violation_detection_delay_buckets`.
  - Added explicit run-level alias counters in metrics: `false_negative_count`, `false_positive_count`, `false_safe_count`, and `false_alert_count`.
  - Updated CSV report export logic and script documentation to include the new observability schema.
  - Kept behavior observational only: no fail-run gate was introduced for false-safe or false-alert rows.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Makes row-level correctness behavior directly inspectable alongside communication metrics.
  - Preserves current experimentation workflow by reporting contradictions without blocking execution.

### 20. Simplified reduction analysis metrics for CSV report consumption
- Summary:
  - Removed `reduction_ratio_primary` from `phase2_sensor_reduction_analysis.csv` output.
  - Rounded `reduction_percent_primary` values to two decimal places.
  - Removed `reduction_ratio_primary_from_metrics` from `phase2_sensor_reduction_analysis.csv` output.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - CHANGELOG.md
- Rationale and impact:
  - Aligns the analysis artifact with requested reporting format and reduces redundant ratio fields.

### 21. Redefined correctness metrics around implemented re-synchronization
- Summary:
  - Changed Phase 2 row-level correctness fields so `distributed_alert`, `false_safe`, and `false_alert` are based on `event_resync_performed` rather than request-generation bits.
  - Changed confusion-matrix diagnostics so predicted-positive means an implemented re-synchronization occurred on the current row.
  - Updated report/dictionary text and README documentation to distinguish request generation from implemented mitigation.
- Affected files:
  - scripts/build_phase2_temperature_sensors.ipynb
  - scripts/export_phase2_report_csvs.py
  - scripts/README.md
  - CHANGELOG.md
- Rationale and impact:
  - Prevents forced re-sync rows from being misclassified as missed violations solely because local warning evaluation was intentionally skipped.
  - Aligns false-safe/false-negative reporting with the user-requested operational question: whether a violating minute lacked an implemented re-synchronization.

### 22. Removed selected correctness metrics from reduction analysis CSV
- Summary:
  - Removed `ratio_delta_computed_minus_metrics` from `phase2_sensor_reduction_analysis.csv` output.
  - Removed `false_negative_count` from `phase2_sensor_reduction_analysis.csv` output.
  - Removed `false_positive_count` from `phase2_sensor_reduction_analysis.csv` output.
- Affected files:
  - scripts/export_phase2_report_csvs.py
  - artifacts/phase2_sensor_reduction_analysis.csv
  - CHANGELOG.md
- Rationale and impact:
  - Keeps the reduction analysis artifact focused on communication and selected observability counters.
  - Avoids duplicating confusion-matrix-oriented fields in this report output.

## Notes

- Archive files were intentionally not modified unless explicitly requested.
- This changelog is now the canonical running record for implemented changes in this repository.
