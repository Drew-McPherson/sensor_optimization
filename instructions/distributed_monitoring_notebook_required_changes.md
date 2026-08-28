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

For the active Phase 2 implementation in this repository, the following canonical policy now applies:

1. local trigger is warming-only: `local_deviation >= local_margin`,
2. cooling (negative) local deviations do not trigger a re-sync request,
3. the preferred row-level timing columns are `entry_xbar_t0`, `entry_delta_global`, `observed_global_average`, and `exit_delta_global`,
4. per-sensor entry-state fields use `entry_{sensor}_reference_value` and `entry_{sensor}_local_margin`, and
5. per-sensor event fields use `event_{sensor}_local_deviation` and `event_{sensor}_resync_requested` naming, and
6. exported per-sensor reporting includes both `entry_{sensor}_local_margin` and `event_{sensor}_margin_proximity_score = entry_delta_global - event_{sensor}_local_deviation` (positive acceptable, negative violating).

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

The root sends one request to each of the \(n\) sensors:

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

Suggested fields:

```python
is_initial_sync
initial_request_message_count
initial_response_message_count
initial_broadcast_message_count
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
