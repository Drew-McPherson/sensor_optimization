# Change Log

This file tracks implemented changes in this repository.

## Logging Policy

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

## Notes

- Archive files were intentionally not modified unless explicitly requested.
- This changelog is now the canonical running record for implemented changes in this repository.
