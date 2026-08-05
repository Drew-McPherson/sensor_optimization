# Distributed Monitoring POC Project Plan

## 1) How To Read This Plan

This document has two layers:
1. Discussion view for stakeholder alignment.
2. Implementation view with deterministic rules that can be coded directly.

Primary project sequence:
1. Phase 1 transformation creates aligned temperature snapshots.
2. Phase 2 deterministic monitoring consumes those snapshots and emits sensor-level re-sync decisions.
3. Phase 3 extends to multivariate/clustering experimentation after Phase 2 is stable.

---

## 2) Conflict Resolution And Locked Decisions

Precedence rule for this repository:
1. If this plan conflicts with Distributed_Data_Streams (1), the Distributed_Data_Streams (1) definition takes precedence.
2. This plan documents the operational approximation used for deterministic implementation while preserving that precedence.

### 2.1 Scope Changes From Prior Version
1. Prior plan: Phase 2 was multivariate transformation from raw files.
2. Updated plan: Phase 2 is deterministic temperature monitoring over aligned Phase 1 output.
3. Prior multivariate scope is moved to Phase 3.

### 2.2 Locked Decisions
1. Required Phase 2 primary input is artifacts/aligned_phase1_temperature.csv.
2. Required threshold source is artifacts/phase1_average_statistics.csv (recompute p90 each run).
3. Required Phase 2 output is artifacts/phase2_temperature_sensors.csv.
4. Optional raw back-reference to Data/files_csv is allowed but not required for Phase 2 runtime.
5. The local deviation definition is delta_v_i(t) = v_i(t) - v_i(t0_i), where t0_i is the most recent synchronization time for sensor i.
6. Global safety tracking follows the Distributed_Data_Streams formulation: monitor feasibility via margin-to-boundary semantics, with univariate temperature instantiated from p90 and global average.
7. Operational local trigger for this deterministic POC is delta_v_i(t) >= margin_i (warming-only), with default equal local margin assignment at each synchronization event.
8. Global margin uses delta_global = p90 - xbar(t0); logic uses unrounded values and delta may be negative.
9. First-row initialization uses xbar(t0) = row1 global average and initializes per-sensor reference values from row1 sensor values.
10. If re-sync is triggered at row t, updated reference state applies starting row t+1; negative delta at row t schedules re-sync for row t+1.
11. Communication reporting must include category-level counts (trigger, request, response, broadcast, total); request-only counts are retained as a legacy comparator.
12. Canonical boundary convention is fixed for Phase 2 aligned outputs: safe when metric < boundary and violated when metric >= boundary.
13. Predicted positive minute for diagnostics remains explicitly defined in the output and must be documented alongside the trigger semantics used in that run.
14. Recall and precision are diagnostic reporting metrics only, not pass/fail gates.
15. Phase 2 implementation artifact is a separate notebook with multiple cells.

---

## 3) Executive Summary (Discussion View)

### What This Experiment Is Proving
We are testing whether deterministic distributed monitoring, aligned to the Distributed_Data_Streams local-deviation framework, can reduce communication while still issuing warnings around high-temperature periods.

### Why This Design Is Deterministic
The workflow does not train a model. It applies fixed rules over aligned minute-bucket data:
1. fixed threshold source (run-specific p90),
2. fixed local-deviation trigger logic and synchronization update rules,
3. fixed state update timing,
4. fixed counting and evaluation definitions.

### What Success Looks Like
1. Fewer communication events than centralized all-sensor-every-minute messaging.
2. No hidden behavior (all state transitions are logged row-by-row).
3. Diagnostic recall remains high during threshold exceedance windows.

---

## 4) Experiment Scope And Phases

### Phase 0 - Setup And Lock Assumptions
Objective: freeze definitions, metrics, and state-machine semantics.

### Phase 1 - Temperature Transformation Core
Objective: transform raw telemetry into aligned minute snapshots with quality metadata.
Output: artifacts/aligned_phase1_temperature.csv and supporting QC/statistics artifacts.

### Phase 2 - Deterministic Temperature Sensor Monitoring
Objective: execute deterministic local-deviation monitoring and re-sync logic on aligned snapshots, preserving Distributed_Data_Streams semantics in a temperature-only instantiation.
Bridge to source formulation: Phase 2 is the d=1 case of the multivariate framework and is treated as a constrained implementation subset, not a replacement for multivariate scope.
Input: artifacts/aligned_phase1_temperature.csv plus p90 from artifacts/phase1_average_statistics.csv.
Output: artifacts/phase2_temperature_sensors.csv.

### Phase 3 - Multivariate And Clustering Extension
Objective: extend validated monitoring ideas to multivariate/clustering designs after Phase 2 validation.

### Phase 4 - Validation And Packaging
Objective: consolidate metrics, sensitivity results, and stakeholder-ready outputs.

---

## 5) Phase 2 Monitoring Logic (Discussion View)

Per minute bucket:
1. Read the current global average and per-sensor temperatures.
2. If a re-sync was scheduled from the prior minute, perform synchronization first using current readings.
3. Maintain per-sensor synchronized reference values and compute per-sensor local deviations.
4. Evaluate local trigger condition delta_v_i(t) >= margin_i for each sensor.
5. If any local trigger fires, perform one re-sync event for the minute.
6. Recompute global margin from synchronized global state.
7. If the resulting global margin is negative, schedule a re-sync for the next minute.
8. Carry updated state forward starting next minute and log event-level communication counts.

Consistency note:
1. Phase 2 uses local constraints as an operational sufficient-condition proxy for the DDS aggregate deviation bound.
2. The canonical production policy uses the fixed boundary convention defined in locked decisions.

Interpretation:
1. False alarms are acceptable trade-offs for safer coverage.
2. Communication naturally clusters near high-temperature periods.
3. The system is deterministic and auditable, but still evaluated using classification-style diagnostics.

---

## 6) Implementation Specification

### 6.1 Required Phase 2 Inputs
1. artifacts/aligned_phase1_temperature.csv.
2. artifacts/phase1_average_statistics.csv.

Required columns in aligned Phase 1 input:
1. bucket_epoch.
2. bucket_time_utc.
3. per-sensor temperature columns (for example A_temperature through H_temperature).
4. average_temperature_non_imputed_devices (preferred global average).
5. fallback average_temperature_all_devices if preferred column is unavailable.

### 6.2 Threshold Derivation
1. Read p90 from phase1_average_statistics.csv each run.
2. Preferred series: non_imputed_devices_only.
3. Fallback series: all_devices_including_imputed.

### 6.3 State Initialization
For first row (t0):
1. entry_xbar_t0 = row1_global_average.
2. entry_delta_global = p90 - entry_xbar_t0.
3. sensor_reference_values[s] = row1_sensor_value_s for each sensor s.
4. local_margin_values[s] are assigned from the active global margin policy for each sensor s.
5. resync_due_next_row = 0.

### 6.4 Per-Row Deterministic State Machine
For each row t:
1. Read `entry_*` state from the prior row's committed `exit_*` state and evaluate whether a scheduled re-sync must be consumed at row t.
2. If scheduled, perform synchronization with current row values and update:
   - reference global state,
   - per-sensor reference values,
   - global and local margins.
3. Compute each sensor's event-local deviation delta_v_i(t) = v_i(t) - v_i(t0_i) using the row's `entry_*` references.
4. For each sensor s, set the event-local trigger bit to 1 when delta_v_s(t) >= margin_s(t), else 0.
5. event_resync_request_count_t = sum(local_trigger_bits_t).
6. If event_resync_request_count_t > 0 and no prior scheduled re-sync was consumed, perform one local-violation re-sync event for row t.
7. Compute actual_positive_global_t from the active boundary policy and record event_any_sensor_requested_resync_t from run-defined trigger semantics.
8. Recompute exit-state global margin after synchronization events; if that margin is negative, set exit_resync_scheduled_next_row_t = 1.
9. Apply any updated reference state starting row t+1.

### 6.5 Row Invariants
For each exported row:
1. `entry_*` fields are the state used to evaluate the current row.
2. `observed_*` fields are the raw values for the current minute bucket.
3. `event_*` fields record outcomes produced during the current minute.
4. `exit_*` fields describe the state committed at the end of the row and carried into the next row.
5. `transition_summary` is an early-row audit field summarizing the row's event and exit-state transitions.

### 6.6 Required Phase 2 Output Schema
artifacts/phase2_temperature_sensors.csv must include:
1. bucket_epoch, bucket_time_utc.
2. early audit fields: transition_summary, p90_threshold_used.
3. row-level global timing fields: observed_global_average, entry_xbar_t0, entry_delta_global, exit_delta_global.
4. optional resync-result fields: exit_xbar_t0_if_resync, exit_delta_global_if_resync.
5. per-sensor current value, synchronized entry reference value, event-local deviation, and entry local allowance fields.
6. one binary event-local trigger/re-sync-request flag per sensor (for example event_A_resync_requested).
7. event_triggering_sensor_names, event_resync_request_count, event_any_sensor_requested_resync.
8. re-sync consumption, trigger, execution, and scheduling fields (for example event_resync_consumed_from_prior_row, event_resync_triggered_by_local_violation, event_resync_performed, exit_resync_scheduled_next_row).
9. synchronization reason fields (for example local_constraint_violation, negative_delta_from_prior_row).
10. communication event fields: trigger_message_count, request_message_count, response_message_count, broadcast_message_count, total_message_count.

### 6.7 Phase 2 Implementation Artifact
Required implementation artifact:
1. scripts/build_phase2_temperature_sensors.ipynb.

Notebook sections (cells):
1. Load input artifacts and constants.
2. Derive p90 and discover sensor columns.
3. Execute deterministic row-wise state machine.
4. Export phase2_temperature_sensors.csv.
5. Compute and export diagnostics summary.

---

## 7) Metrics And Evaluation

### 7.1 Label Definitions
1. Actual positive minute: observed_global_average >= p90 (canonical aligned output rule).
2. Predicted positive minute: derived from the run's local trigger/re-sync rule and explicitly logged as event_any_sensor_requested_resync in each run.
3. Any diagnostic variant boundary comparison must be flagged as non-canonical in output metadata.

### 7.2 Communication Metrics
1. Distributed total messages: sum of total_message_count.
2. Distributed category totals: trigger, request, response, broadcast message sums.
3. Centralized baseline sensor messages: buckets * sensor_count.
4. Primary communication reduction ratio:
   1 - distributed_total_messages / centralized_sensor_messages.
5. Legacy comparator ratio (for backward comparability):
   1 - distributed_trigger_messages / centralized_sensor_messages.

### 7.3 Diagnostic Classification Metrics
1. Recall (diagnostic only): TP / (TP + FN).
2. Precision (diagnostic only): TP / (TP + FP).
3. Confusion counts: TP, FP, FN, TN.

### 7.4 Detection Delay
Compute delay by contiguous actual-positive event windows:
1. For each window, find first predicted-positive minute in the same window.
2. Delay is bucket index difference from window start.
3. Report per-window delays and summary statistics.

---

## 8) Quality Gates And Acceptance

### 8.1 Transformation Gates (Phase 1)
Existing Phase 1 quality gates remain unchanged and must pass before Phase 2.

### 8.2 Phase 2 Acceptance Outputs
A Phase 2 run is considered complete when:
1. artifacts/phase2_temperature_sensors.csv is produced.
2. deterministic state fields are populated consistently.
3. communication and diagnostic metrics are exported.
4. run settings and threshold provenance are logged.

Recall is reported for diagnostics and trend tracking, but is not a hard pass/fail gate.

---

## 9) Verification Checklist

1. aligned_phase1_temperature.csv ingestion is explicit and reproducible.
2. p90 is read from phase1_average_statistics.csv each run.
3. phase2 output includes per-sensor reference and local-deviation fields per row.
4. local trigger semantics and boundary policy are explicitly logged for the run.
5. state update timing (apply on next row) is respected, including negative-delta scheduling.
6. communication category counts reconcile with total_message_count per row and in aggregate.
7. old multivariate Phase 2 references are removed from Phase 2 sections.
8. metrics definitions match deterministic rule outputs.

---

## 10) Sensitivity Matrix (Required Reruns)

Run at least these variants:
1. Trigger threshold source series: non_imputed_devices_only vs all_devices_including_imputed.
2. Initial state option: row1 xbar vs first non-null xbar fallback.
3. Boundary sensitivity check: strict > vs inclusive >= (diagnostic comparison only, non-canonical output).
4. Local allowance assignment policy (for example equal allowance vs normalized alternatives).

Report for each variant:
1. distributed total messages and category totals,
2. communication reduction ratio,
3. diagnostic recall and precision,
4. delay distribution,
5. missed event windows (if any).

---

## 11) Deliverables

### Code And Execution
1. scripts/build_phase1_temperature.py (existing).
2. scripts/build_phase2_temperature_sensors.ipynb (new, required).

### Data Artifacts
1. artifacts/aligned_phase1_temperature.csv.
2. artifacts/phase1_average_statistics.csv.
3. artifacts/phase2_temperature_sensors.csv.
4. artifacts/phase2_temperature_metrics.json.

### Documentation
1. Updated project plan.
2. Updated run instructions.
3. Metrics interpretation notes and limitations.

---

## 12) Major Risks And Mitigations

1. Risk: trigger boundary too conservative or too sensitive.
Mitigation: use required sensitivity reruns and compare communication vs missed windows.

2. Risk: drift from Distributed_Data_Streams semantics in implementation shortcuts.
Mitigation: keep precedence rule explicit and include formula-level verification checks for local deviation and synchronization state.

3. Risk: missing global average values at re-sync minutes.
Mitigation: deterministic fallback to prior xbar, explicitly recorded.

4. Risk: confusion between deterministic rules and predictive modeling terminology.
Mitigation: keep language explicit that metrics are diagnostics on rule behavior.

5. Risk: implementation drift between notebook and plan.
Mitigation: enforce schema and formula checks in verification checklist.

---

## 13) Ready-For-Build Checklist

1. Phase 1 artifacts exist and pass quality checks.
2. Phase 2 notebook exists and runs end-to-end.
3. phase2_temperature_sensors.csv is produced with required fields.
4. Metrics JSON is produced with communication and diagnostics.
5. Phase 3 multivariate work remains deferred until Phase 2 review is complete.
