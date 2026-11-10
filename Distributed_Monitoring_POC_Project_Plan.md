# Distributed Monitoring POC Project Plan

Revision focus (2026-11-03): sponsor-approved Phase 3A stable-cohort pivot, matched Phase 2/FMIC/SMIC comparison, cohort-specific thresholding, compact reproducible outputs, and optional Phase 3B availability robustness. **Synchronization update through US-3.22:** Sections 2, 4, 6–11, 13, and 14 reflect the implementation decisions and validation results recorded in the Pivot Plan.

**Policy update (2026-11-10, US-3.23):** Phase 2 now uses two-sided absolute distance and equal allowances. The revised matched baseline is separately named; all US-3.22 figures and denominators remain historical and unchanged. See Section 14.4. No FMIC/SMIC code, weighting, clustering, or protocol was changed.

## 1) How To Read This Plan

This document has two layers:
1. Discussion view for stakeholder alignment.
2. Implementation view with deterministic rules that can be coded directly.

The sponsor-approved `Phase_3A_Pivot_Plan.md` is incorporated into this plan, with implementation and validation decisions through US-3.22 synchronized as of 2026-11-03. For Phase 3A, the provisions below supersede earlier plan language that required changing observed contributors, re-entry handling, or availability-triggered synchronization as part of the primary FMIC/SMIC experiment.

Primary project sequence:
1. Phase 1 transformation creates the full aligned temperature snapshots and Phase 1 statistics.
2. Phase 2 deterministic monitoring remains the validated non-clustered implementation. The existing full-data run remains historical project evidence.
3. Phase 3A selects a sponsor-approved stable six-sensor cohort and interval from the Phase 1 aligned output, adds a cohort-specific p90 statistics row, and reruns the existing Phase 2 engine on that exact experimental population to create the matched baseline.
4. Phase 3A has implemented and reviewed FMIC and SMIC at `alpha=0.10` on the same cohort, interval, threshold, observations, boundary convention, and communication-counting rules. The two methods independently determine their own synchronization events; they are not required to share Phase 2 synchronization timestamps. The US-3.21 synthetic validation gate and US-3.22 full alpha comparison are complete.
5. Phase 3B is an optional later robustness extension for the broader dataset with changing sensor availability. It is not on the Phase 3A critical path.
6. Multivariate extension remains deferred until the temperature-only clustering experiment is validated and interpreted.

---

## 2) Conflict Resolution And Locked Decisions

Precedence rule for this repository:
1. The definitive methodology source is `140516editor Book Chapter (Last Version).pdf`, *Clustering for Monitoring Distributed Data Streams*. If this plan or another summary conflicts with the chapter on history, normalization, clustering mathematics, FMIC/SMIC calculations, or source-comparable broadcast accounting, the chapter takes precedence **for those source-defined methods**. Explicitly labeled project adaptations (separate root, exact threshold boundary, transmission accounting, and all-zero-weight fallback) govern this project’s experimental implementation and must not be presented as formulas supplied by the chapter.
2. `Phase_3A_Pivot_Plan.md` records the sponsor-approved experimental redesign for Phase 3A and is incorporated into this plan. It governs the Phase 3A experimental population and simplification decisions.
3. Section 1.4 and Algorithms 1.4.1–1.4.2 of the definitive chapter define the clustering/monitoring method; the chapter appendices define moment calculations and source-comparable broadcast accounting.
4. Existing Phase 3 user stories remain historical implementation records. New user stories added after the existing sequence will implement the Phase 3A pivot and explicitly supersede conflicting prior requirements for the Phase 3A path.

### 2.1 Scope Changes From Prior Version
1. Phase 1 remains the full temperature transformation core; its calculation and aggregation logic is unchanged. Source-file discovery was corrected to exclude the aggregate `temperature_raw.csv` from raw inputs (documented in §8.1).
2. Phase 2 remains the deterministic non-clustered monitoring implementation. The existing full-data Phase 2 run is preserved as a historical artifact.
3. The primary clustering experiment is now **Phase 3A**, a stable-cohort experiment using six continuously observed sensors over a locked interval.
4. The previous Phase 3 requirement to model departures, returns, changing observed contributors, re-entry synchronization, changing denominators, and availability-driven coordinator changes is removed from the Phase 3A critical path.
5. Those availability-aware requirements are reserved for optional **Phase 3B** robustness work.
6. Phase 3A production outputs are intentionally compact. Detailed deterministic intermediate states are validated through tests or optional debug traces rather than persisted for every row and alpha.
7. Alpha is treated as a dataset-specific tuning parameter rather than a primary research question.
8. Multivariate monitoring remains a possible later extension after FMIC/SMIC validation; it must not be mixed into the Phase 3A experiment.

### 2.2 Locked Decisions
1. Required Phase 2 primary input remains `artifacts/aligned_phase1_temperature.csv`.
2. The existing full-data Phase 2 run may continue to use its existing Phase 1 threshold source for historical comparability.
3. Phase 3A uses sensors **A, C, D, E, F, and G** only.
4. Phase 3A uses the continuous UTC interval from **2022-02-24T18:50:00+00:00** through **2022-03-10T15:53:00+00:00**, inclusive, with **19,984 one-minute buckets**. Both endpoints are inclusive, so the interval spans 19,983 elapsed minutes.
5. Every selected sensor must have a valid observation in every Phase 3A bucket. No sensor-value imputation is permitted. If cohort, interval, row count, or completeness validation fails, Phase 3A stops rather than falling back to dynamic availability handling.
6. `phase1_average_statistics.csv` retains the existing statistics and includes the `phase3a_stable_cohort` row computed from the six-sensor mean over the locked interval.
7. The Phase 3A p90 is calculated programmatically from the approved experimental population. The recorded full-precision result is **22.428666649999997 °C**; the production statistics row, not a hard-coded number in the monitoring logic, remains authoritative.
8. The current Phase 2 monitoring code is reused rather than rewritten. A matched Phase 3A Phase 2 run is created by filtering to the approved cohort/interval and using the Phase 3A p90.
9. Membership-change behavior must never activate in the matched Phase 3A Phase 2 run. If it does, the input/filtering logic is incorrect.
10. The primary Phase 3A comparison is **stable-cohort Phase 2 vs. stable-cohort FMIC vs. stable-cohort SMIC** under identical observations, timestamps, threshold, boundary convention, and communication-counting definitions. **Each algorithm determines its own synchronization timing;** matched inputs do not imply matching synchronization events.
11. The local deviation definition remains `delta_v_i(t) = v_i(t) - v_i(t0_i)`, where `t0_i` is the most recent synchronization reference for sensor i.
12. The canonical boundary convention remains safe when metric `<` boundary and violated when metric `>=` boundary. Logic uses unrounded values.
13. Source-aligned history remains persistent across resynchronizations and uses signed change relative to the active synchronization reference, not prior-minute change.
14. Phase 3A normalization uses the same six sensors at every clustering event. For scalar history, `H = max_i |h_i|`; when `H > 0`, `a_i = h_i / H`, preserving sign and raw history.
15. The initial all-zero-history case remains a valid deterministic edge case and uses the previously agreed singleton fallback.
16. Cluster quality, partition quality, signed cancellation, greedy merging, stopping behavior, and final partition selection remain source-aligned and are not simplified away.
17. Phase 3A removes runtime logic used only for changing availability: departures, returns/re-entry, changing eligible sets, offline history suspension, changing denominators, membership-triggered synchronization, membership cause attribution, availability-driven coordinator changes, zero-observation states, and deferred synchronization waiting for return.
18. Detailed availability-aware logic may be retained for optional Phase 3B, but it must not complicate the primary Phase 3A execution path.
19. Full sensor-by-minute history traces and exhaustive clustering-search audits are not normal Phase 3A deliverables.
20. Phase 3A retains compact event-level state sufficient to understand and reproduce clustering results: event/synchronization ID, timestamp, algorithm, alpha, raw histories, normalized histories, selected partition, selected partition quality, cluster count, and coordinator assignments.
21. Detailed traces may be generated only through explicit debug/test modes or small samples.
22. FMIC was implemented and reviewed end-to-end in US-3.19 before SMIC was implemented and reviewed in US-3.20. Their production reports show passing correctness at `alpha=0.10`; the US-3.21 synthetic formula, protocol, correctness, and communication-accounting validation gate has also passed.
23. FMIC and SMIC share one monitoring architecture; their main algorithm-specific difference is the source-defined weighting/allowance calculation.
24. Initial correctness work may use `alpha=0.10` as a baseline implementation value only.
25. After US-3.21 comprehensive validation passes, **US-3.22 requires** a 19-value alpha sweep (`0.05, 0.10, ..., 0.95`) for **each** of FMIC and SMIC, for 38 clustered runs. Alpha remains dataset-specific; a lowest-message setting is not a universal optimum or central research finding.
26. Phase 3A uses six sensors plus a **separate root component**. Coordinators are sensor members; communication with oneself costs zero. A request and its response are separate transmissions. Actual transmissions are counted by category and reconcile exactly; chapter-style broadcast estimates, if shown, are labeled separately and are not substituted for actual totals. Membership categories are not required because membership is fixed.
27. Correctness is demonstrated primarily with focused synthetic and hand-calculated tests rather than by retaining every deterministic full-run intermediate state.
28. Reproducibility means that the original aligned data, experiment configuration, threshold statistics row, implementation code/notebook, deterministic algorithms, focused tests, and compact results are sufficient to reproduce the reported experiment.
29. Phase 3B is optional. Phase 3A must be completed and interpreted before any Phase 3B work is considered required.
30. Existing Phase 3 user stories are not rewritten retroactively; new pivot stories govern the Phase 3A implementation where they conflict with prior availability-heavy requirements.

---

## 3) Executive Summary (Discussion View)

### What This Experiment Is Proving
The project tests two linked questions:
1. whether deterministic distributed monitoring can reduce communication relative to centralized all-sensor-every-minute messaging while preserving correct global-threshold monitoring; and
2. whether source-aligned FMIC/SMIC clustering can further reduce communication relative to a matched Phase 2 baseline through signed cancellation.

For Phase 3A, the experiment deliberately removes changing sensor availability as a confounder. The selected six sensors are continuously observed for the full approved interval, so communication differences can be interpreted primarily as algorithm differences rather than availability-management effects.

### Why This Design Is Deterministic
The workflow does not train a predictive model. It applies fixed rules over aligned minute-bucket data:
1. a locked experimental cohort and interval;
2. a programmatically derived Phase 3A p90 threshold from that experimental population;
3. fixed history, clustering, allowance, boundary, synchronization, and message-counting rules;
4. shared implementation logic for FMIC and SMIC except where the source defines different weight/allowance calculations.

### What Success Looks Like
1. The Phase 3A input contract passes: six approved sensors, approved inclusive interval, 19,984 buckets, exact 60-second timestamp spacing, and no missing selected-sensor readings.
2. The cohort-specific p90 is reproducibly calculated and recorded in Phase 1 statistics.
3. A matched Phase 2 baseline is produced from the same experimental population.
4. Source-aligned history, normalization, clustering, FMIC, and SMIC formulas pass focused synthetic and hand-calculated tests.
5. No correctness test shows a global threshold violation concealed by cluster cancellation.
6. Communication categories reconcile exactly to total messages.
7. Phase 3A production artifacts remain small enough to inspect and manage directly.
8. The final Phase 2/FMIC/SMIC comparison is understandable without reconstructing gigabytes of intermediate state.
9. Phase 3B availability robustness is treated as optional follow-on work rather than a prerequisite for the core result.

---

## 4) Experiment Scope And Phases

### Phase 0 - Setup And Lock Assumptions
Objective: freeze definitions, source precedence, metrics, and state-machine semantics.

### Phase 1 - Temperature Transformation Core
Objective: transform raw telemetry into aligned minute snapshots with quality metadata.

Primary outputs:
- `artifacts/aligned_phase1_temperature.csv`
- `artifacts/phase1_average_statistics.csv`

Phase 1 transformation logic remains unchanged. A Phase 3A-specific statistics row is added downstream from the aligned output for the approved six-sensor interval.

### Phase 2 - Deterministic Temperature Sensor Monitoring
Objective: execute deterministic local-deviation monitoring and re-sync logic on aligned snapshots.

Two Phase 2 results are distinguished:
1. **Existing full-data Phase 2 result:** retained as historical evidence of the availability-aware implementation.
2. **Matched Phase 3A Phase 2 baseline:** rerun the existing Phase 2 engine on the six approved sensors and locked 19,984-bucket continuous interval using the Phase 3A-specific p90. This is the comparator used for FMIC/SMIC.

### Phase 3A - Stable-Cohort Temperature Clustering Extension (Required; US-3.16–3.22 Implemented)
Objective: determine whether source-aligned FMIC and SMIC clustering reduce communication beyond the matched stable-cohort Phase 2 baseline while preserving monitoring correctness.

Required sequence:
1. Validate the Phase 3A input contract and derive the Phase 3A p90.
2. Produce the matched stable-cohort Phase 2 baseline.
3. Simplify the existing Phase 3 implementation by removing availability-only branches and oversized production traces from the Phase 3A path.
4. Preserve and revalidate source-aligned history, normalization, partition quality, and greedy clustering already implemented.
5. Implement FMIC end-to-end using one baseline alpha and validate it.
6. Implement SMIC through the same monitoring architecture and validate it independently.
7. Run compact alpha tuning only after both algorithms operate correctly end-to-end.
8. Produce the final matched Phase 2 vs. FMIC vs. SMIC comparison.

**Phase 3A status at this update:** US-3.16–3.18 established the simplified six-sensor pipeline, locked inputs, authoritative p90, and matched Phase 2 baseline. US-3.19 implemented FMIC and US-3.20 added SMIC in the same monitoring engine. US-3.21 passed the synthetic validation gate, then US-3.22 completed 38 full-length runs, all correctness-passing with reconciled messages. See §14 for results and artifact names.

### Phase 3B - Availability Robustness Extension (Optional)
Objective: if time and sponsor interest permit, evaluate the broader dataset with sensor departure/return, changing observed contributors, re-entry handling, changing coordinators, and availability-related communication attribution.

Phase 3B is not required for Phase 3A completion and must not delay FMIC/SMIC implementation for the stable cohort.

### Phase 4 - Validation And Packaging
Objective: consolidate compact metrics, selected cluster-event records, tuning results, correctness evidence, limitations, and stakeholder-ready outputs.

Interpretation rule: the initial clustering experiment remains temperature-only. Multivariate monitoring is deferred so that clustering effects are not confounded with a simultaneous change in dimensionality.

---

## 5) Phase 2 Monitoring Logic (Discussion View)

Per minute bucket:
1. Determine the online set from valid Phase 1 observations and compare it to the preceding bucket; availability detection costs no messages.
2. Compute the mean from current online readings, or record undefined global state when there are none.
3. Initialization and membership changes, including deferred causes, force synchronization and skip operational local-trigger evaluation.
4. Otherwise evaluate `abs(delta_v_i(t)) >= abs(threshold - synchronized_mean)` using entry references and equal allowances; any local trigger causes one synchronization.
5. Combine coinciding causes into at most one synchronization per bucket, preserving all causes with initialization then membership precedence.
6. A completed synchronization contacts only online sensors, counting N requests, N responses, and N threshold updates. Local-trigger messages are counted only when actually generated.
7. When all sensors are offline, send nothing, retain pending causes, and wait for observations to return; do not reuse a prior mean as the current observation.
8. Apply synchronized references/allowances starting next row. Retain the last verified root-known SAFE/VIOLATED state between synchronizations; being above threshold does not schedule another synchronization.

Consistency note:
1. Phase 2 uses local constraints as an operational sufficient-condition proxy for the DDS aggregate deviation bound.
2. The canonical production policy uses the fixed boundary convention defined in locked decisions.

Interpretation:
1. False alarms are acceptable trade-offs for safer coverage.
2. Communication naturally clusters near high-temperature periods.
3. Root-known-state correctness is checked against an independent offline oracle; same-minute synchronization-versus-violation metrics are separately labeled legacy diagnostics.

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
1. The existing full-data Phase 2 run retains its historical threshold provenance.
2. For Phase 3A, filter `aligned_phase1_temperature.csv` to sensors A, C, D, E, F, and G over the locked interval.
3. Compute the six-sensor average for every one of the 19,984 complete, consecutive one-minute buckets.
4. Compute the Phase 3A p90 programmatically from that experimental series.
5. Add a clearly identified row such as `phase3a_stable_cohort` to `phase1_average_statistics.csv`; preserve all existing Phase 1 statistics rows.
6. The planning estimate is approximately `22.42866665`, but the run must use the computed full-precision value rather than a hard-coded approximation.
7. The matched Phase 2, FMIC, and SMIC runs must all read the same Phase 3A p90 from the statistics artifact.

### 6.3 State Initialization
1. Start with undefined global/per-sensor references and margins, no prior membership set, and initialization pending.
2. The first bucket's observed set establishes initial membership without fabricating departure/return events.
3. Leading buckets without readings remain undefined, pending, and message-free. Never borrow values from a later row.
4. At the first usable bucket, complete initialization: synchronize the observed mean and online per-sensor readings, with equal local allowances `abs(p90 - synchronized_mean)` and a verified root-known state (SAFE below p90, VIOLATED at or above).
5. Count N requests, N responses, and N threshold updates for the N online sensors, with zero local triggers. Record `event_initialization_performed` and `initialization_message_count`.
6. Newly synchronized references and margins become next-row entry state. Sensors absent from synchronization have undefined references/margins; returning sensors force synchronization before local evaluation.

### 6.4 Per-Row Deterministic State Machine
For each row t:
1. Read prior committed state into `entry_*`; determine current online sensors, departures, and returns from valid observations after Phase 1 freshness filtering.
2. Add membership changes and initialization to pending synchronization causes. A departure is the first missing bucket and a return is the first subsequent valid bucket.
3. If any forced cause is present, suppress operational local triggers and keep trigger bits/messages zero, but calculate local deviations and constraint comparisons against valid entry references for reporting. Complete synchronization only if at least one sensor is online; otherwise retain pending causes without traffic.
4. Without forced causes, compute signed deviations from entry references and trigger when `abs(deviation) >= allowance`. All triggering sensors produce their trigger messages and one synchronization.
5. At synchronization, set the exit global reference to the current observed mean, set online references/margins from current observations, and invalidate references/margins for excluded sensors.
6. Count request/response/update fanout using the online count, not the configured cohort size. All membership status detection is free.
7. Record all causes, primary reason, completed/pending status, and membership changes. Causes sharing one synchronization do not create duplicate traffic.
8. The actual label is `observed_global_average >= p90` for evaluable rows, otherwise undefined. Diagnostic predicted positive remains `event_resync_performed`, not a claim of threshold violation.
9. Carry new references/allowances into row t+1 without negative-margin scheduling. Zero allowance still triggers conservatively with `>=`, including unchanged readings in the next bucket. Root-known state is updated after this bucket's completed synchronization; the offline oracle never controls communication.

### 6.5 Row Invariants
For each exported row:
1. `entry_*` fields are the state used to evaluate the current row.
2. `observed_*` fields are the raw values for the current minute bucket.
3. `event_*` fields record outcomes produced during the current minute.
4. `exit_*` fields describe the state committed at the end of the row and carried into the next row.
5. `transition_summary` is an early-row audit field summarizing the row's event and exit-state transitions.
6. `distributed_constraint_state` is `VIOLATING` if any absolute observed sensor deviation meets/exceeds its entry local allowance, including reporting-only comparisons on forced rows. `FEASIBLE` requires complete comparison coverage with no violation; incomplete coverage is `NOT_EVALUABLE`, and no observations is `UNDEFINED`.
7. `centralized_constraint_state` remains the observed global p90 oracle; `event_resync_performed` records the independent operational synchronization action. The redundant `distributed_alert` alias is removed.
8. The existing module independently replays reference state from unrounded inputs to validate the full trace before rounding and after CSV export. Exact boundary decisions use original inputs; numeric CSV comparisons use four-decimal tolerance. Violations identify the bucket and field.

### 6.6 Required Phase 2 Output Schema
The general revised notebook writes `artifacts/phase2_two_sided_temperature_sensors.csv`; historical `phase2_temperature_sensors.csv` is preserved. The revised trace includes:
1. bucket_epoch, bucket_time_utc.
2. early audit fields: transition_summary, p90_threshold_used.
3. row-level global timing fields: observed_global_average, entry_xbar_t0, entry_root_allowance; exit global state is represented by the adjacent optional resync-result fields.
4. optional resync-result fields: exit_xbar_t0_if_resync, exit_root_allowance_if_resync. Allowance fields explicitly replace signed-delta fields with nonnegative absolute-distance semantics.
5. per-sensor current value, synchronized entry reference value, event-local deviation, and entry local allowance fields.
6. one binary event-local trigger/re-sync-request flag per sensor (for example event_A_resync_requested).
7. event_triggering_sensor_names, event_resync_request_count, event_any_sensor_requested_resync.
8. re-sync execution and scheduling fields: event_resync_performed, event_initialization_performed, event_resync_triggered_by_membership_change, exit_resync_scheduled_next_row, exit_resync_pending, exit_resync_pending_causes. Consumption/local-cause helper bits remain internal; event_resync_causes preserves their meaning in the public trace.
9. synchronization reasons: initialization, sensor_membership_changed, local_constraint_violation. Negative-margin causes and diagnostic/control fields are removed.
10. communication event fields: trigger_message_count, request_message_count, response_message_count, broadcast_message_count, total_message_count.
11. membership/evaluability fields: observed_online_sensor_names, observed_online_sensor_count, event_departing_sensor_names, event_returning_sensor_names, event_membership_changed, global_state_evaluable.
12. cause-attribution fields: membership_resync_message_count and initialization_message_count. These may overlap and must not be added to transmission-type totals.
13. root-state fields: root_known_state, oracle_global_state, false_safe, false_violated, root_state_not_evaluable; policy identifier threshold_policy. Local/centralized constraint fields remain separate. Legacy event diagnostics are explicitly renamed legacy_event_false_negative, legacy_event_false_alert, and legacy_event_sync_delay_buckets; distributed_alert is not exported.

Implementation precedence rule for `event_resync_reason` when more than one cause is possible in the same row:
1. `initialization`
2. `sensor_membership_changed`
3. `local_constraint_violation`

Record every cause in `event_resync_causes`, including deferred membership events. Forced synchronization rows suppress local triggers. The legacy conditional `sensor_recovered_after_offline` path is replaced by detection of every departure/return.

### 6.7 Phase 2 Implementation Artifact
Required implementation artifact:
1. scripts/build_phase2_temperature_sensors.ipynb.
2. scripts/phase2_monitoring.py, the state machine used by the notebook and synthetic tests.
3. scripts/test_phase2_monitoring.py, run with `python -m unittest scripts.test_phase2_monitoring -v`.

This is the existing general Phase 2 monitoring engine, updated by US-3.23 without removing its availability-aware behavior. Run `python -B -m scripts.phase2_monitoring` for the separately named revised matched baseline; it filters and validates the locked six-sensor cohort and interval and reads the Phase 3A-specific p90. No separate Phase 2 implementation or alternate monitoring state machine is required.

Notebook sections (cells):
1. Load input artifacts and constants.
2. Derive p90 and discover sensor columns.
3. Execute deterministic row-wise state machine.
4. Export separately named phase2_two_sided_temperature_sensors.csv.
5. Compute and export diagnostics summary.

### 6.8 Phase 3A Experiment Input Contract
Phase 3A uses the temperature streams as scalar node streams and preserves the same global temperature-threshold objective used by the matched Phase 2 run.

Before any Phase 3A monitoring or clustering occurs, validate:
1. selected sensors are exactly A, C, D, E, F, and G;
2. first bucket is `2022-02-24T18:50:00+00:00`;
3. last bucket is `2022-03-10T15:53:00+00:00`;
4. row count is exactly 19,984;
5. every selected sensor has a valid finite temperature in every bucket;
6. timestamps are unique, strictly increasing, and every adjacent timestamp differs by exactly 60 seconds;
7. the Phase 3A p90 statistics row exists and was computed from this same cohort and interval.

Failure of any input-contract check stops the Phase 3A run. The implementation must not switch to dynamic availability handling as a fallback.

### 6.9 Phase 3A Source-Aligned Clustering Specification
Source-alignment checkpoints:
1. History initializes at zero and updates for each valid observation after the reference row using `h_i <- 0.5 * h_i + (v_i(t) - v_i(t_j))`. The synchronization-reference row does not create an artificial zero-deviation history update.
2. History uses signed change from the active synchronization reference, never prior-minute change.
3. On a synchronization row, update history against the reference active on row entry, use the resulting history for clustering, and then install the new reference for subsequent rows.
4. Histories persist across synchronization and are not reset.
5. Every Phase 3A clustering event contains the same six sensors. No online/offline eligibility logic is required in the primary path.
6. For scalar histories, normalize with `H = max_i |h_i|`; when `H > 0`, use `a_i = h_i / H`, preserving sign and leaving raw history unchanged.
7. If all six histories are zero, use the previously agreed singleton no-information fallback and mark it explicitly.
8. Cluster quality is `q(pi) = (1 / |pi|) * |sum(a_i)| + alpha * |pi|`; partition quality is `Q(Pi) = max q(pi)`.
9. Signed normalized histories are summed before the absolute value so cancellation remains possible.
10. Algorithm 1.4.1 remains the governing greedy procedure: begin with singleton clusters, select the current worst-quality cluster, merge with the partner producing minimum merged-cluster quality, retain candidate partitions, stop at two clusters for `n >= 2`, and choose the retained partition with minimum `Q`.
11. Existing deterministic project tie rules may remain unless a simpler source-consistent rule is explicitly approved later.
12. FMIC uses the absolute **first moment** of each sensor's post-initialization temperature readings: `W_i = |mu_i|`. The first moment is computed from the persistent discounted sum `S_i(m) = 0.5 * S_i(m-1) + v_i(m)` and `mu_i(m) = S_i(m) / m`, for `m >= 1`. The first synchronization row initializes references and is not counted as a post-initialization moment update. This moment state is distinct from the signed history used for clustering.
13. SMIC uses the source's conservative **second-moment** contribution: `W_i = |mu_i| + sqrt(((m-1)/m) * S2_i)`. Here `S2_i` is the **unnormalized** sum of squared deviations among the discounted observations, not sample or population variance. The implemented recurrence is `S2_i(m) = 0.25 * S2_i(m-1) + ((m-1)/m) * (v_i(m) - 0.5 * mu_i(m-1))^2` for `m >= 2`, with zero second moment after the first post-initialization reading. The source definition and recurrence are documented in Chapter §1.4 and Appendix 1 (printed pp. 22 and 24).
14. For six sensors, let `W = sum_i W_i`. When `W > 0`, normalized weight `w_i = 6 * W_i / W`, so `sum_i w_i = 6`. The node allowance is `delta(i) = w_i * delta(root)`; a cluster coordinator's allowance is the arithmetic mean of its member-node allowances. If **all** weights are zero, use `w_i = 1` for every sensor. This equal-weight fallback is an **explicit project policy**, not a claimed chapter formula. An individually zero-weight sensor retains zero weight when the total is positive.
15. Keep the first and second moments persistent across ordinary root synchronization; changing the sensor reference does not reset either moment. Formula-level tests must verify discounted moments, history, normalization, clustering, weights, node/coordinator allowances, and zero-weight behavior against hand calculations.

### 6.10 Phase 3A Monitoring Lifecycle And Simplification
1. Phase 3A has a fixed six-sensor cohort and complete observations on every row. Departure, return, changing eligible sets, zero-observation state, changing observed denominator, and membership-triggered synchronization do not exist in the primary execution path.
2. Re-clustering remains event-based: initialize at the first completed synchronization and re-cluster at later completed resynchronizations according to the monitoring algorithm, not on a timer.
3. Resulting partitions, coordinators, references, and allowances become active using the agreed next-row state timing.
4. Each cluster uses the existing deterministic coordinator-selection rule unless a later pivot story explicitly changes it. A singleton coordinates itself.
5. Cluster/coordinator information may travel with normal synchronization threshold updates; no duplicate standalone formation traffic is created unless the implementation actually transmits it.
6. Each completed root synchronization records the six-sensor global mean and its **root-known state**: safe if `mean < p90`, violated if `mean >= p90`. The root allowance is `abs(global_mean_at_sync - p90)`, so it is never negative. Equality with p90 is **violated** and gives zero allowance.
7. FMIC and SMIC use **two-sided threshold monitoring**. Their local and coordinator checks must ensure that a change from the last root-known safe/violated state cannot be missed. Node-level violations remain observable even if signed cluster cancellation makes a root check unnecessary. An already-violated mean does not by itself cause forced synchronization; do **not** import historical Phase 2's negative-margin forced-resynchronization rule (removed from Phase 2 by US-3.23).
8. If a coordinator check cannot establish that the root-known state remains valid, it escalates to the separate root component. A completed root synchronization recalculates the actual mean, records the state, recomputes moment-based allowances, and refreshes references and clusters for the next bucket. Cluster checks and root collections follow the shared FMIC/SMIC engine, but **their event times may differ** from Phase 2 and from each other.
9. The true global mean computed from all six readings is available for **offline evaluation only**, not for deciding whether online communication is triggered. Both false-safe and false-violated counts must be zero for the run to be marked `passed`; the correctness comparison is with the actual six-sensor threshold state, **not the Phase 2 synchronization schedule**.
10. Availability-aware branches already built may be retained for optional Phase 3B, but Phase 3A code should remove or isolate them so they do not complicate the primary path.

### 6.11 Phase 3A Production Output And Reproducibility
Normal Phase 3A output is compact and event-oriented.

Do not persist by default:
1. one sensor-history row per sensor per minute;
2. every rejected merge candidate;
3. every merge-partner score;
4. every intermediate partition and cluster quality for every synchronization and alpha;
5. exhaustive nested JSON for deterministic search paths;
6. availability fields that cannot occur in Phase 3A.

At clustering events, retain at minimum:
1. event/synchronization identifier;
2. timestamp;
3. algorithm;
4. alpha;
5. raw histories used for clustering;
6. normalized histories;
7. selected partition;
8. selected partition quality;
9. cluster count;
10. coordinator assignments.

A detailed debug mode may emit deeper traces for synthetic cases or small samples, but it is off by default for full-data runs.

Reproducibility is satisfied when a researcher can regenerate the reported results from the original aligned input, experiment configuration, Phase 3A threshold row, implementation code/notebook, deterministic algorithms, focused tests, and compact output artifacts. Persisting every deterministic intermediate state is not required.

### 6.12 Phase 3A FMIC/SMIC Build Strategy
1. Implement FMIC first as the first complete Phase 3A clustering-monitoring algorithm.
2. Validate FMIC formula outputs and end-to-end behavior before SMIC results are interpreted.
3. Add SMIC through the same monitoring engine. Do not create a second monitoring architecture.
4. Shared behavior includes observations, history, normalization, clustering rules, synchronization **protocol and next-row timing convention** (but not necessarily identical synchronization event timestamps), coordinator behavior, communication counting, outputs, and common correctness tests.
5. The principal algorithm-specific difference is the source-defined weight/allowance calculation.

### 6.13 Phase 3A Alpha Policy
1. Alpha is a dataset-specific tuning parameter, not the primary research question.
2. Use `alpha=0.10` as an initial implementation value only.
3. Do not run the full alpha grid until **US-3.21 comprehensive synthetic validation** passes for FMIC and SMIC.
4. **US-3.22 requires** the 19-value grid `0.05, 0.10, ..., 0.95` for both algorithms (38 runs) and a matched final Phase 2/FMIC/SMIC comparison.
5. Retain one compact result row per algorithm/alpha with `algorithm`, `alpha`, total and category-level messages, correctness in both directions, root synchronizations, and summary cluster metrics. Keep the `alpha=0.10` result as the fixed initial benchmark; run details are not a replacement for independent validation.
6. Do not persist the full internal merge-search path for every alpha.
7. Select or discuss a preferred alpha only among configurations that pass correctness tests.
8. Do not present the selected alpha as a universal optimum.

### 6.14 Phase 3A Synthetic Correctness Test Suite
The Phase 3A suite must document the setup, expected result, and failure interpretation for each case.

1. **History recurrence test:** hand-calculate history across multiple observations and synchronization intervals. Confirms signed deviation from the active reference, 0.5 discounting, persistence across synchronization, and reference replacement.
2. **Normalization test:** use positive, negative, zero, tied-maximum, and all-zero histories. Confirms signed scaling, raw-state preservation, and deterministic zero-history fallback.
3. **Clustering test:** hand-calculate `q`, `Q`, worst-cluster choice, partner choice, merge sequence, retained partitions, and final selected partition for a small sensor set.
4. **FMIC weight/allowance test:** hand-calculate first-moment weights, node allowances, and coordinator allowance.
5. **SMIC weight/allowance test:** hand-calculate first moment, second moment, conservative second-moment component, node allowances, and coordinator allowance.
6. **Safe cancellation test:** one node warms and another cools enough for the monitored global condition to remain safe. Local activity remains observable while unnecessary root escalation may be avoided.
7. **Unsafe partial-cancellation test:** cooling is insufficient; coordinator/root escalation must occur and a true global violation cannot be concealed.
8. **Boundary test:** values just below, exactly at, and just above every relevant node, coordinator, and global boundary follow the declared `<` versus `>=` convention.
9. **Communication accounting test:** a hand-counted 2–4 sensor example reproduces every trigger, request, response, coordinator escalation, synchronization request/response, and broadcast exactly.
10. Availability/offline tests are not Phase 3A gates. They may be retained for optional Phase 3B.

### 6.15 Phase 3B Optional Availability Robustness
Phase 3B may later exercise the broader availability-aware design using the full dataset. Candidate scope includes sensor departure/return, changing observed contributors, re-entry synchronization, retained history through outages, changing coordinators, zero-observation states, and availability-related traffic attribution.

No Phase 3B implementation, test, or output is required for Phase 3A completion. Existing availability-aware code and historical user stories may be reused if Phase 3B is approved later.

## 7) Metrics And Evaluation

### 7.1 Phase 2 Historical Metrics
Existing Phase 2 diagnostic definitions remain valid for the historical full-data run. Synchronization-based precision/recall remain operational diagnostics rather than measures of actual warning accuracy.

### 7.2 Phase 3A Correctness Outcome
For each Phase 3A algorithm/configuration:
1. actual global condition is evaluated from the six-sensor observed mean using the Phase 3A p90 and canonical boundary rule;
2. no selected-sensor observation is missing, so every Phase 3A bucket is globally evaluable;
3. cluster cancellation is acceptable only if it does not conceal a true global threshold violation;
4. correctness requires the **last root-known state** to agree with the actual global threshold state at each bucket; count false-safe and false-violated states separately, and fail if either count is nonzero;
5. the actual six-sensor mean is evaluated offline for validation and must not silently trigger a communication event;
6. correctness test status is a gate for interpreting communication savings.

### 7.3 Phase 3A Communication Metrics
Report actual transmission counts by category:
1. node/local-trigger messages;
2. cluster collection/check requests;
3. cluster collection/check responses;
4. coordinator-to-root escalation messages;
5. root synchronization requests;
6. synchronization responses;
7. synchronization broadcasts/constraint updates;
8. total messages.

Rules:
1. the **primary model** is six sensor nodes and a separate root component; coordinators are sensor members;
2. one message is one actual transmission between distinct nodes/components; **self-communication costs zero**;
3. requests and responses are separate messages, and an update delivered to each individual sensor counts as a separate transmission;
4. category totals reconcile exactly to total messages; bundles containing cluster membership or moment data do not create extra transmissions beyond their enclosing messages;
5. local computation and coordinator selection are not messages by themselves;
6. no membership-change message categories are required in Phase 3A because membership is fixed;
7. the chapter's alternative **root-as-sensor broadcast accounting** may be reported as a clearly labeled secondary comparison, never substituted for the primary actual-transmission total;
8. Phase 2, FMIC, and SMIC use the same transmission definition, even though their monitoring events and categories differ.

### 7.4 Phase 3A Comparison Metrics
For the matched Phase 2, FMIC, and SMIC runs report at minimum:
1. total messages;
2. communication totals by relevant type;
3. communication reduction versus the matched Phase 2 baseline for FMIC/SMIC;
4. communication reduction versus a centralized six-sensor-every-minute baseline;
5. node/local violations;
6. coordinator checks and violations for clustered algorithms;
7. root/global synchronizations or escalations;
8. selected cluster count and cluster-size summary for FMIC/SMIC;
9. correctness-pass status.

The centralized Phase 3A sensor-message baseline is `19,984 * 6 = 119,904` one-way sensor transmissions if defined as one transmission per sensor per minute. Any alternative centralized counting convention must be named explicitly and applied consistently.

### 7.5 Alpha Tuning Metrics
US-3.22 is the required final Phase 3A sensitivity evaluation, **after US-3.21 passes**. Its minimum retained 38-row table contains:
- algorithm and alpha;
- total messages and separate transmission category totals;
- false-safe count, false-violated count, and correctness-pass status;
- root synchronizations and compact cluster count/size information;
- reduction against the same matched Phase 2 baseline.

Use only correctness-passing configurations when describing a minimum-message alpha. This is dataset-specific calibration, not a universal ranking. Do not require full merge traces or per-alpha forensic state.

### 7.6 Phase 3B Metrics (Optional)
If Phase 3B is later approved, availability-specific metrics and cause attribution may be reintroduced. They are not Phase 3A acceptance requirements and must not be mixed into the stable-cohort primary result.

---

## 8) Quality Gates And Acceptance

### 8.1 Transformation Gates (Phase 1)
Existing Phase 1 **quality-gate thresholds and temperature aggregation rules** remain unchanged. During the implementation update, source-file discovery was corrected to exclude `temperature_raw.csv`, an aggregate CSV inadvertently mixed with raw files. The recorded duplicate-key rate changed from **50.050912%** (failing the 0.5% gate) to **0.101823%** (passing). This is a correction to the list of input files, **not** a change to the sensor monitoring formulas or a relaxation of the gate. The separate Phase 3A addition is the cohort-specific statistics row calculated from the aligned Phase 1 output. See `transformation_decisions.md` for the run record.

### 8.2 Phase 3A Input And Threshold Gates
Before matched Phase 2 or clustered runs:
1. sensors are exactly A, C, D, E, F, and G;
2. approved timestamps match the locked interval;
3. exactly 19,984 buckets are present;
4. both interval endpoints are inclusive and every adjacent timestamp differs by exactly 60 seconds;
5. every selected sensor has a valid finite value in every bucket;
6. no imputation is present;
7. the Phase 3A p90 is recomputed programmatically from the six-sensor mean and recorded in `phase1_average_statistics.csv`;
8. all Phase 3A algorithms read the same full-precision threshold value.

### 8.3 Matched Phase 2 Baseline Gate
1. Reuse the existing Phase 2 engine.
2. Run only the approved cohort/interval with the Phase 3A p90.
3. Membership-change behavior must remain inactive for the entire run.
4. Communication totals reconcile.
5. Existing Phase 2 correctness checks relevant to stable operation pass.
6. This matched result, not the historical full-data Phase 2 total, is the comparator for FMIC/SMIC.

### 8.4 Phase 3A Clustering Gates
Phase 3A may proceed to final comparison only when:
1. source-aligned history and normalization tests pass;
2. partition-quality and greedy-merge tests match hand calculations;
3. FMIC passes formula-level and end-to-end correctness tests before SMIC is interpreted;
4. SMIC independently passes its formula-level and end-to-end correctness tests;
5. no synthetic cancellation test hides a crossing in **either** direction: false-safe and false-violated states are both disallowed;
6. tests cover below, exactly at, and above each relevant boundary, including the zero-allowance state;
7. communication categories reconcile exactly to total messages;
8. production output excludes unnecessary full-run audit traces and remains manageable;
9. FMIC and SMIC use the same monitoring architecture except for the intended moment and weight/allowance calculations; their root synchronization timestamps need not match;
10. both directions of monitoring correctness agree with offline six-sensor truth, never with an assumed Phase 2 event schedule;
11. US-3.21 comprehensive validation passes before the required US-3.22 sweep and only correctness-passing alpha configurations may be considered for preferred-result reporting.

### 8.5 Phase 3B Gate (Optional)
No Phase 3B gate blocks Phase 3A completion. Phase 3B begins only after separate approval and may reuse the earlier availability-aware requirements as a starting point.

---

## 9) Verification Checklist

### 9.1 Phase 2 Historical Implementation
1. Existing full-data Phase 2 artifacts remain preserved.
2. Existing state-machine and communication validation remain part of project history.
3. Historical availability-aware behavior is not used as the primary Phase 3A comparator.

### 9.2 Phase 3A Experiment Setup
1. Locked cohort is A, C, D, E, F, G.
2. Locked interval is `2022-02-24T18:50:00+00:00` through `2022-03-10T15:53:00+00:00`.
3. Row count is 19,984.
4. Complete observations are verified for all six sensors on every row.
5. Phase 3A p90 is calculated from this exact population and added to `phase1_average_statistics.csv` without overwriting existing statistics.
6. A minimal `phase3a_experiment_config.json` or equivalent records the locked cohort, interval, expected row count, and threshold source.

### 9.3 Matched Phase 2 Baseline
1. Existing Phase 2 code is reused.
2. It reads the Phase 3A cohort/interval and p90.
3. No membership transition occurs.
4. Stable-run communication totals reconcile.
5. The output is clearly identified as the Phase 3A matched Phase 2 comparator.

### 9.4 Phase 3A Clustering Foundation
1. History updates use the active synchronization reference and retain sign.
2. History survives synchronization and uses the new reference afterward.
3. Normalization is signed, non-destructive, and calculated over all six stable sensors.
4. Initial all-zero history uses the explicit deterministic fallback.
5. Cluster quality and partition quality match the source formulas.
6. Greedy merging matches hand-calculated examples and stops/selects partitions as specified.
7. Availability-specific branches do not complicate the Phase 3A primary path.

### 9.5 Phase 3A FMIC/SMIC
**Implementation and validation through US-3.22:** Both engines are present in the current notebook, passed the US-3.21 synthetic correctness and communication-accounting gate, and completed the US-3.22 alpha sweep with passing correctness and accounting on all 38 runs.

1. FMIC weights and allowances match hand calculations.
2. FMIC passes end-to-end tests before SMIC comparison.
3. SMIC first/second-moment calculations and allowances match hand calculations.
4. SMIC uses the shared monitoring architecture rather than a parallel implementation.
5. Node activity, coordinator checks, and root escalation are distinguishable.
6. Safe cancellation can reduce escalation without hiding global violation.
7. Unsafe partial cancellation escalates correctly.
8. Node/coordinator/global boundary tests pass.
9. Communication accounting matches the hand-counted synthetic example.

### 9.6 Phase 3A Outputs And Reproducibility
1. No full sensor-by-minute production history trace is required.
2. No exhaustive per-alpha merge-search JSON is required.
3. Clustering-event output retains raw/normalized histories, selected partition, quality, cluster count, coordinator, algorithm, alpha, timestamp, and event ID.
4. Completed algorithm-specific event and summary outputs are `phase3a_fmic_events.csv`, `phase3a_fmic_summary.json`, `phase3a_smic_events.csv`, and `phase3a_smic_summary.json`. US-3.22 will produce the compact alpha-results table and final comparison; do not mistake the older proposed generic filename for an existing output.
5. Debug traces are opt-in and small.
6. The run can be reproduced from source data, config, threshold statistics, code/notebook, tests, and compact outputs.

### 9.7 Phase 3B (Optional)
1. Phase 3B requirements are not evaluated as part of Phase 3A completion.
2. If later approved, the earlier availability-aware stories may be reviewed and revised before reuse rather than assumed to remain automatically authoritative.

---

## 10) Sensitivity Matrix (Required Reruns)

### 10.1 Phase 2 Sensitivity
The historical Phase 2 sensitivity work remains available for reference but is not a prerequisite for the Phase 3A matched comparison unless a specific issue requires rerunning it.

### 10.2 Phase 3A Alpha Tuning
After **US-3.21 comprehensive validation passes**, US-3.22 **requires** the following coarse grid for **both** FMIC and SMIC (19 values each, 38 runs):

`0.05, 0.10, 0.15, ..., 0.95`

For each algorithm/alpha retain compact evidence:
1. algorithm and alpha;
2. total messages and message-category counts;
3. false-safe count, false-violated count, and correctness-pass status;
4. root synchronizations and selected cluster/size summary;
5. reduction against the fixed matched Phase 2 baseline.

Interpretation:
1. alpha is a tuning parameter, not the primary research question;
2. `alpha=0.10` is an initial implementation value, not a claimed optimum;
3. only correctness-passing configurations may be considered;
4. do not require a finer sweep unless the team later decides it adds value;
5. do not preserve full internal search traces for every alpha.

### 10.3 Phase 3A Primary Comparison
After tuning, produce the matched comparison using the same cohort, interval, threshold, observations, boundary convention, and counting rules:
1. stable-cohort Phase 2;
2. stable-cohort FMIC;
3. stable-cohort SMIC.

### 10.4 Phase 3B Availability Robustness (Optional)
No availability sensitivity or attribution run is required for Phase 3A. If Phase 3B is approved later, define its experiment separately rather than treating it as a hidden extension of Phase 3A.

---

## 11) Deliverables

### Code And Execution
1. `scripts/build_phase1_temperature.py` — existing transformation, with minimal statistics extension if that is the current statistics-generation location.
2. `scripts/build_phase2_temperature_sensors.ipynb` and `scripts/phase2_monitoring.py` — existing Phase 2 implementation reused for the matched Phase 3A baseline.
3. `scripts/build_phase3_temperature_clustering.ipynb` — existing Phase 3 clustering foundation simplified for stable-cohort Phase 3A and extended with FMIC/SMIC.
4. Focused Phase 3A synthetic/formula-level test harness. Existing test files may be refactored or supplemented rather than multiplied unnecessarily.

### Data And Result Artifacts
Target Phase 3A artifacts are intentionally small:
1. existing `artifacts/aligned_phase1_temperature.csv`;
2. existing `artifacts/phase1_average_statistics.csv` plus the new Phase 3A statistics row;
3. `phase3a_experiment_config.json` or equivalent minimal config;
4. matched stable-cohort Phase 2 result artifact;
5. **Completed FMIC artifacts:** `phase3a_fmic_events.csv` and `phase3a_fmic_summary.json`;
6. **Completed SMIC artifacts:** `phase3a_smic_events.csv` and `phase3a_smic_summary.json`;
7. **US-3.21 complete:** `phase3a_validation_summary.json` records the synthetic/unit-test results and production replay checks;
8. **US-3.22 complete:** `phase3a_alpha_results.csv` (38 rows), `phase3a_alpha_events.csv`, `phase3a_comparison_summary.json`, and three compact plots for messages, synchronizations, and clustering versus alpha. `phase3a_cluster_events.csv`/`phase3a_results.csv` in earlier drafts are generic proposed names, not the implemented artifact names.

Detailed debug traces are optional and are not produced by default. Avoid duplicate summary files unless they provide a clear human-use case.

### Documentation
1. Updated `Distributed_Monitoring_POC_Project_Plan.md` incorporating this pivot.
2. `Phase_3A_Pivot_Plan.md` retained as the sponsor-approved decision record.
3. Existing `Phase_3_User_Stories.md` retained as project history; new user stories are appended for the Phase 3A pivot rather than rewriting completed stories.
4. Updated run instructions for deriving the Phase 3A threshold, producing the matched Phase 2 baseline, and running FMIC/SMIC; the detailed completed-step record is in **§22 of `Phase_3A_Pivot_Plan.md`** (do not duplicate that chronology here).
5. Metrics interpretation notes that clearly distinguish Phase 3A stable-node conclusions from optional Phase 3B availability robustness.
6. Source-alignment notes referencing the definitive chapter and documenting any explicit project adaptations.
7. Focused correctness-test results before communication-savings claims.

---

## 12) Major Risks And Mitigations

1. **Risk: the stable cohort is accidentally filtered incorrectly.**  
Mitigation: enforce the Phase 3A input contract on sensor IDs, inclusive endpoints, exact 19,984-row count, exact 60-second timestamp spacing, and complete finite observations before any monitoring begins.

2. **Risk: the wrong threshold population is used.**  
Mitigation: compute the Phase 3A p90 programmatically from the approved six-sensor interval, add it as a new Phase 1 statistics row, and require matched Phase 2/FMIC/SMIC runs to read that same full-precision value.

3. **Risk: historical availability logic continues to complicate Phase 3A.**  
Mitigation: add a pivot user story that removes or isolates departure, return, dynamic eligibility, changing denominator, and membership-attribution branches from the Phase 3A path.

4. **Risk: drift from the definitive chapter's mathematical methodology while simplifying.**  
Mitigation: simplify infrastructure and outputs, not the source-defined history, normalization, partition-quality, greedy-merge, FMIC, or SMIC mathematics; retain hand-calculated formula tests.

5. **Risk: signed cancellation hides a true global threshold violation.**  
Mitigation: require safe- and unsafe-cancellation synthetic tests, bidirectional crossing tests, and comparison to offline actual global state (not Phase 2 synchronization timestamps) before accepting communication savings.

6. **Risk: FMIC and SMIC become duplicate codebases.**  
Mitigation: require one shared monitoring architecture with algorithm-specific weight/allowance functions.

7. **Risk: alpha tuning expands back into a large research subproject.**  
Mitigation: keep the required US-3.22 19-value-per-algorithm grid compact and run it only after US-3.21 tests pass; do not add an uncontrolled finer search.

8. **Risk: communication savings are overstated through incomplete counting.**  
Mitigation: count actual trigger, request, response, coordinator escalation, synchronization, and broadcast transmissions separately and reconcile exactly to totals.

9. **Risk: production artifacts again become too large to inspect.**  
Mitigation: prohibit full sensor-by-minute history traces and exhaustive merge-search records by default; retain compact event-level outputs and use debug traces only on small cases.

10. **Risk: reproducibility is confused with storing every intermediate state.**  
Mitigation: define reproducibility around source data, config, threshold provenance, deterministic code, tests, and compact outputs; recompute deterministic internals when needed.

11. **Risk: stable-cohort results are overgeneralized to intermittent sensors.**  
Mitigation: state explicitly that Phase 3A evaluates stable node participation; reserve online/offline robustness claims for optional Phase 3B.

12. **Risk: old and new user stories give AI-assisted coding contradictory instructions.**  
Mitigation: retain historical stories but append new pivot stories with explicit Phase 3A supersession language, and point coding tasks to the pivot plan plus the relevant new story.

---

## 13) Ready-For-Build Checklist

### Phase 1 / Threshold Ready
1. Full aligned Phase 1 artifact exists and remains unchanged by the pivot.
2. Stable cohort and interval are locked: A, C, D, E, F, G; 2022-02-24T18:50:00+00:00 through 2022-03-10T15:53:00+00:00.
3. Exactly 19,984 complete, consecutive one-minute Phase 3A buckets are verified, with both endpoints inclusive and no timestamp gaps.
4. `phase1_average_statistics.csv` contains the programmatically computed Phase 3A p90 row while preserving existing rows.

### Matched Phase 2 Ready
1. Existing Phase 2 implementation runs on the Phase 3A subset without code duplication.
2. It reads the Phase 3A p90.
3. Membership-change behavior never activates.
4. Communication totals reconcile.
5. Result is labeled as the matched Phase 3A Phase 2 baseline.

### Phase 3A Clustering Foundation Ready
1. Existing history, normalization, cluster-quality, and greedy-merge logic is revalidated against hand calculations.
2. Availability-only complexity is removed or isolated from the Phase 3A execution path.
3. Production output no longer writes the full sensor-by-minute history trace or exhaustive merge-search records.
4. Compact clustering-event output is defined and manageable.
5. Debug tracing is opt-in.

### FMIC Ready
1. First-moment weights and allowances have direct tests.
2. Coordinator allowance matches the source rule.
3. FMIC passes safe/unsafe cancellation, boundary, and communication tests.
4. FMIC runs end-to-end on the Phase 3A data at the baseline alpha.

### SMIC Ready
1. First- and second-moment calculations have direct tests.
2. SMIC reuses the FMIC monitoring architecture.
3. SMIC passes the same end-to-end correctness gates with only intended algorithm-specific differences.

### Final Phase 3A Comparison Ready
**Complete as of 2026-11-03:** US-3.21 passed before the US-3.22 production sweep; all 38 alpha runs passed correctness and message reconciliation.

1. FMIC and SMIC pass the US-3.21 comprehensive correctness gate.
2. Compact coarse alpha tuning is complete.
3. Preferred configurations are selected only from correctness-passing runs.
4. Matched Phase 2, FMIC, and SMIC use identical Phase 3A cohort, interval, threshold, observations, and counting conventions.
5. Communication totals and reduction calculations reconcile.
6. Final outputs are small enough for direct human review.
7. Reporting clearly states that Phase 3A does not test intermittent sensor availability.

### Phase 3B Status
Phase 3B is optional and not required for the above checklist. If approved later, define its scope and acceptance criteria separately before implementation.

---

## 14) Implementation Status And Results — Through US-3.22

**Recorded:** 2026-11-03. This is a short status checkpoint, **not** a replacement for the milestone-by-milestone record in `Phase_3A_Pivot_Plan.md`, §22. The US-3.21 gate passed before the sweep; all 38 US-3.22 runs passed correctness and message reconciliation, and alpha=0.10 event fingerprints and message categories matched the saved baselines.

| User story | Work completed or planned | Status |
|---|---|---|
| US-3.16 | Simplify Phase 3 for the fixed six-sensor cohort; retain signed history and clustering | Implemented and reviewed |
| US-3.17 | Lock and validate the exact input cohort, interval, and 19,984 complete minute buckets | Implemented and reviewed |
| US-3.18 | Calculate the authoritative cohort-specific p90 and matched Phase 2 baseline | Implemented and reviewed |
| US-3.19 | Implement FMIC, including first-moment weights, two-sided threshold checks, and transparent messages | Implemented and reviewed |
| US-3.20 | Add SMIC's second moment to the shared monitoring engine and confirm FMIC regression behavior | Implemented and reviewed |
| US-3.21 | Comprehensive synthetic and mathematical validation across both algorithms | Implemented and passed; 91 tests |
| US-3.22 | Required 19-alpha sensitivity sweep for each algorithm and final matched evaluation | Implemented and passed; 38 full-length runs |
| US-3.23 | Two-sided equal-allowance Phase 2 policy and separately named matched baseline | Implemented and passed; 103 regression tests |

### 14.1 Prespecified alpha-0.10 comparison

The baseline comparison uses sensors A, C, D, E, F, G; the **19,984-bucket** inclusive interval; full-precision p90 of **22.428666649999997 °C**; the same boundary convention; and `alpha=0.10` for FMIC/SMIC. It remains the prespecified apples-to-apples comparison, separate from the exploratory grid minima.

| Metric | Matched Phase 2 | FMIC | SMIC |
|---|---:|---:|---:|
| Total messages | 38,087 | 11,922 | 11,902 |
| Root synchronizations | 2,107 | 293 | 293 |
| Actual globally violated minutes | 1,999 | 1,999 | 1,999 |
| Reported correctness status | Passed | Passed | Passed |
| Reported false-safe / false-violated states | See baseline correctness fields | 0 / 0 | 0 / 0 |
| Message reduction vs matched Phase 2 | — | 68.70% | 68.75% |

At this one alpha, SMIC uses **20 fewer messages** than FMIC, about **0.17% of FMIC's total**. The difference is 8 node-trigger messages, 6 cluster-check requests, and 6 responses; root-message and coordinator-escalation totals are equal. This is a small dataset-specific difference, not evidence that one method is generally better. The centralized six-sensor-every-minute reference is **119,904** sensor transmissions. Phase 2, FMIC, and SMIC do **not** share identical root synchronization schedules.

### 14.2 US-3.22 alpha sensitivity results

The 19 tested alpha values were run independently for each algorithm on the same approved cohort, interval, threshold, and 19,984 buckets. All 38 runs had zero false-safe and false-violated states, `correctness_status=passed`, and exactly reconciled category/message totals. Both message-count curves are irregular across the tested grid.

| Metric at minimum observed alpha | FMIC | SMIC |
|---|---:|---:|
| Minimum observed alpha | 0.65 | 0.65 |
| Total messages | 8,722 | 8,720 |
| Root synchronizations, including initialization | 436 | 436 |
| Mean clusters per synchronization event, including initialization | 5.8005 | 5.8005 |
| Mean cluster size across all synchronization clusters | 1.0344 | 1.0344 |
| Reduction vs. matched Phase 2 | 77.10% | 77.11% |
| Reduction vs. 119,904 centralized transmissions | 92.73% | 92.73% |

The 0.65 values are minimum observed on this single dataset and tested grid, not theoretically optimal settings or out-of-sample results. At 0.65 SMIC's two-message advantage comes from two fewer coordinator-to-root escalations. Cluster-size mean is total sensor memberships across all selected partitions at synchronization events divided by total clusters; the initialization partition is included for every method and alpha. Mean cluster count is the arithmetic mean of per-event counts with initialization included.

### 14.3 Existing and completed evidence

- **Existing:** `phase1_average_statistics.csv` (`phase3a_stable_cohort` row), `phase3a_phase2_baseline.json`, `phase3a_fmic_events.csv`, `phase3a_fmic_summary.json`, `phase3a_smic_events.csv`, and `phase3a_smic_summary.json`. The FMIC and SMIC event files hold compact root synchronization and clustering records rather than full minute-by-minute sensor traces.
- **Existing:** Phase 3A notebook with a shared FMIC/SMIC monitoring engine and focused moment/protocol tests. Source chapter formulas and project-specific choices are distinguished in §§2, 6, and 7.
- **Completed:** `phase3a_validation_summary.json` records the test command, scenarios, source references, production replay results, and limitations for US-3.21.
- **Completed:** `phase3a_alpha_results.csv` (38 rows), `phase3a_alpha_events.csv` (14,829 synchronization snapshots), and `phase3a_comparison_summary.json`.
- **Completed:** `phase3a_messages_vs_alpha.png`, `phase3a_synchronizations_vs_alpha.png`, and `phase3a_clustering_vs_alpha.png`; all plots derive from the saved results table.
- **Optional, not part of Phase 3A acceptance:** Phase 3B intermittent-sensor experiments.

For the complete step-by-step explanation of why and how the changes were made, refer to `Phase_3A_Pivot_Plan.md`, §22.

### 14.4 US-3.23 revised Phase 2 baseline (2026-11-10)

The shared Phase 2 engine now uses `abs(threshold - synchronized_mean)` and
absolute local deviations, retaining a verified root-known SAFE/VIOLATED state.
Negative-margin scheduling is removed; membership, initialization, next-bucket
activation, and actual-transmission accounting are retained.

The approved 19,984-bucket matched run passed with **9,159 messages**:
753 triggers plus 2,802 requests, 2,802 responses, and 2,802 state updates.
There were **467 synchronizations**, zero membership changes, 1,999 truly
violated buckets, and **zero false-safe and false-violated states**.
The historical 38,087-message / 2,107-synchronization benchmark remains
unchanged. The aggregate policy difference is -28,928 messages and -1,640
synchronizations; no separate causal attribution is inferred from those totals.

The revised artifacts are `phase3a_phase2_two_sided_baseline.json` and
`phase3a_phase2_two_sided_events.csv`. The summary records the policy, commands,
input/config/code hashes, independent root-state correctness, historical
comparison, and before/after hashes for protected outputs. The notebook's
general full-data reports use the `phase2_two_sided_*` prefix.

Sections 14.1–14.2 and published US-3.22 artifacts retain the original Phase 2
denominator as a historical experiment record. No Phase 3 code or outputs were
changed. Any revised Phase 2 versus FMIC/SMIC interpretation remains preliminary:
moment-based allowances and coordinator/cluster protocols are not isolated by
this story. This does not evaluate intermittent availability or establish
universal algorithm superiority.
