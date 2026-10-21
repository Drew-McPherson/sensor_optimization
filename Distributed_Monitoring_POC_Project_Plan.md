# Distributed Monitoring POC Project Plan

Revision focus (2026-10-21): Phase 3 observed-only experiment protocol, definitive chapter precedence, event-based clustering, source-preserving history, highest-ID coordinators, and synchronization traffic attribution.

## 1) How To Read This Plan

This document has two layers:
1. Discussion view for stakeholder alignment.
2. Implementation view with deterministic rules that can be coded directly.

Primary project sequence:
1. Phase 1 transformation creates aligned temperature snapshots.
2. Phase 2 deterministic monitoring consumes those snapshots and emits sensor-level re-sync decisions.
3. Phase 3 validates FMIC/SMIC clustering on the temperature streams after Phase 2 is validated, first under a fixed-membership condition and then under an explicitly separated dynamic-membership policy.
4. Multivariate extension is deferred until the temperature-only clustering experiment is validated and interpreted.

---

## 2) Conflict Resolution And Locked Decisions

Precedence rule for this repository:
1. The definitive methodology source is `140516editor Book Chapter (Last Version).pdf`, *Clustering for Monitoring Distributed Data Streams*. If this plan or another summary, including Distributed_Data_Streams (1), conflicts with that chapter, the chapter takes precedence.
2. Section 1.4 and Algorithms 1.4.1-1.4.2 define the clustering/monitoring method; the chapter's appendices define moment calculations and source-comparable broadcast accounting.
3. This plan records the temperature-only operational policies and explicitly labeled adaptations without presenting them as source equations. The [Phase 3 user stories](Phase_3_User_Stories.md) translate these policies into acceptance criteria.

### 2.1 Scope Changes From Prior Version
1. Prior plan: Phase 2 was multivariate transformation from raw files.
2. Updated plan: Phase 2 is deterministic temperature monitoring over aligned Phase 1 output.
3. Prior multivariate scope is no longer a prerequisite for Phase 3. Phase 3 first evaluates source-aligned clustering on the temperature-only streams.
4. Multivariate monitoring remains a possible later extension after FMIC/SMIC validation; it must not be mixed into the initial clustering experiment.

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
16. Phase 3 must validate Phase 2 correctness before any clustering comparison is treated as interpretable.
17. Phase 3 must implement and validate FMIC and SMIC separately before any combined comparison is reported.
18. Alpha is a clustering design/tuning parameter, not an established optimum for this dataset. alpha=0.10 may be retained only as a named baseline setting.
19. Required Phase 3 alpha sensitivity sweep is 0.05, 0.10, ..., 0.95. The full sensitivity results must be retained; the best-performing value may be identified after the sweep rather than treated as prespecified.
20. Phase 3 must separate the effect of clustering from the effect of sensor membership synchronization. Fixed-membership and dynamic-membership results must be reported separately.
21. No sensor-value imputation is permitted in any project phase. Missing/stale readings remain missing, never zero or a carried-forward temperature. Comparisons against Phase 2 or centralized baselines must use consistent observed-only availability and denominator policies.
22. Cluster construction must follow the source methodology for history vectors, normalization, partition quality, greedy merge procedure, and FMIC/SMIC allowance weights unless an adaptation is explicitly labeled and justified.
23. History updates must use signed change relative to the active synchronization reference, not change relative to the immediately prior minute.
24. Missing/offline readings must never be silently converted to zero change. Returning sensors must re-enter through the explicit membership/synchronization policy before their history resumes in the dynamic-membership variant.
25. Signed cancellation inside a cluster may suppress unnecessary root escalation only when the monitored global condition remains correct. Local sensor violations must still be detected and logged.
26. Phase 3 communication accounting must separate routine monitoring, cluster collection/checks, root escalation, synchronization, membership change, coordinator reassignment, and total messages.
27. Clustering occurs at initial synchronization and every later completed resynchronization, never on a timer. The resulting partition, coordinators, references, and allowances apply starting on the next row.
28. Accumulated history is retained and discounted across resynchronizations, not reset after clustering; subsequent valid updates use the newly synchronized reference.
29. Each cluster's coordinator is its highest-ID available member, using documented deterministic sensor-ID ordering.
30. Cluster/coordinator information is included with normal synchronization threshold updates. It creates no additional standalone formation/reassignment transmissions; message types and synchronization causes must not double-count bundled traffic.
31. Fixed membership keeps the cohort constant while averaging its currently observed readings. Dynamic departure occurs on the first missing bucket after Phase 1 freshness filtering; departure/return triggers synchronization and reclustering on completion.
32. No minimum active-sensor count is imposed. Zero valid readings imply undefined global mean and threshold decision; observation-dependent synchronization cannot complete until valid readings are available.
33. Count every transmitted request, including requests to offline sensors; count responses only when actually transmitted.

---

## 3) Executive Summary (Discussion View)

### What This Experiment Is Proving
We are testing two linked questions:
1. whether deterministic distributed monitoring, aligned to the definitive chapter's local-deviation framework, can reduce communication while preserving correct global threshold monitoring; and
2. whether source-aligned FMIC/SMIC clustering can further reduce communication through cancellation without concealing required warnings or attributing savings to unrelated membership-synchronization behavior.

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
4. Phase 3 synthetic correctness tests show no global threshold violation is concealed by cluster cancellation.
5. Phase 3 reports communication by cause and message type so clustering savings can be separated from membership-management costs.
6. Alpha sensitivity is reported transparently rather than presenting one selected alpha as an established optimum.

---

## 4) Experiment Scope And Phases

### Phase 0 - Setup And Lock Assumptions
Objective: freeze definitions, metrics, and state-machine semantics.

### Phase 1 - Temperature Transformation Core
Objective: transform raw telemetry into aligned minute snapshots with quality metadata.
Output: artifacts/aligned_phase1_temperature.csv and supporting QC/statistics artifacts.

### Phase 2 - Deterministic Temperature Sensor Monitoring
Objective: execute deterministic local-deviation monitoring and re-sync logic on aligned snapshots, preserving the definitive chapter's monitoring semantics with the documented temperature-only operational policies.
Bridge to source formulation: Phase 2 is the d=1 case of the multivariate framework and is treated as a constrained implementation subset, not a replacement for multivariate scope.
Input: artifacts/aligned_phase1_temperature.csv plus p90 from artifacts/phase1_average_statistics.csv.
Output: artifacts/phase2_temperature_sensors.csv.

### Phase 3 - Temperature Clustering Extension (FMIC/SMIC)
Objective: determine whether source-aligned clustering further reduces communication on the temperature streams while preserving monitoring correctness and making the source of any savings identifiable.

Required sequence:
1. Validate Phase 2 behavior with targeted synthetic and row-level tests.
2. Implement FMIC with fixed membership and validate it independently.
3. Run FMIC alpha sensitivity.
4. Implement SMIC with fixed membership and validate it independently.
5. Run SMIC alpha sensitivity.
6. Add the dynamic-membership synchronization policy as a separate experimental factor.
7. Compare fixed-membership and dynamic-membership variants without mixing their communication totals.
8. Only after these steps, produce the full Phase 2 vs FMIC vs SMIC comparison.

Interpretation rule: the initial Phase 3 experiment remains temperature-only. Multivariate monitoring is deferred so that clustering effects are not confounded with a simultaneous change in dimensionality.

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
4. average_temperature_all_devices (strict global average source).

### 6.2 Threshold Derivation
1. Read p90 from phase1_average_statistics.csv each run.
2. Preferred series: all_devices_observed.

### 6.3 State Initialization
For first row (t0):
1. entry_xbar_t0 = row1_global_average.
2. entry_delta_global = p90 - entry_xbar_t0.
3. sensor_reference_values[s] = row1_sensor_value_s for each sensor s.
4. local_margin_values[s] are assigned from the active global margin policy for each sensor s.
5. resync_due_next_row = 0.

Bootstrap edge-case note:
1. This implementation intentionally preserves the startup phenomenon where a sensor may have no usable value at the first row and therefore carries a null or blank reference/deviation state for a bounded initialization window.
2. This is treated as a known bootstrap condition for the deterministic experiment, not as a production-quality sensor health correction.
3. The phenomenon is retained because it is part of the scenario being studied: exposure to cold-start state initialization, not a silent data-quality repair.
4. Any future variant that eliminates this startup gap must be treated as a deliberate modeling change, not as a bug fix to the current deterministic policy.

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

Implementation precedence rule for `event_resync_reason` when more than one cause is possible in the same row:
1. `negative_delta_from_prior_row`
2. `local_constraint_violation`
3. `sensor_recovered_after_offline`

This hierarchy preserves the strictest state-machine cause first while still recording offline recovery as a documented reason when it is the active cause in the row.

### 6.7 Phase 2 Implementation Artifact
Required implementation artifact:
1. scripts/build_phase2_temperature_sensors.ipynb.

Notebook sections (cells):
1. Load input artifacts and constants.
2. Derive p90 and discover sensor columns.
3. Execute deterministic row-wise state machine.
4. Export phase2_temperature_sensors.csv.
5. Compute and export diagnostics summary.

### 6.8 Phase 3 Source-Aligned Clustering Specification
Phase 3 uses the temperature streams as scalar node streams and preserves the same global temperature threshold objective used for the comparable Phase 2 run.

Source-alignment checkpoints:
1. History vectors follow Section 1.4 of `140516editor Book Chapter (Last Version).pdf`: initialize history at zero and repeatedly discount older history while adding the signed change from the current synchronization reference. Operationally, for a valid reading between synchronization times, update the scalar history as `h_i <- 0.5 * h_i + (v_i(t) - v_i(t_j))`, where `t_j` is the active synchronization reference. Use accumulated history to form the partition at synchronization and retain it afterward; do not reset histories at each resynchronization. Subsequent valid updates use the newly synchronized reference.
2. Do not replace the synchronization-reference difference with `v_i(t) - v_i(t-1)`.
3. Before clustering, normalize the history-vector set by the magnitude of the longest history vector when that magnitude is greater than zero, matching the source normalization that places alpha on a convenient [0,1] scale.
4. If all history magnitudes are zero, record that no informative history-based partition exists and use a deterministic no-clustering/singleton fallback for that clustering event rather than inventing an arbitrary partition.
5. Partition quality must implement the source cluster-quality and partition-quality definitions from Section 1.4 exactly, including the alpha-dependent cluster-size term.
6. The incremental merge procedure must follow Algorithm 1.4.1: begin with singleton clusters, repeatedly select the current worst-quality cluster, merge it with the partner producing the smallest merged-cluster quality, retain each candidate partition, and select the retained partition with minimum partition quality.
7. FMIC must use the source first-moment weighting/allowance calculation.
8. SMIC must use the source second-moment weighting/allowance calculation based on the first moment plus the conservative second-moment term.
9. Coordinator allowance must be derived from member-node allowances using the source rule rather than an independently invented threshold.
10. Formula-level unit tests must compare implementation outputs for history, normalization, cluster quality, merge selection, FMIC/SMIC weights, node allowances, and coordinator allowances against hand-calculated examples.

### 6.9 Phase 3 Monitoring And Membership Policies
#### Fixed-membership condition — primary clustering-effect experiment
1. Hold the sensor cohort constant, not the set of observed contributors. At each row, compute the mean of valid observations from that cohort divided by the observed contributor count; do not fill missing values.
2. Do not trigger re-clustering or synchronization merely because of a membership-policy event.
3. Produce a matched Phase 2 fixed-membership comparator using the same cohort, observed readings, timestamps, and denominator policy; do not compare fixed-membership Phase 3 against a Phase 2 run with different membership behavior.
4. Use this condition to estimate the communication effect attributable to FMIC/SMIC clustering itself.
5. No minimum observed count is imposed. Zero valid readings yield an undefined global mean and threshold decision, not safe/violated labels.
6. Explicitly test changes in the observed denominator. A fixed cohort does not make observed contributors constant or establish monitoring correctness by itself.

#### Dynamic-membership condition — secondary policy experiment
1. Treat sensor departure/return handling as an additional experimental policy, not as part of the clustering algorithm.
2. A sensor with no usable reading must not receive a fabricated zero-change history update.
3. Detect departure on the first bucket without a valid reading after Phase 1 freshness filtering, and return on the first subsequent valid reading. Each departure/return triggers synchronization; reclustering occurs on its completion.
4. When a sensor returns, perform the required synchronization/re-entry handling before resuming its history updates or cluster participation.
5. Attribute requests, responses, and broadcasts caused by membership change to that synchronization cause while retaining their normal transmission-type counts. Cluster/coordinator information travels with threshold updates; do not add duplicate formation/reassignment traffic.
6. Compare dynamic-membership FMIC/SMIC only against a matched Phase 2 run using the same departure/return and availability assumptions.
7. Compute the global mean from currently active sensors with valid readings, using the observed active count as the denominator. There is no minimum active-sensor count.
8. With zero valid readings, record undefined global mean/threshold decision; no sensor value or safe/violated label is fabricated. Observation-dependent synchronization cannot complete until valid readings are available.

#### Event-based clustering lifecycle and coordinators
1. Cluster at initial synchronization and recluster at every later completed resynchronization, including monitoring-triggered, scheduled negative-margin, and dynamic membership-triggered synchronization. There is no periodic clustering schedule; a cluster check alone does not trigger reclustering.
2. Each clustering event records the synchronization event/cause, histories used, partition, coordinator assignments, and activation row. Updated partitions, coordinators, references, and allowances apply starting on the next row.
3. Initialize histories at zero at their required initial starting point. Retain accumulated histories across subsequent synchronizations; missing readings create no synthetic history update, and dynamic return requires re-entry synchronization before history updates resume.
4. All-zero histories use the deterministic singleton fallback, including at initialization. No observation-dependent synchronization or fabricated cluster/coordinator assignment is completed when there are zero valid observations.
5. At clustering, choose each cluster's highest-ID available member as coordinator; a singleton coordinates itself. Document deterministic ID ordering, including numeric versus string representation, and record old/new assignments when they change.
6. Cluster formation/reassignment information is included with new thresholds in normal synchronization updates, with zero additional standalone formation/reassignment transmissions. Transmission types and event causes are separate accounting views, not additive duplicate totals.

#### Cluster monitoring correctness
1. A node-level warming/local-constraint violation must always be detected and logged even when later cluster cancellation prevents escalation to the root.
2. Signed cluster averaging is allowed because cancellation is the intended clustering mechanism, but it may not conceal a violation of the monitored global threshold.
3. If individual-sensor warming is reported as a separate safety signal, that signal remains independent of the cluster-average decision and cannot be canceled by another sensor's cooling.
4. Root/global state after any escalation or synchronization must match the state that would be obtained under the corresponding non-clustered reference calculation for the same available sensors.

### 6.10 Phase 3 Alpha Policy
1. `alpha=0.10` is a baseline design choice only; do not describe it as optimal for the temperature data.
2. Required coarse sensitivity grid: `0.05, 0.10, ..., 0.95` for both FMIC and SMIC.
3. For each alpha, retain cluster assignments, number of clusters, cluster-size distribution, root escalations/synchronizations, coordinator checks, and communication totals by type.
4. Report the full sensitivity curve/table and identify the minimum-communication alpha only after the sweep.
5. If useful, a second local refinement (for example 0.01 spacing around the best region) may be run, but it supplements rather than replaces the required coarse sweep.

### 6.11 Phase 3 Synthetic Correctness Test Suite
The following tests must pass before full-data performance comparisons:
1. Single-sensor warming while the global mean remains below threshold: local warming trigger is detected; global violation is not falsely declared.
2. Warming/cooling cancellation that safely keeps the global mean below threshold: cluster handling may avoid root escalation while logging the local event.
3. Partial cancellation where the global mean still crosses the threshold: cluster logic must escalate/detect the global violation.
4. Sensor unavailable: global denominator/state and membership behavior follow the declared policy; no synthetic zero change is inserted.
5. Sensor returns: required re-entry synchronization occurs before stale history/reference state can be reused.
6. Multiple clusters with one coordinator violation: escalation path and resulting root state are correct.
7. Boundary cases: just below, exactly at, and just above every relevant node/coordinator/global boundary follow the declared `<` versus `>=` convention.
8. Hand-counted communication scenario with 2–4 sensors: every request, response, trigger, cluster check, root escalation, synchronization broadcast, membership message, and reassignment message reconciles exactly to the expected count.
9. History across multiple resynchronizations: accumulated history is retained rather than reset, and subsequent valid updates use the new synchronization reference.
10. Lifecycle/coordinator cases: initialization, consecutive resynchronizations, no-resync intervals, next-row activation, highest-ID selection independent of input order, singleton fallback, and coordinator departure/return.
11. Availability cases: fixed-cohort contributor/denominator changes, dynamic first-missing-bucket departure/return, one valid reading, and zero valid readings with undefined global state.
12. Bundled traffic and offline requests: cluster/coordinator data adds no standalone transmissions to threshold updates; requests sent to offline sensors count without inventing responses.

---

## 7) Metrics And Evaluation

### 7.1 Label Definitions
1. Actual positive minute: observed_global_average >= p90 (canonical aligned output rule).
2. Predicted positive minute: derived from the run's local trigger/re-sync rule and explicitly logged as event_any_sensor_requested_resync in each run.
3. Any diagnostic variant boundary comparison must be flagged as non-canonical in output metadata.
4. Under the Phase 3 observed-only protocol and its matched comparators, a zero-observation bucket has undefined actual global label, not a negative label. Report such buckets separately rather than treating them as safe in diagnostic metrics.

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

### 7.5 Phase 3 Communication Accounting
Report both source-comparable totals and diagnostic detail.

Required message categories:
1. routine node/local-trigger messages,
2. cluster collection/check requests,
3. cluster collection/check responses,
4. coordinator-to-root escalation messages,
5. root synchronization requests,
6. synchronization responses,
7. synchronization broadcasts/constraint updates,
8. standalone membership departure/return messages, only when actually transmitted,
9. standalone coordinator reassignment/re-clustering messages (zero under the bundled-update protocol),
10. total messages.

Rules:
1. A message is one transmission between distinct nodes/components; do not collapse a request and response into one event.
2. Category totals must reconcile exactly to the overall total.
3. For comparison with the source paper, also report a broadcast-style aggregate using one consistent definition documented in run metadata.
4. Phase 2, FMIC, and SMIC comparisons must use the same sensor-availability assumptions for the comparison being made.
5. Count a transmitted request to an offline sensor even if there is no response. Count only actual response transmissions, not expected responses.
6. Include cluster/coordinator information with normal synchronization threshold updates. Count the enclosing transmission once; no extra standalone formation/reassignment message is generated.
7. Record initialization, monitoring, and membership-change causes on synchronization traffic. Cause attribution is a separate view of transmission-type totals; do not sum overlapping views into total messages.
8. Use the same counting rules for initialization and all resynchronization causes. Local computation, absence detection, and coordinator selection are not themselves network transmissions.

### 7.6 Phase 3 Attribution Metrics
For each algorithm and alpha report:
1. total messages,
2. routine monitoring messages,
3. cluster-check messages,
4. root escalation/synchronization messages,
5. membership-management messages,
6. coordinator reassignment/re-clustering events and their zero standalone-message count under bundled updates,
7. communication reduction versus the matched Phase 2 baseline,
8. communication reduction versus centralized all-sensor-every-minute messaging,
9. number of node violations,
10. number of coordinator violations,
11. number of root/global synchronizations,
12. cluster count and cluster-size distribution.

Primary attribution comparison:
`clustering effect = matched fixed-membership Phase 3 result - matched fixed-membership Phase 2 result`.

Membership-policy impact must be reported separately as the difference between fixed-membership and dynamic-membership variants under otherwise matched settings.

Membership-triggered synchronization costs are attributed by cause even though they use normal synchronization request/response/update messages. Cluster information bundled into those updates does not add another message total.

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

### 8.3 Phase 3 Acceptance Gates
Phase 3 may proceed to full-data comparison only when:
1. Phase 2 reference behavior has passed the targeted correctness tests used as the non-clustered comparator.
2. FMIC passes all synthetic correctness and formula-level tests before SMIC results are interpreted.
3. SMIC independently passes all synthetic correctness and formula-level tests.
4. No synthetic test shows a global threshold violation concealed by cluster cancellation.
5. History, partition, merge, allowance, and coordinator calculations match hand-calculated/source-aligned expectations.
6. Communication categories reconcile exactly to total messages.
7. Fixed-membership results are available before dynamic-membership results are used to discuss clustering performance.
8. The alpha sensitivity sweep is complete for each algorithm before a preferred alpha is named.

---

## 9) Verification Checklist

### 9.1 Phase 2
1. aligned_phase1_temperature.csv ingestion is explicit and reproducible.
2. p90 is read from phase1_average_statistics.csv each run.
3. phase2 output includes per-sensor reference and local-deviation fields per row.
4. local trigger semantics and boundary policy are explicitly logged for the run.
5. state update timing (apply on next row) is respected, including negative-delta scheduling.
6. communication category counts reconcile with total_message_count per row and in aggregate.
7. old multivariate Phase 2 references are removed from Phase 2 sections.
8. metrics definitions match deterministic rule outputs.

### 9.2 Phase 3
1. Phase 2 comparator passes correctness tests before Phase 3 comparison.
2. history update uses the active synchronization reference, not prior-minute difference.
3. no missing reading is silently interpreted as zero change.
4. history normalization and alpha handling match the source method.
5. partition quality and greedy merge choices match hand calculations on small examples.
6. FMIC and SMIC allowance calculations are tested separately.
7. node trigger, coordinator check, and root escalation are distinguishable in outputs.
8. local warming detection remains observable even when cluster cancellation prevents root escalation.
9. global violations are identical to matched reference calculations under the same availability assumptions.
10. fixed-membership and dynamic-membership message totals are never pooled in the primary clustering-effect comparison.
11. all Phase 3 message categories reconcile to the overall total.
12. alpha sensitivity outputs preserve every tested alpha, not just the best-performing setting.
13. clustering occurs at initialization and every completed resynchronization, never on a timer, with new state active on the next row.
14. accumulated histories survive resynchronization, and coordinator selection follows highest available sensor ID.
15. zero-observation global state remains undefined, and requests to offline sensors do not imply response messages.
16. bundled cluster/threshold updates are counted once; cause-attribution views reconcile without duplicate traffic.

---

## 10) Sensitivity Matrix (Required Reruns)

### 10.1 Phase 2 Sensitivity
Run at least these variants:
1. Trigger threshold source series: all_devices_observed vs observed-only fallback baselines.
2. Initial state option: row1 xbar vs first non-null xbar fallback.
3. Boundary sensitivity check: strict > vs inclusive >= (diagnostic comparison only, non-canonical output).
4. Local allowance assignment policy (for example equal allowance vs normalized alternatives).

Report for each variant:
1. distributed total messages and category totals,
2. communication reduction ratio,
3. diagnostic recall and precision,
4. delay distribution,
5. missed event windows (if any).

### 10.2 Phase 3 Alpha Sensitivity
For FMIC and SMIC separately, run alpha values:
`0.05, 0.10, 0.15, ..., 0.95`.

For every alpha report:
1. cluster assignments or a reproducible cluster-membership trace,
2. number of clusters and cluster-size distribution,
3. node violations,
4. coordinator checks and coordinator violations,
5. root/global escalations and synchronizations,
6. total messages and every message category,
7. communication reduction versus matched Phase 2,
8. monitoring correctness outcomes and any missed/late global events.

Interpretation:
1. alpha=0.10 is a baseline, not a claimed optimum.
2. The preferred alpha may be identified empirically only after viewing the complete sensitivity results.
3. If the response is irregular or the minimum occurs between coarse-grid values, a secondary 0.01-step refinement may be added around the promising region.

### 10.3 Phase 3 Membership Ablation
For each selected FMIC/SMIC configuration, compare:
1. fixed membership with no membership-triggered synchronization/re-clustering, and
2. dynamic membership with the explicit departure/return policy enabled.

Report the incremental communication attributable to membership management separately from communication attributable to clustering.

---

## 11) Deliverables

### Code And Execution
1. scripts/build_phase1_temperature.py (existing).
2. scripts/build_phase2_temperature_sensors.ipynb (required baseline implementation).
3. Phase 3 FMIC implementation artifact (notebook/script; final filename must be recorded here when created).
4. Phase 3 SMIC implementation artifact (may share a notebook with FMIC only if algorithm-specific validation and outputs remain separately auditable).
5. Synthetic correctness/unit-test artifact for Phase 2/FMIC/SMIC logic.

### Data Artifacts
1. artifacts/aligned_phase1_temperature.csv.
2. artifacts/phase1_average_statistics.csv.
3. artifacts/phase2_temperature_sensors.csv.
4. artifacts/phase2_temperature_metrics.json.
5. Phase 3 row/cluster trace artifacts sufficient to reproduce cluster assignments, node/coordinator/root events, and message counts.
6. Phase 3 alpha sensitivity summary for FMIC and SMIC.
7. Phase 3 fixed-vs-dynamic membership ablation summary.
8. Phase 3 synthetic correctness test results.

### Documentation
1. Updated project plan.
2. Updated run instructions.
3. Metrics interpretation notes and limitations.
4. Phase 3 source-alignment notes referencing `140516editor Book Chapter (Last Version).pdf`, Section 1.4 / Algorithms 1.4.1–1.4.2 and the moment/broadcast-count appendices, documenting any deviations.
5. Test-case results showing correctness before communication-savings claims.

---

## 12) Major Risks And Mitigations

1. Risk: trigger boundary too conservative or too sensitive.  
Mitigation: use required sensitivity reruns and compare communication versus missed windows.

2. Risk: drift from the definitive chapter's methodology in implementation shortcuts.  
Mitigation: keep the definitive chapter's precedence explicit and include formula-level verification checks for local deviation and synchronization state.

3. Risk: missing global average values at re-sync minutes.  
Mitigation: preserve undefined global state when no valid readings exist; never fill missing temperatures or classify an undefined mean as safe. Compare only under matched observed-only availability/denominator policies.

4. Risk: confusion between deterministic rules and predictive modeling terminology.  
Mitigation: keep language explicit that metrics are diagnostics on rule behavior.

5. Risk: implementation drift between notebook and plan.  
Mitigation: enforce schema, formula, and communication-reconciliation checks in the verification checklist.

6. Risk: treating alpha=0.10 as an established optimum.  
Mitigation: label it as a baseline design choice and run the required 0.05–0.95 sensitivity sweep for FMIC and SMIC.

7. Risk: attributing communication changes to clustering when they are caused by departure/return synchronization or re-clustering.  
Mitigation: use fixed-membership as the primary clustering-effect condition and report dynamic-membership costs as a separate ablation.

8. Risk: signed cancellation hides a true global threshold violation.  
Mitigation: require synthetic cancellation tests and matched reference calculations before accepting any communication savings.

9. Risk: stale history/reference state after missing readings or sensor return.  
Mitigation: never inject zero change for missing data; require explicit re-entry synchronization before history resumes in the dynamic-membership condition.

10. Risk: incorrect reproduction of the source clustering method.  
Mitigation: add hand-calculated tests for history discounting, normalization, partition quality, greedy merge selection, FMIC/SMIC weights, node allowances, and coordinator allowances.

11. Risk: communication savings are overstated through incomplete counting.  
Mitigation: count actual requests, responses, broadcasts, cluster checks, and root escalations, and attribute membership/coordinator events without double-counting bundled updates. Count requests sent to offline sensors without inferring responses; require exact reconciliation to total messages.

---

## 13) Ready-For-Build Checklist

### Phase 2 Ready / Validated
1. Phase 1 artifacts exist and pass quality checks.
2. Phase 2 notebook exists and runs end-to-end.
3. phase2_temperature_sensors.csv is produced with required fields.
4. Metrics JSON is produced with communication and diagnostics.
5. Phase 2 targeted correctness tests are documented and pass before Phase 3 performance claims are made.

### Phase 3 Ready
1. Source equations/algorithm steps for history, partition quality, Algorithm 1.4.1 merging, FMIC/SMIC weights, and coordinator constraints have direct implementation tests.
2. Fixed-membership assumptions are documented and matched to the Phase 2 comparator.
3. Dynamic-membership departure/return rules are documented as a separate policy.
4. Communication categories and counting rules are locked before running experiments.
5. FMIC is validated before SMIC comparison.
6. SMIC is independently validated before the full comparison.
7. Required alpha sensitivity runs are complete before a preferred alpha is selected.
8. Synthetic cancellation, offline/return, boundary, escalation, and hand-counted communication tests pass.
9. Multivariate extension remains deferred until the temperature-only clustering results are validated and interpreted.
10. The event-based lifecycle and highest-ID coordinator story, US-3.15 in the [Phase 3 user stories](Phase_3_User_Stories.md), passes its acceptance tests.
11. The agreed observed-only denominator, undefined-state, retained-history, and bundled-message rules are implemented and tested against matched comparators.
