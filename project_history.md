# Project History

This document records major decisions, pivots, discussions, and implementation
milestones. The [project plan](Distributed_Monitoring_POC_Project_Plan.md) is
the current specification; this history does not govern current behavior.
The [changelog](CHANGELOG.md) records dated changes and validation.

## Reading the record

The original documents below are reproduced in full, grouped by the development
they describe. Their dates, paths, commands, requirements, and status statements
are historical snapshots, not instructions to run retired workflows or claims
that a referenced file still exists. An original "current" or "not implemented"
statement applies at the time of that source. Source-specific numerical and
validation claims are retained as recorded, not independently revalidated by
this consolidation. See the project plan and current workflow documentation
for present requirements and locations.

Untouched source copies and their section mapping are retained locally under
`C:\Users\mcphe\.copilot\session-state\f24974c1-55b9-4370-b3a9-619ec9f44fa8\files\us-002-recovery\`.
These session files are not tracked by Git; the complete source text is also
embedded in this history. Back up the recovery directory outside session storage
if a separate long-term copy is needed.

### Transformation and duplicate-input discovery

The [transformation run records](#transformation-run-records) preserve five
automated runs. The first three processed 3,472 files and reported a duplicate
key rate of 50.050912%, failing the 0.5% gate. After the aggregate
`temperature_raw.csv` was excluded, the 2026-11-03 run processed 3,471 files
and reported 0.101823%, passing; the later recorded notebook run reported the
same rate. All gate values and original timestamps remain in the source record.
The change corrected the input population rather than relaxing the gate.

### Phase 2 monitoring corrections and policy evolution

The [notebook correction discussion](#phase-2-notebook-corrections) explains
the original reference, local-trigger, threshold-boundary, synchronization,
and communication-counting problems and proposed corrections. Its
warming-only and negative-margin scheduling rules are historical: US-3.23
later adopted two-sided absolute deviations and retained the last verified root
state without resynchronizing solely because the margin is negative.

### Phase 3A stable-cohort pivot and implementation

The [pivot record](#phase-3a-pivot-record) preserves the sponsor-approved
decision to focus the primary experiment on six continuously observed sensors,
the source-aligned mathematical and protocol requirements, and the original
implementation milestones. Its original precedence language, proposed paths,
statistics-row ownership, and deliverable descriptions are historical; the
current plan incorporates applicable requirements and later changes.

### Comparability and controlled evaluation

The [November 10 comparability record](#phase-3a-comparability-record)
explains why the original 38,087-message signed-margin Phase 2 comparison
could not isolate clustering from threshold policy, weighting, and protocol.
Its status that US-3.23-3.25 were not implemented describes that discussion at
the time. Later [changelog entries](CHANGELOG.md) record the revised two-sided
baseline, Phase 2/C0 per-bucket equivalence, and C0/C1/C2 plus clustered
evaluation and validation. The revised 9,159-message baseline and the older
38,087-message baseline must not be interchanged. The original source also
distinguishes provisional diagnostic replays from saved production evidence.
Related requirements are recorded in
[US-3.23](User%20Stories/US-3.23_phase2_two_sided_geometric_threshold_policy.md),
[US-3.24](User%20Stories/US-3.24_phase2_phase3_protocol_equivalence_validation.md),
[US-3.25](User%20Stories/US-3.25_isolate_weighting_clustering_and_revised_alpha_evaluation.md),
and [US-3.26](User%20Stories/US-3.26_harden_US-3.25_validation_reproducibility_and_reporting.md).
User stories are local, Git-ignored planning material and may be absent from a
source-only checkout.

## Original records

Each section below reproduces one complete source document, including its
headings and historical references. The recovery inventory records the
original source bytes, SHA-256 values, and section mapping; those copies were
verified before the originals were removed. The source documents may contain
mutually superseded policies and references that are no longer active.


<a id="transformation-run-records"></a>

### Transformation run records

Original source: `Writing/Markdowns/transformation_decisions.md`. The following is a historical record, not current requirements.

<!-- US-0.02 ORIGINAL SOURCE START: Writing/Markdowns/transformation_decisions.md -->


## Automated Run
- Date: 2026-10-08T11:10:49+00:00
- Script: build_phase1_temperature.py
- Config file: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\config\transformation_defaults.yaml
- Data directory: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\Data\files_csv
- Files processed: 3472

### Locked Defaults Used
- bucket_size_seconds: 60
- min_devices_per_snapshot: 6
- stale_threshold_seconds: 120

### Gate Checks
- schema_validity_min_percent: actual=100.0, threshold >= 100.0, passed=True
- duplicate_key_rate_max_percent: actual=50.050912, threshold <= 0.5, passed=False
- stale_snapshot_rate_max_percent: actual=0.971359, threshold <= 10.0, passed=True
- device_coverage_min_percent: actual=99.028641, threshold >= 90.0, passed=True

### QC Snapshot
- schema_validity_percent: 100.0
- duplicate_key_rate_percent: 50.050912
- stale_snapshot_rate_percent: 0.971359
- device_coverage_percent: 99.028641

## Automated Run
- Date: 2026-10-08T11:15:37+00:00
- Script: build_phase1_temperature.py
- Config file: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\config\transformation_defaults.yaml
- Data directory: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\Data\files_csv
- Files processed: 3472

### Locked Defaults Used
- bucket_size_seconds: 60
- min_devices_per_snapshot: 6
- stale_threshold_seconds: 120

### Gate Checks
- schema_validity_min_percent: actual=100.0, threshold >= 100.0, passed=True
- duplicate_key_rate_max_percent: actual=50.050912, threshold <= 0.5, passed=False
- stale_snapshot_rate_max_percent: actual=0.971359, threshold <= 10.0, passed=True
- device_coverage_min_percent: actual=99.028641, threshold >= 90.0, passed=True

### QC Snapshot
- schema_validity_percent: 100.0
- duplicate_key_rate_percent: 50.050912
- stale_snapshot_rate_percent: 0.971359
- device_coverage_percent: 99.028641

## Automated Run
- Date: 2026-11-03T13:00:49+00:00
- Script: build_phase1_temperature.py
- Config file: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\config\transformation_defaults.yaml
- Data directory: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\Data\files_csv
- Files processed: 3472

### Locked Defaults Used
- bucket_size_seconds: 60
- min_devices_per_snapshot: 6
- stale_threshold_seconds: 120

### Gate Checks
- schema_validity_min_percent: actual=100.0, threshold >= 100.0, passed=True
- duplicate_key_rate_max_percent: actual=50.050912, threshold <= 0.5, passed=False
- stale_snapshot_rate_max_percent: actual=0.971359, threshold <= 10.0, passed=True
- device_coverage_min_percent: actual=99.028641, threshold >= 90.0, passed=True

### QC Snapshot
- schema_validity_percent: 100.0
- duplicate_key_rate_percent: 50.050912
- stale_snapshot_rate_percent: 0.971359
- device_coverage_percent: 99.028641

## Automated Run
- Date: 2026-11-03T15:47:16+00:00
- Script: build_phase1_temperature.py
- Config file: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\config\transformation_defaults.yaml
- Data directory: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\Data\files_csv
- Files processed: 3471
- Excluded non-source CSV filenames: ["temperature_raw.csv"]

### Locked Defaults Used
- bucket_size_seconds: 60
- min_devices_per_snapshot: 6
- stale_threshold_seconds: 120

### Gate Checks
- schema_validity_min_percent: actual=100.0, threshold >= 100.0, passed=True
- duplicate_key_rate_max_percent: actual=0.101823, threshold <= 0.5, passed=True
- stale_snapshot_rate_max_percent: actual=0.971359, threshold <= 10.0, passed=True
- device_coverage_min_percent: actual=99.028641, threshold >= 90.0, passed=True

### QC Snapshot
- schema_validity_percent: 100.0
- duplicate_key_rate_percent: 0.101823
- stale_snapshot_rate_percent: 0.971359
- device_coverage_percent: 99.028641

## Automated Run
- Date: 2026-11-12T00:01:10+00:00
- Script: phase1_implement.ipynb
- Config file: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\config\transformation_defaults.yaml
- Data directory: C:\Users\mcphe\Dropbox\Business\Data\sensor_project\Data\files_csv
- Files processed: 3471
- Excluded non-source CSV filenames: ["temperature_raw.csv"]

### Locked Defaults Used
- bucket_size_seconds: 60
- min_devices_per_snapshot: 6
- stale_threshold_seconds: 120

### Gate Checks
- schema_validity_min_percent: actual=100.0, threshold >= 100.0, passed=True
- duplicate_key_rate_max_percent: actual=0.101823, threshold <= 0.5, passed=True
- stale_snapshot_rate_max_percent: actual=0.971359, threshold <= 10.0, passed=True
- device_coverage_min_percent: actual=99.028641, threshold >= 90.0, passed=True

### QC Snapshot
- schema_validity_percent: 100.0
- duplicate_key_rate_percent: 0.101823
- stale_snapshot_rate_percent: 0.971359
- device_coverage_percent: 99.028641


<!-- US-0.02 ORIGINAL SOURCE END: Writing/Markdowns/transformation_decisions.md -->


<a id="phase-2-notebook-corrections"></a>

### Phase 2 notebook corrections

Original source: `Writing/Markdowns/distributed_monitoring_notebook_required_changes.md`. The following is a historical record, not current requirements.

<!-- US-0.02 ORIGINAL SOURCE START: Writing/Markdowns/distributed_monitoring_notebook_required_changes.md -->

# Distributed Monitoring Notebook: Required Logic Corrections

## Purpose

This document describes the major logical issues identified in `build_phase2_temperature_sensors.ipynb` and the changes required to align the implementation with the intended distributed monitoring design.

The corrected implementation should:

1. maintain a synchronized reference value for each sensor,
2. calculate each sensor's local deviation from its own synchronized value,
3. compare each local deviation against the correct local constraint,
4. handle global threshold violations and negative delta values explicitly,
5. apply consistent threshold boundaries, and
6. count all communication events transparently.

## Active Implementation Policy Note

### Approach A comparison policy (2026-10-21)

Keep the selected cohort constant, but synchronize on every observed-contributor
departure/return. Apply this same policy to Phase 2, FMIC, and SMIC; Phase 3
reclusters on each completed synchronization. The existing Phase 2 engine already
implements this comparator, so no duplicate fixed/dynamic modes are required.
The `dynamic_observed_only` metadata refers to changing availability within the
cohort. Mean/threshold changes caused solely by a changed denominator must still
be caught by availability-triggered synchronization. Report algorithm differences
under the matched policy and availability costs by cause; do not interpret
subtracting those costs as a no-availability-change counterfactual.

### Local-state reporting and correctness validation (2026-10-21)

1. `distributed_constraint_state` means a sensor-local allowance violation, not
   that synchronization occurred: `VIOLATING` if any online sensor has deviation
   greater than or equal to its entry allowance; `FEASIBLE` only when every online
   sensor has a valid comparison and none violates. Incomplete comparison coverage
   is `NOT_EVALUABLE`; no readings is `UNDEFINED`.
2. Forced synchronization rows still calculate deviations and local comparisons
   for reporting, using entry state, but emit zero local triggers and preserve
   existing synchronization reasons, causes, traffic, and next-row timing.
3. Remove `distributed_alert`, formerly a redundant synchronization alias. Use
   `event_resync_performed` to identify a completed synchronization, and the
   existing reason/causes fields to explain it.
4. Confusion metrics, precision/recall, false-safe/false-alert, and detection delays
   remain synchronization-based diagnostics, not actual global-warning accuracy.
   The new local-state meaning does not change their predictor or calculation.
5. Extend the existing monitoring module/test suite rather than add one-off
   validation scripts. Independently replay unrounded source observations to
   check means, references, allowances, state continuity, triggers, membership,
   pending causes, comparison coverage, and traffic. Validate before rounding and
   in notebook Stage 4 after export; CSV numeric checks allow reporting precision,
   but boundary decisions always use original unrounded inputs.
6. Synthetic tests cover safe/partial cancellation, simultaneous triggers,
   cooling recovery, unequal multi-sensor states, forced-row reporting, boundary
   cases, and deliberately corrupted traces rejected with bucket/field details.

### Membership-aware Phase 2 policy (2026-10-21)

At the 2026-10-21 milestone, the notebook implemented the Phase 2 slice of
US-3.9 without clustering or additional run modes. The current import-safe
shared engine is `scripts/shared_monitoring_engine.py`; its later two-sided
policy supersedes historical trigger rules in this section where they differ:

1. Online/offline status is known without communication. Compare online sets each
   bucket; first missing/returning observations trigger synchronization.
2. Initialize at the first usable bucket and count startup traffic. Do not look
   ahead when leading buckets have no readings.
3. Each completed synchronization contacts only N currently online sensors:
   N requests, N responses, N threshold updates. Offline traffic and membership
   notification costs are zero.
4. Combine causes into one synchronization per bucket, retain every cause in
   `event_resync_causes`, and prefer `negative_delta_from_prior_row` as primary.
   Initialization/membership/pending-negative-margin rows suppress local triggers.
5. Global mean is the observed-only online mean. Zero online sensors means an
   undefined global state, pending synchronization, and zero traffic, not reuse
   of an older mean as a current observation. State updates apply next row.
6. Classification diagnostics exclude undefined rows; synchronization is an
   operational indicator, not a declaration that a threshold was violated.
7. Report the configured-cohort counterfactual and a matched observed-only
   centralized baseline separately. Cause-attributed traffic is not added again
   to transmission-type totals.

Run `python -m unittest scripts.test_shared_monitoring -v` for synthetic state,
message-count, and notebook-report regression tests.

For the active Phase 2 implementation in this repository, the following canonical policy now applies:

1. local trigger is warming-only: `local_deviation >= local_margin`,
2. cooling (negative) local deviations do not trigger a re-sync request,
3. the preferred row-level timing columns are `entry_xbar_t0`, `entry_delta_global`, `observed_global_average`, and `exit_delta_global`,
4. per-sensor entry-state fields use `entry_{sensor}_reference_value` and `entry_{sensor}_local_margin`, and
5. per-sensor event fields use `event_{sensor}_local_deviation` and `event_{sensor}_resync_requested` naming, and
6. exported per-sensor reporting includes both `entry_{sensor}_local_margin` and `event_{sensor}_margin_proximity_score = entry_delta_global - event_{sensor}_local_deviation` (positive acceptable, negative violating).
7. notebook execution includes an integrated post-export validation stage for smoke and export-policy invariants.

This note documents the current canonical implementation choices while preserving the broader design discussion below.

---

## 1. Local deviation uses the wrong reference

### Current problem

The notebook currently calculates local deviation using the prior global average as the reference:

```python
local_deviation = current_sensor_value - prior_global_average
```

This computes:

\[
v_i(t) - \bar{x}(t_0)
\]

That is not the intended local deviation.

Each sensor must compare its current reading against **its own reading at the last synchronization**:

\[
\Delta v_i(t) = v_i(t) - v_i(t_0)
\]

### Why this matters

A sensor's synchronized value may differ substantially from the synchronized global average.

Example:

- Sensor A at synchronization: 20°C
- Global average at synchronization: 22°C
- Sensor A now: 22°C

Correct local deviation:

\[
22 - 20 = 2
\]

Current notebook calculation:

\[
22 - 22 = 0
\]

The current implementation can therefore suppress legitimate local deviations or create incorrect ones.

### Required change

Maintain a dictionary or equivalent structure containing the synchronized reference value for every sensor:

```python
sensor_reference_values = {
    sensor_name: synchronized_row[sensor_name]
    for sensor_name in sensor_columns
}
```

Calculate local deviation as:

```python
local_deviation = (
    current_sensor_value
    - sensor_reference_values[sensor_name]
)
```

Whenever a re-synchronization occurs, update every sensor's reference value to the current synchronized reading.

---

## 2. The trigger rule is mathematically incorrect

### Current problem

The notebook currently derives a trigger threshold using:

```python
threshold_minus_delta = threshold - prior_delta
trigger = current_sensor_value > threshold_minus_delta
```

Because:

\[
\delta = T_{\max} - \bar{x}(t_0)
\]

then:

\[
T_{\max} - \delta
=
T_{\max} - (T_{\max} - \bar{x}(t_0))
=
\bar{x}(t_0)
\]

The current trigger rule therefore simplifies to:

\[
v_i(t) > \bar{x}(t_0)
\]

In plain language, the script triggers whenever a sensor exceeds the previous global average. That is not the distributed monitoring rule.

### Correct trigger rule

Each sensor should compare its warming local deviation against its assigned local margin:

\[
\Delta v_i(t) \geq m_i
\]

For the initial equal-constraint implementation:

\[
m_i = m_{\text{global}}
\]

for every sensor.

### Required change

Replace the current trigger logic with:

```python
local_deviation = (
    current_sensor_value
    - sensor_reference_values[sensor_name]
)

local_violation = (
    local_deviation
    >= local_margin_values[sensor_name]
)
```

If all sensors use the same local allowance:

```python
local_margin_values = {
    sensor_name: global_delta
    for sensor_name in sensor_columns
}
```

A local violation means that the mathematical guarantee can no longer be established from local information alone. It does **not** automatically mean the global temperature threshold has been violated.

---

## 3. The script does not maintain per-sensor synchronized states

### Current problem

The notebook maintains global state such as:

```python
prior_global_average
prior_delta
```

but it does not maintain the synchronized reference reading for each sensor.

A correct implementation requires both global and per-sensor state.

### Required synchronized state

At minimum, maintain:

```python
reference_global_average
global_delta
sensor_reference_values
local_margin_values
```

Conceptually:

- `reference_global_average`: the global average at the most recent synchronization,
- `global_delta`: distance from that average to the global threshold,
- `sensor_reference_values[sensor]`: the reading of each sensor at the most recent synchronization,
- `local_margin_values[sensor]`: the local margin assigned to each sensor.

### Re-synchronization update

When a re-synchronization occurs:

```python
reference_global_average = current_global_average

sensor_reference_values = {
    sensor_name: current_row[sensor_name]
    for sensor_name in sensor_columns
}

global_delta = threshold - reference_global_average

local_margin_values = {
    sensor_name: global_delta
    for sensor_name in sensor_columns
}
```

This update must occur only when the re-synchronization is actually completed.

---

## 4. Negative delta must trigger a re-synchronization in the next minute

### Definition

The global margin is:

\[
\delta = T_{\max} - \bar{x}(t_0)
\]

A negative delta means:

\[
\bar{x}(t_0) > T_{\max}
\]

The synchronized global state is already outside the feasible region.

### Required behavior

Every minute in which the calculated delta is negative should schedule a re-synchronization for the **next minute**.

This requires a pending-state flag rather than an immediate same-row update.

### Suggested state variable

```python
resync_due_next_minute = False
```

### Suggested sequence

At minute \(t\):

1. Evaluate whether a re-synchronization was already scheduled from minute \(t-1\).
2. If scheduled, perform the re-synchronization using the current minute's readings.
3. Recalculate the global average and delta.
4. If the newly calculated delta is negative, set:

```python
resync_due_next_minute = True
```

5. Otherwise:

```python
resync_due_next_minute = False
```

### Important implication

If delta remains negative after each re-synchronization, the system will continue to schedule another re-synchronization for the following minute.

This behavior should be logged explicitly, for example:

```python
negative_delta_detected
resync_scheduled_for_next_minute
resync_reason
```

Suggested values for `resync_reason`:

- `local_constraint_violation`
- `negative_delta_from_prior_minute`
- `initial_sync`
- `manual_or_quality_control`

### Recommended rule

Use the unrounded delta for logic:

```python
global_delta_raw = threshold - reference_global_average
```

Use rounded values only for display.

---

## 5. The threshold boundary is inconsistent

### Current problem

The monitoring condition is defined as:

\[
g(t) > 0
\]

For temperature:

\[
g(t) = T_{\max} - x(t)
\]

Therefore, the system is safe only when:

\[
x(t) < T_{\max}
\]

A violation occurs when:

\[
x(t) \geq T_{\max}
\]

The notebook currently uses a strict greater-than comparison in some places:

```python
current_global_average > threshold
```

This treats equality as safe, which conflicts with the stated feasible-region definition.

### Required change

Use:

```python
global_violation = current_global_average >= threshold
```

Likewise, if local safety requires warming-only margin checks:

\[
\Delta v_i(t) < m_i
\]

then a local violation occurs at equality:

```python
local_violation = local_deviation >= local_margin
```

### Consistency requirement

Use the same boundary convention throughout:

- safe: `<`
- violated: `>=`

This must be applied consistently to:

- global threshold evaluation,
- local constraint evaluation,
- negative or zero delta handling,
- metrics and labels,
- event logs.

---

## 6. Communication calculations substantially undercount messages

### Current problem

The notebook currently counts only the sensors that trigger a re-synchronization.

That omits the additional communication required to complete the re-synchronization.

### Agreed communication-counting rule

For each full re-synchronization, count the following categories separately.

#### 1. Trigger messages

One message from each triggering sensor to the root:

\[
M_{\text{trigger}} = \text{number of triggering sensors}
\]

#### 2. Request messages

Here \(n\) means currently online sensors, not the configured cohort. The root
sends one request to each online sensor; offline status detection requires no
notification and offline sensors receive no traffic:

\[
M_{\text{request}} = n
\]

#### 3. Response messages

Each sensor sends its current value to the root:

\[
M_{\text{response}} = n
\]

#### 4. Broadcast messages

The root sends the updated reference state, delta, or local constraint information to each sensor:

\[
M_{\text{broadcast}} = n
\]

#### 5. Total messages

\[
M_{\text{total}}
=
M_{\text{trigger}}
+
M_{\text{request}}
+
M_{\text{response}}
+
M_{\text{broadcast}}
\]

or:

\[
M_{\text{total}}
=
M_{\text{trigger}} + 3n
\]

for a normal full re-synchronization.

### Transparency requirement

Store each category separately in the output:

```python
trigger_message_count
request_message_count
response_message_count
broadcast_message_count
total_message_count
```

### Re-synchronization caused by negative delta

When a negative delta schedules a re-synchronization for the next minute, the re-synchronization may not have a new sensor trigger message.

When that scheduled event is consumed on the next row, treat it as a forced synchronization row:

1. Perform synchronization immediately from the current snapshot.
2. Do not evaluate local trigger conditions against the prior entry margins on that row.
3. Set all per-sensor local trigger bits to `0` for that row.
4. Keep trigger message count at `0`; count only request/response/broadcast fanout.

For that event:

```python
trigger_message_count = 0
request_message_count = n
response_message_count = n
broadcast_message_count = n
total_message_count = 3 * n
```

The cause should be logged as:

```python
resync_reason = "negative_delta_from_prior_row"
```

### Multiple triggering sensors

If multiple sensors violate their local constraints during the same minute:

```python
trigger_message_count = number_of_triggering_sensors
```

Only one full re-synchronization should occur for that minute unless the implementation explicitly models separate asynchronous events.

### Initial synchronization

The initial synchronization should be counted separately from later distributed monitoring events.

Implemented fields (initialization traffic is included once in the normal
request/response/update totals, with a separate attribution view):

```python
event_initialization_performed
initialization_message_count
```

This prevents the initial setup cost from being confused with ongoing monitoring costs.

---

## Recommended state-machine order

For each minute, process events in the following order:

1. Load the aligned sensor readings for the current minute.
2. Check whether a re-synchronization was scheduled from the prior minute.
3. If scheduled:
   - count request messages,
   - count response messages,
   - compute the current global average,
   - update every sensor's synchronized reference value,
   - calculate the new global delta,
   - assign local delta values,
   - count broadcast messages.
4. If no scheduled re-synchronization:
   - calculate each sensor's local deviation,
   - compare each deviation with its local delta,
   - record triggering sensors.
5. If one or more sensors trigger:
   - count trigger messages,
   - perform one full re-synchronization,
   - count requests, responses, and broadcasts separately.
6. After any synchronization:
   - evaluate the new raw delta,
   - if delta is negative, schedule another re-synchronization for the next minute.
7. Record all state values and message counts for that minute.
8. Move to the next minute.

---

## Recommended output fields

The event-level output should include at least:

```text
timestamp
transition_summary
entry_xbar_t0
observed_global_average
entry_delta_global
exit_delta_global
global_violation
event_exit_delta_negative
event_resync_consumed_from_prior_row
exit_resync_scheduled_next_row
event_resync_performed
event_resync_reason
event_resync_request_count
event_triggering_sensor_names
trigger_message_count
request_message_count
response_message_count
broadcast_message_count
total_message_count
```

For each sensor, retain:

```text
observed_sensor_temperature
entry_sensor_reference_value
event_sensor_local_deviation
entry_sensor_local_margin
event_sensor_resync_requested
```

Row invariant for the active implementation:

```text
entry_*   = state used to evaluate the current row
observed_* = raw values for the current minute bucket
event_*   = outcomes produced during the current minute
exit_*    = state committed at row end and applied on the next row
```

---

## Acceptance checks

The corrected implementation should pass the following checks.

### Local deviation

For every sensor:

\[
\Delta v_i(t)
=
v_i(t)-v_i(t_0)
\]

where \(v_i(t_0)\) is that sensor's value at the most recent synchronization.

### Trigger rule

A sensor triggers exactly when:

\[
\Delta v_i(t) \geq m_i
\]

### Re-synchronization state

After a re-synchronization:

- the global reference average equals the current global average,
- every sensor reference equals its current value,
- delta is recalculated from the new global reference,
- local allowances are reassigned.

### Negative delta

If delta is negative at minute \(t\):

- a re-synchronization is scheduled for minute \(t+1\),
- the next-minute event is logged,
- requests, responses, and broadcasts are counted separately.

### Threshold boundary

- safe global state: `global_average < threshold`
- global violation: `global_average >= threshold`
- safe local state: `local_deviation < local_margin`
- local violation: `local_deviation >= local_margin`

### Communication accounting

For every ordinary full re-synchronization:

```text
total_message_count
=
trigger_message_count
+ request_message_count
+ response_message_count
+ broadcast_message_count
```

with:

```text
request_message_count = n
response_message_count = n
broadcast_message_count = n
```

For rows where `event_resync_consumed_from_prior_row == 1`:

```text
trigger_message_count = 0
event_resync_request_count = 0
event_any_sensor_requested_resync = 0
event_resync_triggered_by_local_violation = 0
```

The corrected implementation should also enforce:

1. `event_resync_consumed_from_prior_row == 1` implies `trigger_message_count == 0`.
2. A row cannot represent the same synchronization as both forced and locally triggered unless separate modeled events are explicitly introduced.

---

## Priority order for implementation

1. Add per-sensor synchronized reference state.
2. Correct the local deviation calculation.
3. Replace the trigger rule.
4. Implement explicit re-synchronization state updates.
5. Add next-minute re-synchronization scheduling for negative delta.
6. Standardize all threshold boundaries.
7. Replace the communication metric with transparent category-level counts.
8. Add validation tests before rerunning project metrics.

Until these changes are completed, the notebook's monitoring and communication-reduction results should not be treated as valid evidence of the intended distributed monitoring algorithm.


<!-- US-0.02 ORIGINAL SOURCE END: Writing/Markdowns/distributed_monitoring_notebook_required_changes.md -->


<a id="phase-3a-pivot-record"></a>

### Phase 3A pivot record

Original source: `Phase3A_Pivot_Plan.md`. The following is a historical record, not current requirements.

<!-- US-0.02 ORIGINAL SOURCE START: Phase3A_Pivot_Plan.md -->

# Phase 3A Pivot Plan
## Distributed Monitoring POC — Stable-Cohort FMIC/SMIC Experiment

**Status:** Sponsor-approved project pivot  
**Date:** 2026-11-01  
**Purpose:** Simplify Phase 3 so that the primary FMIC/SMIC experiment is methodologically defensible, computationally manageable, and understandable by a part-time product manager using AI-assisted coding.

**Implementation record updated:** 2026-11-03 — completed work through US-3.22 is documented in Section 22.

**Policy follow-up (2026-11-10):** US-3.23 revised Phase 2 to the two-sided
equal-allowance policy. Its separately named baseline and validation are recorded
in Section 22.12; US-3.22 results and denominators remain unchanged historical evidence.

---

## 1. Why This Pivot Is Being Made

The original Phase 3 implementation became substantially more complex than necessary for the core research question. The implementation added dynamic sensor availability, re-entry handling, changing eligible sets, extensive audit traces, exhaustive clustering-search records, and other state-management requirements before FMIC or SMIC had been implemented end-to-end.

This complexity produced artifacts that were difficult to inspect and manage. In particular, Phase 3 output grew to multiple gigabytes even though the validated Phase 2 output was less than 100 MB.

The project will therefore simplify the primary Phase 3 experiment while preserving the source-defined clustering methodology.

The primary research question remains:

> **Can source-aligned FMIC and SMIC clustering reduce communication relative to the Phase 2 distributed-monitoring approach while preserving correct monitoring of the global temperature threshold?**

The pivot is intended to keep implementation effort focused on that question.

---

## 2. Governing Rule During the Pivot

This document records the approved Phase 3A design decisions.

For the **primary Phase 3A experiment**, if this document conflicts with the existing `Phase_3_User_Stories.md` or the current `Distributed_Monitoring_POC_Project_Plan.md`, this pivot plan governs until those documents are updated.

The original Phase 3 user stories remain part of the project history and should not be rewritten retroactively. New user stories will be added to implement the approved pivot.

The definitive methodology source remains:

`140516editor Book Chapter (Last Version).pdf`  
*Clustering for Monitoring Distributed Data Streams*

The source chapter continues to govern the mathematical definitions for history, normalization, partition quality, greedy clustering, FMIC, SMIC, and source-comparable communication accounting.

---

## 3. Phase 3A and Phase 3B

Phase 3 is now divided into two conceptual tracks.

### Phase 3A — Primary Experiment

Phase 3A is the required project path.

It evaluates Phase 2, FMIC, and SMIC using a fixed set of continuously observed sensors over a continuous time interval with no missing selected-sensor observations.

This is the experiment that must be completed before any optional robustness work is considered.

### Phase 3B — Optional Availability Robustness Extension

Phase 3B is optional and is not part of the Phase 3A critical path.

It may later evaluate the algorithms using the broader dataset with sensors going online and offline, changing observed contributors, re-entry synchronization, changing coordinator assignments, and other availability-related behaviors.

The availability-aware work already implemented is not considered wasted, but it is no longer required before FMIC and SMIC can be implemented and evaluated.

---

## 4. Locked Phase 3A Experimental Cohort

The primary Phase 3A experiment will use the following six sensors:

- A
- C
- D
- E
- F
- G

Sensors B and H are excluded from the primary Phase 3A cohort.

The selected interval is:

- **Start:** `2022-02-24T18:50:00+00:00`
- **End:** `2022-03-10T15:53:00+00:00`
- **Expected one-minute buckets:** `19,984`

Every selected sensor has a valid observation in every included bucket.

The interval is strictly continuous at one-minute resolution: both endpoints are inclusive, and every adjacent timestamp must differ by exactly 60 seconds. With inclusive endpoints, 19,984 buckets span 19,983 elapsed minutes.

No sensor-value imputation is permitted.

The Phase 3A implementation must validate these conditions before running. Validation must include the expected cohort, inclusive interval endpoints, exact 19,984-bucket row count, complete selected-sensor observations, and exact 60-second spacing between every adjacent timestamp. If any requirement is not satisfied, the run should fail rather than fall back to dynamic availability handling.

---

## 5. Phase 1 Changes

The existing Phase 1 transformation logic remains unchanged.

Phase 1 will continue to produce the full aligned temperature dataset.

A small addition will be made to the Phase 1 statistics output so that `phase1_average_statistics.csv` includes a row representing the Phase 3A stable cohort and interval.

The Phase 3A threshold will be calculated from the six-sensor average over the approved Phase 3A interval.

The approximate p90 value identified during planning is:

`22.42866665 °C`

The implementation should calculate and record the value programmatically rather than rely on a manually entered approximation.

The new statistics row should have a clear series identifier such as:

`phase3a_stable_cohort`

The existing full-data Phase 1 statistics must be preserved.

---

## 6. Phase 2 Baseline for Phase 3A

The current Phase 2 monitoring implementation will be reused rather than rewritten.

A new matched Phase 2 run will be produced using exactly:

- sensors A, C, D, E, F, and G;
- the approved Phase 3A time interval;
- the Phase 3A-specific p90 threshold;
- the existing Phase 2 boundary and synchronization conventions.

Because every selected sensor is present on every included row, membership-change behavior should never activate in this run.

If membership-change behavior occurs, the stable-cohort input or filtering logic should be treated as incorrect.

The existing full-data Phase 2 output remains a valid historical artifact, but it will not be used as the primary comparator for Phase 3A.

The required primary comparison is:

**Stable-cohort Phase 2 vs. Stable-cohort FMIC vs. Stable-cohort SMIC**

All three must use the same observations, timestamps, cohort, threshold, boundary convention, and communication-counting definitions.

---

## 7. Existing Phase 3 Work to Preserve

The project will pivot from the existing Phase 3 implementation rather than start over.

The source-aligned mathematical work already implemented through the current clustering foundation should be preserved unless testing shows that it is incorrect.

The following core behavior remains required:

1. persistent per-sensor history;
2. signed deviation from the active synchronization reference;
3. history retained across synchronization rather than reset;
4. signed normalization using the maximum history magnitude;
5. deterministic handling of the initial all-zero-history condition;
6. source-aligned cluster quality and partition quality;
7. signed cancellation within clusters;
8. source-aligned greedy merging and partition selection.

The mathematical core should not be simplified merely to reduce coding effort.

The implementation and output infrastructure surrounding that core may be simplified substantially.

---

## 8. Phase 3A Complexity to Remove

Phase 3A should remove implementation logic that exists only to support changing sensor availability.

The primary Phase 3A execution path does not need:

- sensor departure handling;
- sensor return or re-entry handling;
- changing eligible-sensor sets;
- offline-sensor history suspension;
- stale pre-return reference protection;
- zero-observation global states;
- changing observed denominators;
- membership-triggered synchronization;
- membership-related cause attribution;
- coordinator changes caused by sensor availability;
- deferred synchronization waiting for sensors to return.

These behaviors may remain relevant to optional Phase 3B, but they should not complicate the Phase 3A implementation.

A new user story will explicitly govern removal of unnecessary Phase 3A complexity rather than merely leaving unused branches in place.

---

## 9. History and Normalization Under Phase 3A

Phase 3A keeps the source-defined history rule.

For sensor `i`, with active synchronization reference `v_i(t_j)`, history is updated from valid observations as:

`h_i <- 0.5 * h_i + [v_i(t) - v_i(t_j)]`

The deviation remains signed.

History persists across synchronization events. Synchronization changes the reference used for future updates but does not reset accumulated history.

Because the Phase 3A cohort is stable, every clustering event uses the same six sensors.

For scalar temperature histories:

`H = max_i |h_i|`

and, when `H > 0`:

`a_i = h_i / H`

Normalization must preserve sign and must not overwrite raw accumulated history.

The initial all-zero-history condition remains a valid edge case and should use the previously agreed deterministic fallback.

---

## 10. Clustering Logic to Preserve

The current source-aligned clustering mathematics remains in scope.

For cluster `pi`:

`q(pi) = (1 / |pi|) * |sum(a_i)| + alpha * |pi|`

For partition `Pi`:

`Q(Pi) = max q(pi)`

The implementation must preserve signed cancellation by summing signed normalized histories before taking the absolute value.

The greedy merge procedure remains source-aligned:

1. begin with singleton clusters;
2. identify the current worst-quality cluster;
3. merge it with the partner producing the smallest merged-cluster quality;
4. retain candidate partitions;
5. stop at two clusters when applicable;
6. select the retained partition having minimum partition quality.

Existing deterministic project tie rules may remain unless a simpler source-consistent rule is explicitly approved later.

---

## 11. Production Output Simplification

Phase 3A production outputs should contain only information required to understand and reproduce the experiment.

The project will no longer require persistence of every deterministic intermediate calculation.

### Remove from normal full-data output

Do not persist:

- one sensor-history row for every sensor for every minute;
- every rejected merge candidate;
- every merge-partner score;
- every intermediate partition quality for every candidate;
- exhaustive JSON representations of the full clustering search path for every synchronization and alpha;
- detailed availability audit fields that cannot occur in Phase 3A.

### Retain at clustering events

At a minimum, retain:

- event/synchronization identifier;
- timestamp;
- algorithm;
- alpha;
- raw sensor histories used for clustering;
- normalized histories;
- selected partition;
- selected partition quality;
- cluster count;
- coordinator assignments.

Detailed traces may be generated in an explicit debug mode for synthetic tests or small samples, but they are not normal project deliverables.

---

## 12. FMIC and SMIC Implementation Strategy

FMIC will be implemented first as the first complete Phase 3A clustering-monitoring algorithm.

FMIC must use the source-defined first-moment weighting and allowance calculations.

After FMIC is validated end-to-end, SMIC will be added using the same monitoring architecture.

FMIC and SMIC must not become separate implementations of the monitoring lifecycle.

They should share:

- source observations;
- history handling;
- normalization;
- clustering;
- synchronization timing;
- coordinator behavior;
- communication accounting;
- output generation;
- correctness tests where the behavior is common.

The main algorithm-specific difference should be the weighting/allowance calculation.

SMIC adds the source-defined conservative second-moment component to the first-moment approach.

---

## 13. Alpha Policy

Alpha is treated as a clustering tuning parameter for this dataset, not as a primary research question or a generally transferable scientific result.

Initial implementation and correctness testing should use a single baseline value, such as:

`alpha = 0.10`

The full alpha sweep should occur only after FMIC and SMIC each operate correctly end-to-end.

A coarse sweep of:

`0.05, 0.10, 0.15, ..., 0.95`

may then be used to identify a reasonable dataset-specific setting.

The alpha tuning output should remain small. At minimum it needs:

- algorithm;
- alpha;
- total communication;
- correctness-pass status.

Additional compact metrics such as root synchronizations or cluster count may be retained if useful.

The project does not need to preserve the complete internal clustering search path for every alpha.

The selected alpha should not be presented as a universal optimum.

---

## 14. Communication Accounting

Transparent communication accounting remains required.

Phase 3A should separately count genuine transmission types needed to compare the methods, including as applicable:

- node/local-trigger messages;
- cluster collection/check requests;
- cluster collection/check responses;
- coordinator-to-root escalation messages;
- root synchronization requests;
- synchronization responses;
- synchronization broadcasts/constraint updates;
- total messages.

Requests and responses remain separate transmissions.

Message categories must reconcile to total communication.

Phase 3A does not require membership-change communication categories because membership does not change during the primary experiment.

---

## 15. Correctness Testing Philosophy

Correctness will be demonstrated primarily through focused synthetic and hand-calculated tests rather than by retaining every full-run intermediate state.

The required test suite should include, at minimum:

### History Test

Verify the history recurrence against hand calculations across multiple observations and synchronization intervals.

**Purpose:** confirm that history uses the active synchronization reference, preserves sign, discounts older history correctly, survives synchronization, and uses the new reference afterward.

### Normalization Test

Verify signed normalization against hand-calculated histories, including positive values, negative values, zeros, and the all-zero case.

**Purpose:** confirm that normalization scales histories without destroying direction or modifying raw history.

### Clustering Test

Use a small hand-calculated set of normalized histories and verify cluster quality, partition quality, greedy merge choices, retained candidates, and final selected partition.

**Purpose:** confirm that implementation matches the source clustering algorithm rather than merely producing plausible clusters.

### FMIC Weight and Allowance Test

Hand-calculate first-moment weights, node allowances, and coordinator allowances.

**Purpose:** establish formula-level agreement before communication results are interpreted.

### SMIC Weight and Allowance Test

Hand-calculate the required first moment, second moment, conservative second-moment component, and resulting allowances.

**Purpose:** prove that SMIC differs from FMIC only in the intended source-defined calculation.

### Safe Cancellation Test

Construct a case where one node warms and another cools enough that cluster cancellation keeps the monitored global condition safe.

**Expected behavior:** the local event is recognized, but unnecessary root escalation may be avoided.

### Unsafe Partial-Cancellation Test

Construct a case where cooling does not offset warming enough to preserve the global condition.

**Expected behavior:** coordinator/root escalation occurs and the global violation is not concealed.

### Boundary Test

Test values immediately below, exactly at, and immediately above node, coordinator, and global boundaries.

**Purpose:** prove consistent application of the declared `<` versus `>=` convention.

### Communication Accounting Test

Use a small 2–4 sensor example and manually count every expected transmission.

**Purpose:** prove that requests, responses, triggers, escalations, and broadcasts are neither omitted nor double-counted.

Availability/offline tests are not required for Phase 3A and may be retained for optional Phase 3B.

---

## 16. Reproducibility Standard

Phase 3A replaces exhaustive audit retention with a reproducibility requirement.

A researcher should be able to reproduce the reported results using:

- the original Phase 1 aligned data;
- the Phase 3A experiment configuration;
- the Phase 3A threshold statistics row;
- the implementation notebooks/code;
- the deterministic algorithm definitions;
- the focused correctness tests;
- the compact clustering-event and results artifacts.

The project does not need to permanently store every intermediate state that can be deterministically recomputed.

---

## 17. Target Phase 3A Artifacts

The normal Phase 3A deliverable set should remain small.

Target artifacts are:

1. The `phase3a_experiment` section of `config/project_config.yaml`
2. `phase3a_cluster_events.csv`
3. `phase3a_results.csv`
4. Phase 3A synthetic/unit-test results

The exact filenames may change during implementation if a simpler organization is justified, but the project should avoid unnecessary duplicate outputs.

`phase3a_results.csv` should be capable of supporting the primary Phase 2/FM​IC/SMIC comparison and compact alpha tuning results.

Detailed debug traces are optional and should not be produced by default.

---

## 18. Primary Final Comparison

The primary Phase 3A result will compare:

1. Stable-cohort Phase 2
2. Stable-cohort FMIC
3. Stable-cohort SMIC

All three must use:

- sensors A, C, D, E, F, and G;
- the approved 19,984-bucket continuous interval;
- the same Phase 3A p90 threshold;
- identical input observations;
- identical boundary conventions;
- consistent synchronization timing;
- consistent communication-counting rules.

The primary outcome is whether clustering reduces communication while preserving correct monitoring behavior.

---

## 19. Phase 3A Scope Limitation

Phase 3A evaluates FMIC and SMIC under stable node participation.

It does not establish how the algorithms perform when sensors repeatedly disappear and return.

That question is reserved for optional Phase 3B.

Final reporting should state this limitation explicitly rather than implying that Phase 3A represents all operational sensor-network conditions.

---

## 20. Documentation and User-Story Strategy

The project will not retroactively rewrite the existing Phase 3 user stories that drove the current implementation.

Instead:

1. this pivot plan records the approved redesign;
2. `Distributed_Monitoring_POC_Project_Plan.md` will be updated to incorporate Phase 3A and optional Phase 3B;
3. new user stories will be added after the existing sequence to implement the pivot;
4. those new stories will explicitly supersede conflicting prior requirements for the Phase 3A path.

The next planned implementation stories are expected to address, in sequence:

- simplifying the existing Phase 3 implementation for stable-cohort operation;
- establishing and validating the Phase 3A input contract;
- producing the matched stable-cohort Phase 2 baseline;
- implementing FMIC end-to-end;
- implementing SMIC through shared monitoring logic;
- validating Phase 3A with focused synthetic tests;
- tuning alpha and producing the final Phase 3A comparison.

The exact story numbering and acceptance criteria will be defined separately so that each coding task remains limited in scope and manageable for AI-assisted implementation.

---

## 21. Definition of Success for the Pivot

The Phase 3A pivot is successful when:

1. the primary experiment operates on the approved six-sensor stable interval;
2. the Phase 3A-specific p90 is reproducibly calculated and documented;
3. the matched Phase 2 baseline is rerun on the same experimental population;
4. unnecessary availability-related complexity is removed from the Phase 3A implementation path;
5. Phase 3 production outputs are small enough to inspect and manage directly;
6. source-aligned history, normalization, clustering, FMIC, and SMIC formulas pass focused correctness tests;
7. FMIC and SMIC use one shared monitoring architecture;
8. alpha is treated as dataset-specific tuning rather than the central research question;
9. communication accounting remains transparent and reconciled;
10. the final Phase 2/FM​IC/SMIC comparison is understandable without reconstructing gigabytes of intermediate state.

---

## 22. Implementation Record — Decisions and Completed Milestones Through US-3.22

**Recorded as of:** 2026-11-03  
**Status:** Work through US-3.22 has been implemented and reviewed. The US-3.21 correctness gate passed before the full alpha sweep; the sweep and final comparison passed validation.

This section describes what the project actually did after the original pivot was approved. Sections 1–21 above remain the approved plan and describe the intended approach. This section is the implementation history; where a later, documented implementation decision is more specific than the original plan, it explains the difference.

### 22.1 Main decisions made during implementation

**Focus the required experiment on six continuously reporting sensors.** We kept sensors **A, C, D, E, F, and G** and excluded B and H from Phase 3A. The selected period runs from **2022-02-24 18:50 UTC** through **2022-03-10 15:53 UTC**, inclusive. It contains exactly **19,984 one-minute observations** per selected sensor. This removes missing-data and sensor-return decisions from the main comparison. Testing changing sensor availability remains a possible Phase 3B activity, not a prerequisite.

**Keep the source mathematics while reducing software and output complexity.** We reused the existing history, normalization, and greedy clustering approach. We removed availability-driven paths from the normal Phase 3A work and stopped treating detailed per-minute histories and exhaustive merge records as required production outputs. Short synthetic tests and compact event records provide the evidence needed to understand the results.

**Use one matched set of experimental conditions.** Phase 2, FMIC, and SMIC use the same six sensors, timestamps, temperature readings, threshold, and global decision boundary: **safe when the mean is below p90; violated when the mean is at or above p90**. The p90 value is calculated from the selected cohort rather than borrowed from the broader eight-sensor data.

**Use consistent, explicit message counts.** For the primary comparison, the simulation uses **six sensor nodes and a separate root component**. Cluster coordinators are selected from the sensors. Messages to oneself cost zero; a request and its response count as two transmissions. We count local triggers, cluster requests, cluster responses, coordinator escalations, root requests, root responses, and root state updates separately. This network arrangement is a **documented project adaptation**: the chapter's own broadcast examples sometimes use a sensor as the root. A chapter-style count must not be substituted for the project's actual-transmission total.

**Monitor the threshold from both sides.** At each root synchronization, the root stores whether the global mean is currently safe or violated. The next monitoring allowance is based on the **absolute distance from that mean to the threshold**. A mean above p90 is not automatically a reason to synchronize again. The nodes and coordinators must detect changes that could cross the threshold in either direction and bring them to the root. At exactly p90, the state is violated and the allowance is zero. We did not copy Phase 2's negative-margin forced-synchronization schedule into FMIC or SMIC.

**Implement FMIC before SMIC, using one shared engine.** FMIC first established a working local-trigger, coordinator-check, root-update, and clustering lifecycle. SMIC then added the second-moment calculation and selected a different weight formula in that same engine. It did not introduce a separate coordinator or synchronization implementation.

**Run alpha sensitivity only after validation.** The initial production comparison used **alpha = 0.10**. After the US-3.21 validation gate passed, US-3.22 completed the 19-value end-to-end sweep for both methods. Any minimum is reported only as a dataset- and grid-specific observation, not as a universal optimum.

### 22.2 US-3.16 — Simplify Phase 3 for stable-cohort operation

**What was done**

1. We retained the existing Phase 3 clustering foundation rather than starting over. The same notebook now contains stable-cohort input preparation, persistent sensor histories, signed normalization, and deterministic cluster selection.
2. We narrowed the normal execution path to the fixed six-sensor set. Sensor departures, returns, changing denominators, and membership-based resynchronizations are not part of the Phase 3A simulation.
3. We preserved the signed history update: each minute contributes the difference between the current reading and that sensor's active synchronization reference, while earlier history is discounted by a factor of 0.5. History is **not reset** when a root synchronization occurs; the synchronization only changes the reference for later minutes.
4. We kept normalization by the largest absolute sensor history while preserving each history's sign, including a deterministic fallback for an all-zero history vector.
5. We kept the greedy clustering procedure: start with individual sensors, merge according to cluster quality, evaluate retained candidate partitions, and select the partition with the lowest maximum cluster quality. We retained deterministic rules so the same inputs produce the same clusters.
6. We reduced normal output to compact synchronization/clustering records instead of writing the full internal clustering search and every sensor's history on every minute. Detailed checks remain appropriate for short synthetic examples.

**Milestone achieved:** A simpler Phase 3A foundation that can be reused by both monitoring algorithms without changing the source-based clustering rules. This foundation is exercised by the subsequent FMIC and SMIC runs.

### 22.3 US-3.17 — Establish and validate the fixed experiment input

**What was done**

1. We locked the cohort to **A, C, D, E, F, G** and the inclusive time interval **2022-02-24 18:50 UTC–2022-03-10 15:53 UTC**.
2. We established a Phase 3A configuration file to record the selected sensors, input dataset, timestamps, expected row count, one-minute sampling interval, alpha, threshold source, and decision boundary.
3. We added input checks that reject missing or unexpected sensor columns, missing/nonfinite readings, duplicate or out-of-order timestamps, incorrect endpoints, and any gap other than exactly 60 seconds.
4. We made invalid input stop the run instead of quietly filling gaps or switching back to the changing-availability logic.
5. We fixed **alpha = 0.10** for initial implementation. The threshold was identified by its authoritative Phase 1 statistics row, rather than treating an approximate manually entered p90 as final.

**Milestone achieved:** A repeatable, validated input contract for **19,984 complete one-minute buckets** with no imputation. FMIC and SMIC use this same contract.

### 22.4 US-3.18 — Calculate the cohort-specific p90 and matched Phase 2 baseline

**What was done**

1. We extended the **production Phase 1 statistics calculation** to compute the average temperature of the six selected sensors at each of the 19,984 timestamps and then calculate that series' 90th percentile.
2. We added a separate `phase3a_stable_cohort` row to `phase1_average_statistics.csv`, preserving the preexisting full-data statistics. The authoritative threshold is **22.428666649999997 °C**. The original full-data p90, about **24.343381 °C**, is **not** the Phase 3A cutoff.
3. We linked the experiment configuration to this exact statistics row and made subsequent monitoring runs check that the configured threshold matches the recorded value.
4. We reused the existing Phase 2 monitoring method on the same six sensors, interval, and new p90. This is a new matched comparator, not a comparison to the earlier full-data/eight-sensor Phase 2 run.
5. We recorded the matched baseline in `phase3a_phase2_baseline.json`, including message totals, synchronization counts, global threshold violations, and the no-membership-change result.
6. During related Phase 1 quality-control work, we found that an aggregate file named `temperature_raw.csv` was being read along with source CSV files. The source-file discovery rule was changed to exclude this aggregate. The recorded duplicate-key rate then fell from **50.050912%** to **0.101823%**, below the **0.5%** quality gate. This was a data-input correction, **not a change to the FMIC or SMIC monitoring formulas**.

**Observed matched Phase 2 result**

| Measure | Value |
|---|---:|
| One-minute buckets evaluated | 19,984 |
| Total messages | 38,087 |
| Local trigger messages | 161 |
| Root requests | 12,642 |
| Root responses | 12,642 |
| Root updates/broadcasts | 12,642 |
| Resynchronizations | 2,107 |
| Minutes with global mean at or above p90 | 1,999 |
| Membership-change events | 0 |
| Centralized reference: 6 sensor messages each minute | 119,904 |

The message categories add up to **38,087**. The baseline reports a passed correctness check. The p90 and 19,984-row cohort are now the common basis for all subsequent Phase 3A comparisons.

**Milestone achieved:** A defensible, like-for-like Phase 2 comparison point with documented data and threshold provenance.

### 22.5 US-3.19 — Implement and review FMIC end to end

**What was done**

1. We implemented the **first-moment method** in the Phase 3 notebook and traced its mathematical definition to the original chapter PDF after discovering that some formulas were damaged in the extracted text.
2. For each sensor, we maintain a discounted sum of its post-initialization readings. A new reading is added to half of the previous discounted sum. The sum is divided by the number of processed post-initialization readings to get that sensor's first moment. This state is separate from the signed history used for clustering and is not reset at synchronization.
3. The FMIC weight for each scalar temperature sensor is the **absolute value of its first moment**. We scale weights so their total equals the number of sensors, then multiply each scaled weight by the current root allowance to obtain the sensor's allowance. A coordinator's allowance is the average of its cluster members' allowances.
4. We made the all-zero-weight case explicit. When every weight is zero, every sensor receives equal scaled weight **1**. This is a **project-defined fallback**, not a formula claimed to come directly from the chapter. An individual zero weight remains zero if other weights are nonzero.
5. We implemented the full monitoring sequence: sensors check their local allowance; triggered sensors report to the cluster coordinator; the coordinator evaluates the cluster and collects additional sensor values as needed; an unresolved cluster check escalates to the root; the root collects the current sensor readings, records the global threshold state, recalculates constraints, and reclusters.
6. The root uses the two-sided threshold policy described in Section 22.1. A root synchronization is driven by FMIC's own monitoring events, **not by replaying Phase 2's synchronization times**. Updated references and allowances apply to subsequent observations.
7. We recorded each message category separately, including the root collection and state-update messages. Communication between a coordinator and itself is not counted as a network transmission.
8. We added hand-calculated tests for first moments, node and coordinator allowances, zero weights, signed cancellation, root escalation, threshold boundaries, persistent history, and message counting. During review, the correctness summary was tightened to require **both** zero false-safe and zero false-violated states. Source references and a hand-calculated example were added to explain the first-moment recurrence.
9. We wrote a compact synchronization-event file and summary rather than an all-minute sensor-history dump. The FMIC file has **293 events**, one per root synchronization.

**Observed FMIC result at alpha = 0.10**

| Measure | Value |
|---|---:|
| Total messages | 11,922 |
| Root synchronizations, including initialization | 293 |
| Monitoring-triggered root synchronizations | 292 |
| Node triggers (events, not transmitted messages) | 3,689 |
| Coordinator checks | 3,522 |
| Coordinator-to-root escalations | 420 |
| Minutes with global mean at or above p90 | 1,999 |
| False-safe / false-violated minutes | 0 / 0 |
| Reported reduction relative to matched Phase 2 | 68.70% |

The **11,922** messages consist of **2,564 node-trigger transmissions; 1,832 cluster requests; 1,832 cluster responses; 420 coordinator-to-root escalations; 1,758 root requests; 1,758 root responses; and 1,758 root state updates**. The categories reconcile and the summary reports correctness `passed`.

**Milestone achieved:** A complete, independently scheduled FMIC simulation with compact event output and an initial, successful comparison against matched Phase 2. The reported results were reviewed for internal consistency; a later comprehensive validation stage remains planned.

### 22.6 US-3.20 — Add SMIC to the shared FMIC monitoring engine

**What was done**

1. We implemented the source-based **second-moment** calculation while preserving FMIC's first-moment calculation. The original chapter and its appendix were used to clarify the mathematical symbols, including the fact that the second moment is an **unnormalized sum of squared deviations** of the discounted observations, not an ordinary sample variance.
2. We used the running calculation documented by the implementation: if `S2` is the stored second moment, a new observation updates it using `0.25 * old_S2 + (m-1)/m * (reading - 0.5 * previous_first_moment)^2`, with `m` representing the number of observations after the new reading. The implementation includes handling for the first observation, invalid values, and all-zero weights.
3. We calculated SMIC's scalar sensor weights as **absolute first moment plus the conservative second-moment term**, `sqrt((m-1)/m * S2)`. The same shared weight-scaling, node-allowance, and coordinator-allowance calculations are then applied.
4. We **reused the FMIC monitoring class** (`FMICMonitor`) with a method setting of `FMIC` or `SMIC`. The two methods share the same sensors, history and clustering code, threshold policy, coordinator/root behavior, communication categories, and output conventions. The chosen moment/weight calculation is the intended difference.
5. We retained the project fallback of equal scaled weights when the total calculated weight is zero. Information about moments and weights travels with existing root synchronization responses and state updates; the simulation does not invent extra transmissions just because SMIC has more numerical fields.
6. We extended the synthetic tests with hand-calculated second moments, direct comparisons with explicit discounted observation sets, early-observation cases, zero/nonzero weights, allowance reconciliation, persistent moment states, exact message counts, threshold-crossing tests, and checks that identical allowances lead to identical monitoring decisions. Regression tests were added to guard against changing FMIC behavior.
7. We generated SMIC's own event and summary files. As with FMIC, these are compact root synchronization records rather than one detailed history row per sensor per minute.

**Observed SMIC result at alpha = 0.10**

| Measure | Value |
|---|---:|
| Total messages | 11,902 |
| Root synchronizations, including initialization | 293 |
| Monitoring-triggered root synchronizations | 292 |
| Node triggers | 3,680 |
| Coordinator checks | 3,514 |
| Coordinator-to-root escalations | 420 |
| Minutes with global mean at or above p90 | 1,999 |
| False-safe / false-violated minutes | 0 / 0 |
| Reported reduction relative to matched Phase 2 | 68.75% |

The **11,902** messages consist of **2,556 node-trigger transmissions; 1,826 cluster requests; 1,826 cluster responses; 420 coordinator-to-root escalations; 1,758 root requests; 1,758 root responses; and 1,758 root state updates**. The categories reconcile and the summary reports correctness `passed`.

**Milestone achieved:** SMIC now runs through the same monitoring architecture as FMIC and produces a matched, preliminary result for the approved cohort and alpha.

### 22.7 What the completed runs show so far

| Measure | Matched Phase 2 | FMIC | SMIC |
|---|---:|---:|---:|
| One-minute buckets | 19,984 | 19,984 | 19,984 |
| Threshold (°C) | 22.42866665 | 22.42866665 | 22.42866665 |
| Total messages | 38,087 | 11,922 | 11,902 |
| Root synchronizations | 2,107 | 293 | 293 |
| Minutes at or above threshold | 1,999 | 1,999 | 1,999 |
| Reported monitoring correctness | Passed | Passed | Passed |
| Reduction in messages vs Phase 2 | — | 68.70% | 68.75% |

FMIC and SMIC both use far fewer messages than the matched Phase 2 simulation at **alpha = 0.10**. SMIC sends only **20 fewer messages** than FMIC, a difference of about **0.17% of FMIC's message total**. The two event files contain the same selected cluster partitions at corresponding event positions. Their synchronization timestamps differ in only **two** corresponding event positions, by one minute each. Therefore, the second-moment calculation has made only a small difference in this first experiment; it should not be treated as a universal finding about SMIC.

The reported zero-error results mean the monitoring methods kept their last root-known safe/violated state consistent with the observed global state at each of the 19,984 minutes in these runs. The centralized global mean is used as an **offline correctness check**; it is not allowed to secretly trigger communication during monitoring.

These comparisons are **preliminary, fixed-alpha results**, not the final study. They establish that the algorithms have working implementations and comparable outputs. They do **not** yet establish that alpha 0.10 is optimal, that SMIC will always use fewer messages, or that either method performs the same way with sensors dropping offline.

### 22.8 US-3.21 — Comprehensive synthetic validation

**What was done**

1. Expanded shared FMIC/SMIC protocol tests with an explicit sender/recipient/purpose/category transmission ledger and a singleton-cluster case.
2. Confirmed the centralized correctness oracle detects injected false-safe and false-violated states, reports failure for either mismatch, and does not determine protocol communication.
3. Verified source-moment and weighting expectations against independent hand calculations and the rendered original PDF: Section 1.4, printed p.10/PDF p.14, and Appendix 1, printed p.22/PDF p.26.
4. Ran `python -B -m unittest scripts.phase3_test_monitoring scripts.phase3_test_history scripts.test_phase2_monitoring -q`; all **91 tests passed**.
5. Replayed both production methods from the current notebook implementation in an isolated temporary root using the approved 19,984-bucket input. FMIC passed with 11,922 messages and 293 synchronizations; SMIC passed with 11,902 messages and 293 synchronizations. Both had 1,999 violated buckets, zero false-safe/false-violated states, and reconciled message totals. The generated event and summary files matched the saved artifacts byte-for-byte.

**Milestone achieved:** Synthetic formula, protocol, correctness, and communication-accounting validation passed for FMIC and SMIC. The validation record is `artifacts/phase3a_validation_summary.json`.

### 22.9 US-3.22 — Alpha sensitivity and final comparison

**What was done**

1. Confirmed the US-3.21 validation record passed before starting the sweep.
2. Ran 19 fresh, full-length FMIC monitors and 19 fresh, full-length SMIC monitors over alpha **0.05–0.95 by 0.05**. Every run used sensors A, C, D, E, F, and G; the inclusive interval 2022-02-24 18:50 UTC–2022-03-10 15:53 UTC; 19,984 buckets; and the full-precision p90 **22.428666649999997 °C**.
3. All 38 runs had zero false-safe and false-violated states, passed correctness, and reconciled all seven message categories. The alpha=0.10 sweep runs matched the fixed-alpha baselines in total and category messages, root synchronization counts, correctness counts/status, and event fingerprints.
4. Protected input, configuration, matched Phase 2, and fixed-alpha production artifact hashes were unchanged during the final sweep execution. The notebook's normal execution path writes sweep artifacts without invoking the fixed-alpha output writers.
5. Wrote 38 result rows, 14,829 compact synchronization-event snapshots, a comparison summary, and three result-derived PNG plots. The event file preserves per-alpha partitions and monitor state without minute-by-minute traces.
6. Defined mean cluster size as total sensor memberships across all selected partitions at synchronization events, including initialization, divided by total clusters across those events. Mean cluster count is the arithmetic mean of per-event counts, also including initialization.
7. All 94 Phase 2/Phase 3 regression tests passed on the final implementation.

**Findings**

- Both methods reached their minimum observed message total at **alpha=0.65** on this dataset and tested grid: FMIC **8,722** messages and SMIC **8,720**. Each had 436 root synchronizations, mean cluster count 5.8005, and mean cluster size 1.0344. The reductions versus matched Phase 2 were 77.10% and 77.11%, respectively; these are in-sample descriptive minima, not generalizable or theoretically optimal settings.
- Message totals were irregular across alpha for both algorithms. At the prespecified alpha=0.10, FMIC used 11,922 messages and SMIC 11,902, with 293 root synchronizations each. The 20-message difference came from 8 additional FMIC node-trigger messages, 6 additional cluster-check requests, and 6 additional responses; root message and escalation categories were equal.
- At alpha=0.65, SMIC used two fewer messages than FMIC, entirely from two fewer coordinator-to-root escalations. The methods remain closely matched on this fixed experiment; no general superiority or statistical-significance claim is made.

**Milestone achieved:** US-3.22 completes the required Phase 3A alpha sensitivity sweep and matched final comparison. Phase 3B remains optional and was not evaluated.

### 22.10 What remains after US-3.22

**Phase 3B — Optional.** Only if separately approved, return to intermittent sensor availability and changing membership. The current Phase 3A outcomes do not answer those questions.

### 22.11 Files and evidence available for this record

The implementation history can be checked against these project artifacts:

- `build_phase1_temperature.py` — Phase 1 transformation and Phase 3A p90 statistics.
- `phase1_average_statistics.csv` — full-data and `phase3a_stable_cohort` statistics rows.
- `transformation_decisions.md` — Phase 1 run records and the aggregate-input exclusion correction.
- `build_phase3_temperature_clustering.ipynb` — Phase 3A history, clustering, FMIC, and SMIC code (the latest reviewed upload was named `build_phase3_temperature_clustering(4).ipynb`).
- `test_phase3_history.py` and `test_phase3_monitoring.py` — synthetic and implementation tests (the latest reviewed monitoring-test upload was named `test_phase3_monitoring(1).py`).
- `phase3a_phase2_baseline.json` — matched Phase 2 metrics.
- `phase3a_fmic_events.csv` and `phase3a_fmic_summary.json` — FMIC event history and results.
- `phase3a_smic_events.csv` and `phase3a_smic_summary.json` — SMIC event history and results.
- `phase3a_validation_summary.json` — US-3.21 test command, scenarios, source references, and production replay outcomes.
- `phase3a_alpha_results.csv`, `phase3a_alpha_events.csv`, and `phase3a_comparison_summary.json` — US-3.22 results, event snapshots, provenance, comparisons, and limitations.
- `phase3a_messages_vs_alpha.png`, `phase3a_synchronizations_vs_alpha.png`, and `phase3a_clustering_vs_alpha.png` — plots derived from the saved results table.
- `US-3.16` through `US-3.22` Markdown user stories — the scoped development instructions used to make the changes.

The US-3.21 gate was confirmed before the sweep. The US-3.22 38-run production sweep was executed and checked against the fixed-alpha baselines; the final sweep preserved their event and summary files.

### 22.12 US-3.23 — Two-sided geometric Phase 2 policy (2026-11-10)

The shared Phase 2 engine now gives each participating sensor the same
nonnegative allowance `abs(threshold - synchronized_mean)` and tests absolute
local deviations against it with `>=`. The signed local deviation remains
available for audit. The root retains the last synchronized SAFE/VIOLATED state;
an already-violated state no longer schedules a repeated root collection.
At exact equality, zero allowance still conservatively triggers on the next
bucket, even for unchanged readings. Initialization, membership/deferred
synchronization, next-bucket activation, and actual-transmission counting are
preserved.

The independent offline oracle checks the root state after bucket actions and
never controls synchronization. The revised 19,984-bucket matched run passed
with **9,159 messages** (753 triggers and 2,802 each of requests, responses, and
updates), **467 synchronizations**, 1,999 violated buckets, and **zero false-safe
and false-violated states**. Membership changes remained zero.

Outputs are `phase3a_phase2_two_sided_baseline.json` and
`phase3a_phase2_two_sided_events.csv`, generated by
`python -B -m scripts.phase2_monitoring`. The original signed-margin baseline
remains 38,087 messages and 2,107 synchronizations. The aggregate reduction of
28,928 messages and 1,640 synchronizations cannot be split causally between
scheduling removal and consequential trigger/timeline changes from those
aggregates alone.

All **103 Phase 2/Phase 3 tests passed**, including both oracle negative
controls, exact boundaries, cooling/warming, batched triggers, availability,
notebook reports, and protected outputs. Two fresh-process production runs
produced byte-identical revised baseline and event files. Before/after SHA-256
checks verified that the original Phase 2 outputs/baseline, input/configuration,
Phase 3 notebook, FMIC/SMIC results, US-3.21 validation, and US-3.22
tables/summary/plots were unchanged.

The general full-data Phase 2 notebook uses separate `phase2_two_sided_*`
output names. Its field dictionary documents the renamed absolute allowances,
removed negative-margin fields, retained root state, and explicitly separated
`legacy_event_*` synchronization diagnostics.

This is a policy repair, not full isolation of clustering benefits. Moment-based
allowances and coordinator/cluster protocol effects remain uncontrolled; any
comparison with existing FMIC/SMIC results is preliminary. No Phase 3 experiment
was rerun or denominator changed by US-3.23.


<!-- US-0.02 ORIGINAL SOURCE END: Phase3A_Pivot_Plan.md -->


<a id="phase-3a-comparability-record"></a>

### Phase 3A comparability record

Original source: `Writing/Markdowns/Phase3A_Comparability_Decision_Record_2026-11-10 (1).md`. The following is a historical record, not current requirements.

<!-- US-0.02 ORIGINAL SOURCE START: Writing/Markdowns/Phase3A_Comparability_Decision_Record_2026-11-10 (1).md -->

# Phase 3A Experimental Comparability — Issues, Decisions, and Implications

**Project:** Distributed Monitoring of Environmental Sensor Streams  
**Decision record date:** November 10, 2026  
**Scope:** Review and redesign decisions discussed concerning Phase 2, FMIC, SMIC, alpha sensitivity, and communication accounting  
**Status:** **Design decisions and user stories prepared; implementation deferred.** US-3.23, US-3.24, and US-3.25 have **not** been implemented as part of this discussion.

## 1. Executive summary

The original Phase 3A experiment compared the matched non-clustered Phase 2 monitor against FMIC and SMIC clustering monitors. The US-3.22 alpha sensitivity sweep completed 38 reported runs (19 alpha values for each of FMIC and SMIC), all with passing reported threshold-state correctness and reconciled transmission totals. Both methods used the fewest messages on the tested dataset at **alpha = 0.65**.

That initially appeared to demonstrate substantial communication savings from clustering. Closer inspection revealed a problem with **causal attribution**: at alpha = 0.65, FMIC and SMIC generally use **nearly six separate clusters for six sensors**. Full singleton partitions offer **no cross-sensor cancellation**, yet Phase 3 still communicates far less than the original Phase 2 baseline. Thus, the measured Phase 2–Phase 3 difference cannot reasonably be attributed to clustering alone.

We identified three comparability questions:

1. **Threshold policy:** Original Phase 2 uses a signed margin and automatically schedules further synchronization when the synchronized global margin is negative. Phase 3 uses a nonnegative distance to the threshold and retains a verified safe/violated state while its distributed constraints guarantee that state remains correct.
2. **Allowance allocation:** Phase 2 gives sensors equal allowances; FMIC/SMIC distribute allowances based on source-defined first- and second-moment weights. This changes local-trigger rates even when clustering is disabled.
3. **Communication protocol:** Phase 2 sends alerts directly to the root; Phase 3 uses member-sensor coordinators and possible within-cluster checks. Some differences are inherent to clustering, but equivalent no-clustering implementations should agree on decisions and actual transmitted messages.

**Agreed direction:** Preserve the original results as historical evidence; implement the two-sided Phase 2 correction (**US-3.23**); prove Phase 2/Phase 3 equivalence with equal allowances and six fixed singletons (**US-3.24**); then separately quantify weighting, clustering, alpha sensitivity, communication composition, and repeated cluster checks (**US-3.25**). **Do not resume alpha-based final ranking until the earlier gates pass.**

This is primarily a correction to the **experimental design and interpretation**, not evidence that FMIC/SMIC's source-defined mathematics must be replaced.

---

## 2. The original experiment and the observation that prompted review

### Fixed experimental contract

- **Experiment:** `phase3a_stable_cohort`.
- **Six sensors:** A, C, D, E, F, G.
- **Interval:** February 24, 2022, 18:50 UTC through March 10, 2022, 15:53 UTC, inclusive.
- **Observations:** 19,984 consecutive one-minute buckets; no imputation in the selected cohort.
- **Threshold:** the cohort-specific p90, currently `22.428666649999997` °C, sourced from `phase1_average_statistics.csv` rather than hard-coded.
- **Boundary:** global mean below threshold is **SAFE**; global mean equal to or above threshold is **VIOLATED**.
- **Comparison metric:** actual transmissions between distinct components, separately counting requests and responses. Six sensors plus a **separate root**.
- **Offline correctness check:** true global mean and its threshold-state label at every bucket; the oracle must not trigger operational communication.

### Original saved results

| Configuration | Messages | Root synchronizations | Reduction versus original Phase 2 |
|---|---:|---:|---:|
| Original matched Phase 2 | 38,087 | 2,107 | — |
| FMIC, alpha 0.10 | 11,922 | 293 | 68.70% |
| SMIC, alpha 0.10 | 11,902 | 293 | 68.75% |
| FMIC, alpha 0.65 | 8,722 | 436 | 77.10% |
| SMIC, alpha 0.65 | 8,720 | 436 | 77.11% |

The stored US-3.22 CSV has 38 unique method/alpha rows from 0.05 through 0.95 in increments of 0.05. Its seven message categories sum to the recorded total on all 38 rows. All rows report zero false-safe and zero false-violated buckets; the earlier US-3.21 validation summary reports 91 passing tests on November 3, 2026. These observations provide evidence for the **existing implementations**; they do not resolve whether the original comparison isolated clustering's effect.

At **alpha 0.65**, the saved records report mean cluster count approximately **5.8005** at synchronization and mean cluster size approximately **1.0344**. Diagnostic review found **354 of 436 synchronization events (81.2%)** used six singleton clusters; the remainder included limited grouping. This is the central interpretability concern: **the alpha with the lowest total messages is often functionally non-clustered**.

**Implication:** The previous conclusion should be phrased as *"the full Phase 3 implementation used fewer messages than the historical Phase 2 implementation"*, not *"clustering itself saved 77% of the messages."* The US-3.22 minimum remains the **minimum observed on one dataset and grid**, not a universal optimum.

---

## 3. Issue 1 — Inconsistent threshold-monitoring policy

### Concern

Original Phase 2 sets a **signed** synchronized allowance:

`margin = threshold - synchronized_global_mean`

When the synchronized global mean is above threshold, this is negative. Under its current policy, Phase 2 schedules another full synchronization at the next bucket whenever the new margin remains negative. A sustained violation can therefore generate repeated full-network communication even if readings are stable and the root already knows that the global condition is violated.

Phase 3 instead sets:

`root_allowance = abs(threshold - synchronized_global_mean)`

It maintains the last verified **SAFE** or **VIOLATED** status and checks whether local/cluster movement is large enough to make that known status uncertain. No automatic next-minute synchronization is triggered merely because the root's verified state is VIOLATED.

**Example:** With threshold 25°C and a synchronized mean of 27°C, Phase 2 obtains margin -2°C and schedules further synchronization while above threshold. Phase 3 obtains a **2°C distance**; it can remain silent while correctly enforced constraints establish that the global mean has not crossed the boundary. This works for cooling toward safety as well as warming toward violation.

### Agreed resolution — US-3.23

Change **only** the Phase 2 threshold policy, while retaining a non-clustered design and equal node allowances:

1. At synchronization, set the node/root allowance to `abs(threshold - synchronized_mean)`.
2. Trigger on `abs(current_sensor_value - synchronized_sensor_reference) >= allowance`.
3. Remove automatic next-bucket resynchronization **solely** because a synchronized margin is negative.
4. Retain the last verified SAFE/VIOLATED root state until a legitimate synchronization updates it.
5. Preserve existing initialization, actual membership-change handling (where applicable), explicit `>=` boundary convention, and next-bucket activation of new references.
6. Add independent two-sided synthetic tests, exact-boundary tests, a centralized-oracle correctness gate, and per-category communication reconciliation.
7. Save a **separately named corrected Phase 2 baseline**; do not overwrite the historical 38,087-message result or change original Phase 3 artifacts.

### Why this is mathematically defensible

For six sensors with current deviations `d_i` from their synchronized references and a nonnegative global distance `delta`, if every sensor satisfies `|d_i| < delta`, then:

`|mean(d_i)| <= mean(|d_i|) < delta`.

The mean cannot move sufficiently to cross the threshold without a local constraint reaching its trigger condition. This is a **deterministic guarantee under the model's assumptions**, not a statistical prediction. Correctness still depends on valid sensor observations, coherent references, current data and correctly delivered protocol messages. The real dataset checks only the sampled one-minute observations and the **global average**, not individual sensor overheating or between-sample excursions.

### Implications

- Removes a major **unwanted confounder** that can overstate the apparent benefit of clustering.
- Likely reduces Phase 2 synchronization traffic substantially, but **no new production message total is accepted until US-3.23 is actually implemented and run**.
- Does **not** itself resolve weighting or protocol equivalence.
- Does not require changing source-defined FMIC/SMIC mathematics or their old alpha results.

---

## 4. Issue 2 — Equal allowances versus moment-based allowances

### Concern

After threshold-policy alignment, Phase 2 would still give each of the six sensors the **same local allowance** `delta`. FMIC and SMIC instead allocate different sensor-specific allowances, which can affect triggering independently of whether sensors are actually grouped into multi-member clusters.

The Phase 3 formulas normalize nonnegative raw weights to sum to the sensor count:

`w_i = 6 * W_i / sum_j(W_j)` and `allowance_i = w_i * delta`, so `sum_i allowance_i = 6 * delta`.

- **FMIC:** `W_i = abs(first_moment_i)`.
- **SMIC:** `W_i = abs(first_moment_i) + sqrt(((m-1)/m) * second_moment_i)`; the second-moment term is the source-defined **unnormalized central second-moment** construction, not ordinary sample standard deviation.
- The existing project-defined all-zero-weight fallback assigns equal weights.

These formulas come from the paper's source-defined method of assigning node-dependent constraints; they are **not** an accidental Phase 3 implementation difference. The first moment in the current project is derived from discounted **raw** temperature readings, so it should not be described simply as a sensor volatility estimate.

### Agreed resolution — controlled configurations in US-3.25

**Do not add moment weighting to the revised primary Phase 2 baseline.** Keep Phase 2 as a meaningful equal-allowance, non-clustered reference. Instead, use the same Phase 3 engine to establish five configuration types:

| ID | Configuration | Allowance method | Clustering |
|---|---|---|---|
| **C0** | Common control | Equal | Six fixed singleton clusters |
| **C1** | FMIC weighting alone | FMIC first moment | Six fixed singleton clusters |
| **C2** | SMIC weighting alone | SMIC first + second moment | Six fixed singleton clusters |
| **F** | Full FMIC | FMIC first moment | Source-defined, alpha-selected partition |
| **S** | Full SMIC | SMIC first + second moment | Source-defined, alpha-selected partition |

**Interpretation of comparisons:**

- **C0 → C1 and C0 → C2:** effect of changing the allowances while holding the singleton protocol fixed.
- **C1 → F and C2 → S:** incremental effect of clustering **conditional on the same weighting method**.
- **F ↔ S:** distinction between the complete FMIC and SMIC approaches.

### Implications

- Separates the contributions of **weight allocation** and **actual clustering**, rather than crediting their combined savings to clustering.
- Keeps the original algorithms scientifically recognizable and consistent with their source-defined moments and weights.
- Allows effects to be non-additive; weighting and clustering can interact.
- The fixed singleton controls **do not need alpha sweeps**, since their partitions do not depend on alpha.

**Provisional diagnostic evidence from the morning's code review** (not acceptance targets): at alpha 0.65, controlled replays reported **9,159** messages for equal allowances + six singletons (C0-like), **8,964** for FMIC weighting + six singletons, **8,962** for SMIC weighting + six singletons, versus **8,722** full FMIC and **8,720** full SMIC. These figures suggest weighting and clustering each provided smaller incremental savings than the original headline comparison implied, but the final experiment must reproduce its own results and validation gates.

---

## 5. Issue 3 — Phase 2 versus Phase 3 communication-protocol comparability

### Concern

Phase 2 sends a genuine local trigger notification **directly to the root**, which then requests readings, receives responses, and distributes updates to all six sensors. Phase 3 places a coordinator within each cluster. A triggering sensor may notify its coordinator; the coordinator may request remaining member readings and, if its cluster constraint is not satisfied, escalate to the root. The root then performs its own six-sensor collection and update.

This difference is **largely inherent to the clustering mechanism being evaluated**. It may substitute limited local communications for expensive root-wide checks, but failed cluster checks introduce additional overhead. We should not rewrite the coordinator protocol solely to force a desired outcome.

A genuine concern remains: Are there **implementation or accounting differences** even when all intended mechanisms are turned off? Different message-category labels can also mask semantically identical traffic.

### Agreed resolution — US-3.24 protocol-equivalence gate

Compare revised Phase 2 to **C0**, a Phase 3 configuration with:

- Exactly six **fixed singleton** clusters at every synchronization.
- Equal node allowances computed from the same two-sided root distance.
- No use of moment-derived allowances or multi-sensor cancellation.
- Independent event-driven monitoring over the same 19,984 observations; no replay of one method's decisions by the other.
- The same initialization, `>=` boundary, next-bucket state activation, and per-bucket trigger rules.

Map corresponding transmissions:

| Actual communication | Revised Phase 2 | C0 (Phase 3 singleton) |
|---|---|---|
| Sensor-to-root local alert | `trigger_message_count` | `coordinator_root_escalations` |
| Root-to-sensor requests | `request_message_count` | `root_sync_requests` |
| Sensor-to-root responses | `response_message_count` | `root_sync_responses` |
| Root-to-sensor updates | `broadcast_message_count` | `root_state_updates` |
| Between-sensor checks | None | `node_trigger_messages`, `cluster_check_requests`, `cluster_check_responses` must all be **zero** |

With a separate root and six sensors, one full root synchronization costs **18 messages** (six requests + six responses + six updates). If there are `S` synchronizations, including initialization, and `L` genuine sensor-to-root trigger notifications, both implementations should yield:

`total_messages = 18*S + L`.

A valid equivalence result requires **same trigger sensors, synchronization timestamps, entry references/allowances, root-known state, and mapped message counts on every bucket**. Matching only the aggregate message total is insufficient. Any unexplained divergence fails US-3.24 and blocks US-3.25.

### Implications

- Establishes a **common zero-clustering, equal-allocation baseline** on which the causal comparisons can rest.
- Demonstrates which communication differences reflect intended clustering rather than incompatible state machines or undercounted messages.
- Retains the legitimate possibility that clustered methods have **more** messages in some circumstances due to coordinator overhead.
- Requires no rewrite of the ordinary FMIC/SMIC coordinator mechanism unless a focused equivalence/correctness test exposes a defect.

---

## 6. Communication composition — message purpose matters, not just total messages

### Concern

Two configurations with similar total messages could operate very differently. One might send many local peer/coordinator messages while avoiding root checks; another might perform almost no local checking yet synchronize the full network frequently. A total-message summary alone would conceal this important behavior.

### Findings from the existing US-3.22 outputs

The saved Phase 3 results already record **seven mutually exclusive transmission categories**. These can be grouped into:

1. **Within-cluster:** `node_trigger_messages + cluster_check_requests + cluster_check_responses`.
2. **Coordinator-to-root:** `coordinator_root_escalations`.
3. **Root-wide:** `root_sync_requests + root_sync_responses + root_state_updates`.

For FMIC:

| Purpose of transmission | Alpha 0.10 | Alpha 0.65 |
|---|---:|---:|
| Within-cluster | 6,228 | 192 |
| Coordinator-to-root | 420 | 682 |
| Root-wide synchronization | 5,274 | 7,848 |
| **Total** | **11,922** | **8,722** |
| Root synchronizations | 293 | 436 |
| Within-cluster share | 52.2% | 2.2% |

This means **alpha 0.65 produces fewer total messages while performing more root-wide synchronizations**. It principally avoids a large amount of coordinator/peer exchange rather than minimizing root synchronization frequency. The communication pathways and their purpose are meaningful secondary research outcomes.

### Agreed resolution — required US-3.25 outputs

Retain **total actual transmitted messages** as the primary metric, but require the following for every configuration:

- All seven raw categories and exact reconciliation to total.
- Counts **and percentages** for the three pathway groups.
- Coordinator checks resolved locally versus checks that escalate, reported as **operations** rather than transmissions.
- Compact counts of within-cluster traffic and check outcomes **by checked cluster size**.
- A fourth alpha visualization showing communication composition, in addition to total messages, synchronizations, and cluster structure.

Do not automatically call a locally resolved check an *avoided root synchronization*: another cluster might still escalate on that same bucket. Counterfactual root-sync savings must come from a comparison against an **independently executed singleton control**.

### Implications

- Enables explanation of **how** clustering redistributes network communication, even when total counts are close.
- Reveals trade-offs between peer/coordinator overhead and root-wide synchronization.
- Does **not** prove that local traffic uses fewer bytes, less energy, fewer hops, or less latency. Those require different network/cost models; the project currently measures **transmission counts**, not bandwidth.

---

## 7. Repeated cluster checks, locally resolved alerts, and apparent “false positives”

### Concern

A sensor that exceeds its local allowance may cause a cluster check. If the coordinator discovers that sensor deviations cancel sufficiently, it **does not** escalate to the root. However, the existing protocol **does not reset** the cluster's sensor references or allowances after that successful local check.

Consequently, if the same sensor deviations remain outside individual allowances on the following bucket, the coordinator may **check the same cluster again**, even though the last check succeeded. This can produce repeated within-cluster traffic with no new root synchronization.

For example, two members might move **+3°C** and **−3°C** relative to their synchronized references. Their average change is zero, but each may exceed its individual allowance. If those readings persist, the same check can recur each minute.

This is an **efficiency issue**, not a demonstrated loss of correctness. A locally resolved alert is not a statistical “false positive”: the sensor's individual constraint was genuinely exceeded, even though the cluster or global state may remain safe/unchanged.

### Diagnostic results discussed

A morning diagnostic replay reported, for FMIC:

| Coordinator-check diagnostic | Alpha 0.10 | Alpha 0.65 |
|---|---:|---:|
| Total checks | 3,522 | 774 |
| Checks without escalation | 3,102 | 92 |
| Checks repeated for same cluster on adjacent buckets | 2,889 | 60 |
| Repeated-check share | 82.0% | 7.8% |

These figures are **diagnostic observations**, not previously published US-3.22 acceptance results; US-3.25 must regenerate and validate these additional counters. A consecutive check does **not** establish identical readings or prove the second check could safely have been skipped.

### Agreed resolution — measure, do not silently suppress

US-3.25 now requires:

- `repeated_coordinator_check_count` for the **same member set checked at adjacent one-minute buckets**, with no intervening root synchronization/reference reset.
- The subset of such repeated checks **resolved without escalation**.
- Repeated-check percentage of all checks and compact breakdowns **by cluster size**.
- Synthetic fixtures with persistent offsetting deviations, later deteriorating cancellation, gaps between checks, and root synchronization resets.
- Explicit reconciliation of operations versus actual message transmissions.

**Do not automatically suppress repeated checks.** A coordinator's successful check at minute `t` does not guarantee cancellation at minute `t+1` without new information. Blind suppression could miss a threshold-state change.

### Possible future research extension — local cluster resynchronization

A future algorithm could introduce a locally verified checkpoint and redistribute **remaining** cluster allowance after a successful coordinator check, potentially reducing repeated traffic. This would require a new mathematical proof that repeated local resets cannot cumulatively permit an undetected global boundary crossing; explicit messages and a new test suite would be needed. It is **not part of US-3.25** and should not be added to the present source-aligned comparison.

### Implications

- Makes a previously hidden source of coordinator overhead visible.
- Helps explain why lower alpha values with multi-member clusters can incur more local traffic than almost-singleton configurations.
- Preserves current protocol correctness and source alignment while leaving room for a **separate future algorithmic improvement**.

---

## 8. Exact-boundary and zero-allowance behavior

### Concern

With the conservative local trigger rule:

`abs(local_deviation) >= node_allowance`

an allowance of exactly **zero** makes even an unchanged reading trigger (`abs(0) >= 0` is true). If the synchronized global mean lies exactly on the threshold, the root distance is zero, so the current implementation can generate repeated checks or synchronizations with unchanged readings.

This is an **efficiency boundary case**, not automatically a correctness error. The equality convention (global mean `>= threshold` is violated) and conservative local trigger need explicit review before changing anything.

### Agreed response

Include focused synthetic tests and an explicit report in US-3.25, covering:

- Global mean exactly equal to threshold; unchanged versus genuinely changed observations.
- Individual sensors with zero moment-derived weights/allowances.
- Warming and cooling across the boundary, including next-bucket activation and correct root-known states.
- Communications and repeated no-change events caused by the existing conservative `>=` rule.

**Do not globally replace `>=` with `>` as an optimization.** A narrowly targeted zero-allowance exception might be considered later only after a proof, consistency review for revised Phase 2/C0, and regression tests for all affected modes.

### Implications

- Makes another source of potential communication overhead auditable.
- Prevents optimization for fewer messages from accidentally weakening exact-boundary correctness.
- Leaves current production semantics unchanged pending validated evidence.

---

## 9. False negatives and the meaning of correctness

### Concern

Would Phase 3's reduced frequency of root synchronization cause more **false negatives**, particularly when the global mean remains above threshold?

### Finding

Under a correct implementation of the sensor and coordinator constraints, the root need not receive new measurements every minute to know that the **last verified threshold state has not changed**. For non-clustered equal allowances, the triangle inequality gives the guarantee described in Section 3. For multi-member clusters, the coordinator must verify its cluster's signed mean movement against the valid cluster allowance; all cluster guarantees combine to protect the root's known global state. A cluster check that fails its guarantee must escalate.

Thus **silence is not equivalent to “safe.”** The root retains the last verified state, which could be VIOLATED. The correct diagnostic is whether that **root-known state** agrees with the true global threshold state each minute—not whether a synchronization occurs on each above-threshold minute.

### Agreed response

Every revised Phase 2 and Phase 3 configuration must pass the independent two-sided correctness gate:

- `false_safe_count == 0`.
- `false_violated_count == 0`.
- Same authoritative sample interval, threshold and boundary convention.
- Oracle computes true labels **offline** and must not influence triggers or communication.
- Synthetic validation includes both crossing directions and deliberately injected incorrect states that the tests must detect.

### Implications and limits

- Correctly implemented geometric monitoring does **not inherently trade missed threshold-state changes for fewer messages**.
- The finite real-data result (38 reported passing runs) supports, but does not universally prove, correct operation in all possible streams.
- Guarantees assume complete one-minute readings, correct state synchronization and timely/accurate communications. They do **not** cover unobserved between-minute crossings, individual-device overheating when the global mean remains acceptable, or arbitrary asynchronous/out-of-order real-world networks.

---

## 10. Decision to pause alpha evaluation

### Concern

Continuing to optimize alpha while Phase 2 and Phase 3 differ in monitoring policy, weighting and protocol could choose a low-message configuration for reasons other than clustering. For singleton controls, alpha has **no causal role** because the partition is fixed.

### Agreed response

1. **Suspend further alpha ranking** until US-3.23 and US-3.24 pass and the US-3.25 control comparisons are validated.
2. Preserve the 38 original US-3.22 rows, results and interpretation as **historical/provisional**—do not discard or silently relabel them.
3. Run the **three** alpha-independent controls C0/C1/C2 once each over the full cohort, with fresh states.
4. Only **then** compare full FMIC and SMIC over the 19-value alpha grid. The output design comprises **41 Phase 3 records** (3 singleton controls + 19 FMIC + 19 SMIC) plus the separately validated revised Phase 2 baseline.
5. Keep `alpha = 0.10` as the **prespecified** full-algorithm reference; report best observed grid alpha(s) separately as **exploratory, in-sample** outcomes. All ties must be acknowledged.
6. Recompute every Phase 2-relative reduction with the **revised** baseline, not the historical 38,087 denominator.
7. Do not interpret a deterministic single-dataset sweep as statistical significance, generalization, or universal hyperparameter optimization.

### Implications

- Restores a defensible order: **baseline correctness → protocol equivalence → isolated mechanism comparisons → alpha sensitivity**.
- Avoids wasted redundant singleton alpha runs and prevents premature interpretation of results.
- Protects historical reproducibility while producing a new scientifically interpretable comparison.

---

## 11. Implementation sequence and user-story ownership

| Story | Purpose | Required outcome | Current status |
|---|---|---|---|
| **US-3.21** | Independent FMIC/SMIC source mathematics, protocol and accounting validation | Original validation record: 91 tests passed; historical production baselines passed | **Previously reported complete**; rerun affected tests if code changes |
| **US-3.22** | Original 19-by-2 alpha sweep and matched Phase 2 comparison | 38 records, reported correctness passing and reconciled message categories | **Completed historically**, but causal interpretation **provisional** |
| **US-3.23** | Align Phase 2 to two-sided geometric threshold monitoring | Corrected and separately named Phase 2 baseline, with unchanged historical artifacts | **Story written; not implemented** |
| **US-3.24** | Establish Phase 2/C0 singleton protocol equivalence | Per-bucket identical decisions, reference states and mapped message totals; stop on any mismatch | **Story written; not implemented** |
| **US-3.25** | Mechanism isolation, communication composition, repeated-check and zero-allowance diagnostics, revised alpha sweep | 3 controls + 38 clustered configurations, complete correctness and communication checks; revised final report | **Final story written; not implemented** |

**Required order:** `US-3.23 → US-3.24 (must pass) → US-3.25 (controls and correctness must pass before resumed alpha interpretation)`.

**Boundaries on implementation:**

- Reuse the existing validated Phase 2 and shared Phase 3 engines; do not create unrelated duplicate state machines.
- Preserve the original source-defined FMIC/SMIC moments, signed histories, greedy clustering and coordinator protocol, absent a separately demonstrated defect.
- Count **actual** transmissions between distinct components; requests and responses are separate; self-messages and internal computations cost zero; do not double-count piggybacked information.
- Keep compact run-level and cluster-event summaries, not gigabytes of minute-by-minute production logs.
- Reproducibly record commands, code/config/input hashes and deterministic event checks; if earlier results can be reused, verify that the source and version match and clearly label that reuse.

---

## 12. Future work expressly deferred

These are **ideas to evaluate later**, not commitments in US-3.23–US-3.25:

1. **Local coordinator re-check suppression or local resynchronization:** promising for repeated cluster checks, but requires new safety invariants, state distribution rules and correctness proof. Blind suppression is unsafe.
2. **Special zero-allowance optimization:** may reduce unnecessary unchanged-value traffic but cannot alter the global threshold convention or remove required checks without rigorous validation.
3. **Network cost beyond message counts:** byte volume, message payload size, network hops, energy, latency and physical topology could change which communication pattern is preferable.
4. **Sensor availability robustness (Phase 3B):** departures, returns, incomplete cohorts and asynchronous communication remain outside the six-sensor fixed-cohort experiment.
5. **Multivariate extension and out-of-sample validation:** required before making broad claims about other sensor modalities, networks and operating conditions.

---

## 13. Final interpretation and decision summary

The morning's review did **not** establish that the existing Phase 3 monitoring algorithms fail correctness. It established that our prior headline comparison **combined several different mechanisms** and therefore did not isolate clustering's contribution.

The scientific approach going forward is to **standardize only what must be comparable** (threshold policy, root-state semantics, input, communication accounting and the no-clustering control), while **preserving the intended differences** (first- versus second-moment weighting and actual cluster coordination). Then report not only *how many* transmissions occur, but *why they occur, which communication pathway carries them, how often checks are locally resolved or repeated, and how those patterns vary with clustering and alpha*.

**Decisions reached:**

- **Yes:** Correct Phase 2's signed/negative-margin threshold behavior through US-3.23, retaining the original results.
- **Yes:** Require exact revised Phase 2 versus C0 singleton equivalence through US-3.24.
- **Yes:** Use C0/C1/C2 plus full FMIC/SMIC to distinguish weighting and clustering effects through US-3.25.
- **Yes:** Make within-cluster / coordinator-to-root / root-wide composition, checks resolved locally, repeat-check diagnostics, cluster-size summaries and zero-allowance tests mandatory secondary outcomes.
- **Not now:** Reweight Phase 2, redesign coordinator checks, suppress repeated checks, change threshold-boundary semantics, optimize network-byte costs or choose alpha before control validation.

**Final status as of November 10, 2026:** The experimental redesign is **documented, not implemented**. The original baseline and sweep are preserved as historical evidence; a revised, causal-attribution-ready final experiment remains to be executed under US-3.23–US-3.25.

---

## 14. Source and artifact references

The decision record was prepared from the discussion on November 10, 2026, and the following supplied project materials. Diagnostic calculations mentioned in this record are labeled separately from saved production results.

- `140516editor Book Chapter (Last Version)(1).pdf` — *Clustering for Monitoring Distributed Data Streams*, especially source monitoring/clustering algorithms and moment formulas.
- `Phase3A_Pivot_Plan.md` and `Distributed_Monitoring_POC_Project_Plan.md` — governing stable-cohort design and historical implementation context.
- `US-3.21_comprehensive_synthetic_validation_FMIC_SMIC.md` — original validation requirements.
- `US-3.22_alpha_sensitivity_and_final_comparative_evaluation.md` — original alpha experiment requirements.
- `US-3.23_phase2_two_sided_geometric_threshold_policy.md` — proposed Phase 2 correction.
- `US-3.24_phase2_phase3_protocol_equivalence_validation.md` — protocol-equivalence test requirements.
- `US-3.25_Final.md` — final proposed controlled evaluation, communication-composition and repeated-check requirements.
- `build_phase2_temperature_sensors.ipynb` and `build_phase3_temperature_clustering.ipynb` — supplied implementation notebooks.
- `phase3a_phase2_baseline.json`, `phase3a_alpha_results.csv`, `phase3a_comparison_summary.json`, `phase3a_validation_summary.json`, `phase3a_fmic_summary.json`, `phase3a_smic_summary.json`, and baseline event CSVs — historical recorded outcomes.

**Note on evidence strength:** Historical CSV/JSON totals and recorded validation status were inspected. Morning diagnostic replays and illustrative examples are useful for motivating tests but are **not** substitutes for the new implementation, independent US-3.24 equivalence gate, or US-3.25 final validated reruns.


<!-- US-0.02 ORIGINAL SOURCE END: Writing/Markdowns/Phase3A_Comparability_Decision_Record_2026-11-10 (1).md -->
