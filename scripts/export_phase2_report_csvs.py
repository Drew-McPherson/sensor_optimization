#!/usr/bin/env python3
"""Export Phase 2 report outputs as CSV files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pandas as pd


def _detect_sensors(columns: list[str]) -> list[str]:
    sensors: set[str] = set()
    pattern = re.compile(r"^observed_(.+)_temperature$")
    for column in columns:
        match = pattern.match(column)
        if match:
            sensors.add(match.group(1))
    return sorted(sensors)


def _describe_column(column: str, sensor_names: set[str]) -> dict[str, str]:
    static: dict[str, dict[str, str]] = {
        "bucket_epoch": {
            "category": "time",
            "measures": "Unix epoch second for the bucket row.",
            "calculation": "Copied from aligned Phase 1 bucket timestamp.",
            "units": "seconds since 1970-01-01 UTC",
        },
        "bucket_time_utc": {
            "category": "time",
            "measures": "UTC timestamp for the bucket row.",
            "calculation": "Formatted datetime representation of bucket_epoch.",
            "units": "UTC datetime",
        },
        "transition_summary": {
            "category": "state",
            "measures": "Compact state transition label for row auditability.",
            "calculation": "Composed from row event conditions in the state machine.",
            "units": "text",
        },
        "p90_threshold_used": {
            "category": "threshold",
            "measures": "Global P90 threshold used for this run.",
            "calculation": "Loaded from phase1_average_statistics.csv for the selected series.",
            "units": "temperature",
        },
        "observed_global_average": {
            "category": "global",
            "measures": "Current row global average temperature.",
            "calculation": "From Phase 1 aligned field average_temperature_all_devices.",
            "units": "temperature",
        },
        "entry_xbar_t0": {
            "category": "global",
            "measures": "Global reference average entering this row.",
            "calculation": "Prior synchronized global reference carried into this row.",
            "units": "temperature",
        },
        "entry_delta_global": {
            "category": "global",
            "measures": "Global margin entering this row.",
            "calculation": "p90_threshold_used - entry_xbar_t0.",
            "units": "temperature",
        },
        "exit_delta_global": {
            "category": "global",
            "measures": "Global margin after row event processing.",
            "calculation": "p90_threshold_used - exit global reference (post-event state).",
            "units": "temperature",
        },
        "global_violation": {
            "category": "diagnostic",
            "measures": "Whether row average violates canonical threshold boundary.",
            "calculation": "1 when observed_global_average >= p90_threshold_used, else 0.",
            "units": "binary (0/1)",
        },
        "event_triggering_sensor_names": {
            "category": "event",
            "measures": "Sensor names that requested re-sync on this row.",
            "calculation": "Pipe-delimited list of sensors with event_{sensor}_resync_requested == 1.",
            "units": "text",
        },
        "event_resync_request_count": {
            "category": "event",
            "measures": "Count of sensor-local re-sync requests on this row.",
            "calculation": "Sum of event_{sensor}_resync_requested over all sensors.",
            "units": "count",
        },
        "event_any_sensor_requested_resync": {
            "category": "event",
            "measures": "Whether any sensor requested re-sync on this row.",
            "calculation": "1 when event_resync_request_count > 0, else 0.",
            "units": "binary (0/1)",
        },
        "event_resync_consumed_from_prior_row": {
            "category": "event",
            "measures": "Whether row consumed a forced re-sync scheduled by prior row.",
            "calculation": "Equals prior row exit_resync_scheduled_next_row.",
            "units": "binary (0/1)",
        },
        "event_resync_triggered_by_local_violation": {
            "category": "event",
            "measures": "Whether row triggered re-sync due to local violations.",
            "calculation": "1 when no forced consumption and any local request is present.",
            "units": "binary (0/1)",
        },
        "event_resync_performed": {
            "category": "event",
            "measures": "Whether a re-sync event was executed on this row.",
            "calculation": "1 when forced consumption or local trigger causes synchronization.",
            "units": "binary (0/1)",
        },
        "event_resync_reason": {
            "category": "event",
            "measures": "Reason code for performed re-sync.",
            "calculation": "Categorical label from row event evaluation.",
            "units": "text",
        },
        "event_exit_delta_negative": {
            "category": "event",
            "measures": "Whether the row exit global margin is negative.",
            "calculation": "1 when exit_delta_global < 0, else 0.",
            "units": "binary (0/1)",
        },
        "exit_resync_scheduled_next_row": {
            "category": "state",
            "measures": "Whether next row must consume a forced re-sync.",
            "calculation": "Set to 1 when current row exit_delta_global is negative.",
            "units": "binary (0/1)",
        },
        "exit_xbar_t0_if_resync": {
            "category": "state",
            "measures": "Global reference that becomes next row entry_xbar_t0 after re-sync.",
            "calculation": "Set to observed_global_average when re-sync is performed; otherwise carry prior.",
            "units": "temperature",
        },
        "exit_delta_global_if_resync": {
            "category": "state",
            "measures": "Global margin that becomes next row entry_delta_global after re-sync.",
            "calculation": "Set to p90_threshold_used - exit_xbar_t0_if_resync.",
            "units": "temperature",
        },
        "trigger_message_count": {
            "category": "communication",
            "measures": "Number of sensor trigger messages emitted this row.",
            "calculation": "On local-trigger rows equals event_resync_request_count; forced rows fixed to 0.",
            "units": "messages",
        },
        "request_message_count": {
            "category": "communication",
            "measures": "Number of distributed request messages this row.",
            "calculation": "Fanout count recorded when re-sync is performed.",
            "units": "messages",
        },
        "response_message_count": {
            "category": "communication",
            "measures": "Number of distributed response messages this row.",
            "calculation": "Fanout count recorded when re-sync is performed.",
            "units": "messages",
        },
        "broadcast_message_count": {
            "category": "communication",
            "measures": "Number of distributed broadcast messages this row.",
            "calculation": "Fanout count recorded when re-sync is performed.",
            "units": "messages",
        },
        "total_message_count": {
            "category": "communication",
            "measures": "Total communication messages for this row.",
            "calculation": "trigger_message_count + request_message_count + response_message_count + broadcast_message_count.",
            "units": "messages",
        },
    }

    if column in static:
        return {
            "field_name": column,
            "category": static[column]["category"],
            "measures": static[column]["measures"],
            "calculation": static[column]["calculation"],
            "units": static[column]["units"],
        }

    sensor_observed = re.match(r"^observed_(.+)_temperature$", column)
    if sensor_observed:
        sensor = sensor_observed.group(1)
        if sensor in sensor_names:
            return {
                "field_name": column,
                "category": "sensor_observed",
                "measures": f"Observed temperature for sensor {sensor} on this row.",
                "calculation": "Direct carry-forward of aligned Phase 1 per-sensor value for the same bucket.",
                "units": "temperature",
            }

    sensor_reference = re.match(r"^entry_(.+)_reference_value$", column)
    if sensor_reference:
        sensor = sensor_reference.group(1)
        return {
            "field_name": column,
            "category": "sensor_state",
            "measures": f"Entry synchronized reference value for sensor {sensor}.",
            "calculation": "Sensor value stored at most recent synchronization event.",
            "units": "temperature",
        }

    sensor_margin = re.match(r"^entry_(.+)_local_margin$", column)
    if sensor_margin:
        sensor = sensor_margin.group(1)
        return {
            "field_name": column,
            "category": "sensor_state",
            "measures": f"Entry local trigger margin for sensor {sensor}.",
            "calculation": f"p90_threshold_used - entry_{sensor}_reference_value.",
            "units": "temperature",
        }

    sensor_deviation = re.match(r"^event_(.+)_local_deviation$", column)
    if sensor_deviation:
        sensor = sensor_deviation.group(1)
        return {
            "field_name": column,
            "category": "sensor_event",
            "measures": f"Row local deviation for sensor {sensor}.",
            "calculation": f"observed_{sensor}_temperature - entry_{sensor}_reference_value.",
            "units": "temperature",
        }

    sensor_request = re.match(r"^event_(.+)_resync_requested$", column)
    if sensor_request:
        sensor = sensor_request.group(1)
        return {
            "field_name": column,
            "category": "sensor_event",
            "measures": f"Whether sensor {sensor} requested re-sync on this row.",
            "calculation": f"1 when event_{sensor}_local_deviation >= entry_{sensor}_local_margin and row is not forced; else 0.",
            "units": "binary (0/1)",
        }

    return {
        "field_name": column,
        "category": "other",
        "measures": "Field included in Phase 2 output schema.",
        "calculation": "See scripts/README.md and notebook logic for detailed derivation.",
        "units": "n/a",
    }


def _build_data_dictionary(raw_columns: list[str], sensor_names: list[str]) -> pd.DataFrame:
    sensor_set = set(sensor_names)
    rows = [_describe_column(column, sensor_set) for column in raw_columns]
    return pd.DataFrame(rows)


def _as_number(value: Any, field_name: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"Expected numeric value for '{field_name}', received: {value!r}")


def _build_reduction_analysis(metrics: dict[str, Any]) -> pd.DataFrame:
    communication = metrics.get("communication")
    if not isinstance(communication, dict):
        raise ValueError("Missing 'communication' object in metrics JSON.")

    rows = _as_number(metrics.get("rows"), "rows")
    sensor_count = _as_number(metrics.get("sensor_count"), "sensor_count")
    baseline = rows * sensor_count

    actual = _as_number(
        communication.get("distributed_total_messages"), "distributed_total_messages"
    )
    trigger_messages = _as_number(
        communication.get("distributed_trigger_messages"), "distributed_trigger_messages"
    )
    request_messages = _as_number(
        communication.get("distributed_request_messages"), "distributed_request_messages"
    )
    response_messages = _as_number(
        communication.get("distributed_response_messages"), "distributed_response_messages"
    )
    broadcast_messages = _as_number(
        communication.get("distributed_broadcast_messages"), "distributed_broadcast_messages"
    )

    if baseline <= 0:
        raise ValueError("Baseline communications must be > 0.")

    difference = baseline - actual
    ratio = 1.0 - (actual / baseline)
    percent = ratio * 100.0

    ratio_from_metrics = communication.get("communication_reduction_ratio_primary")
    ratio_delta = None
    if isinstance(ratio_from_metrics, (int, float)):
        ratio_delta = ratio - float(ratio_from_metrics)

    analysis_rows = [
        {
            "metric": "baseline_every_minute_messages",
            "value": int(round(baseline)),
            "units": "messages",
            "calculation": "rows * sensor_count",
            "notes": "Counterfactual baseline if every sensor transmitted every minute.",
        },
        {
            "metric": "poc_actual_messages",
            "value": int(round(actual)),
            "units": "messages",
            "calculation": "distributed_total_messages",
            "notes": "Actual total distributed traffic under this Phase 2 implementation.",
        },
        {
            "metric": "reduction_difference_messages",
            "value": int(round(difference)),
            "units": "messages",
            "calculation": "baseline_every_minute_messages - poc_actual_messages",
            "notes": "Absolute communication reduction achieved by the POC.",
        },
        {
            "metric": "reduction_ratio_primary",
            "value": ratio,
            "units": "ratio",
            "calculation": "1 - (poc_actual_messages / baseline_every_minute_messages)",
            "notes": "Primary reduction ratio agreed for reporting.",
        },
        {
            "metric": "reduction_percent_primary",
            "value": percent,
            "units": "percent",
            "calculation": "reduction_ratio_primary * 100",
            "notes": "Primary reduction expressed as percentage.",
        },
        {
            "metric": "distributed_trigger_messages",
            "value": int(round(trigger_messages)),
            "units": "messages",
            "calculation": "sum(trigger_message_count)",
            "notes": "Trigger-category communication breakdown.",
        },
        {
            "metric": "distributed_request_messages",
            "value": int(round(request_messages)),
            "units": "messages",
            "calculation": "sum(request_message_count)",
            "notes": "Request-category communication breakdown.",
        },
        {
            "metric": "distributed_response_messages",
            "value": int(round(response_messages)),
            "units": "messages",
            "calculation": "sum(response_message_count)",
            "notes": "Response-category communication breakdown.",
        },
        {
            "metric": "distributed_broadcast_messages",
            "value": int(round(broadcast_messages)),
            "units": "messages",
            "calculation": "sum(broadcast_message_count)",
            "notes": "Broadcast-category communication breakdown.",
        },
        {
            "metric": "rows",
            "value": int(round(rows)),
            "units": "count",
            "calculation": "metrics.rows",
            "notes": "Number of Phase 2 minute buckets.",
        },
        {
            "metric": "sensor_count",
            "value": int(round(sensor_count)),
            "units": "count",
            "calculation": "metrics.sensor_count",
            "notes": "Number of sensors included in Phase 2 run.",
        },
    ]

    resync = metrics.get("resync_events")
    if isinstance(resync, dict) and isinstance(
        resync.get("resync_performed_count"), (int, float)
    ):
        analysis_rows.append(
            {
                "metric": "resync_performed_count",
                "value": int(round(float(resync["resync_performed_count"]))),
                "units": "count",
                "calculation": "sum(event_resync_performed)",
                "notes": "Count of synchronization events in the run.",
            }
        )

    if isinstance(ratio_from_metrics, (int, float)):
        analysis_rows.append(
            {
                "metric": "reduction_ratio_primary_from_metrics",
                "value": float(ratio_from_metrics),
                "units": "ratio",
                "calculation": "metrics.communication.communication_reduction_ratio_primary",
                "notes": "Recorded metric from notebook output for parity checking.",
            }
        )

    if ratio_delta is not None:
        analysis_rows.append(
            {
                "metric": "ratio_delta_computed_minus_metrics",
                "value": ratio_delta,
                "units": "ratio",
                "calculation": "reduction_ratio_primary - reduction_ratio_primary_from_metrics",
                "notes": "Should be near zero; non-zero indicates rounding or contract mismatch.",
            }
        )

    return pd.DataFrame(analysis_rows)


def _write_csv_atomic(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(output_path)


def export_phase2_report_csvs(
    rows_input: Path,
    metrics_input: Path,
    data_dictionary_output: Path,
    analysis_output: Path,
    raw_output: Path,
) -> dict[str, Path]:
    if not rows_input.exists():
        raise FileNotFoundError(f"Missing rows input CSV: {rows_input}")
    if not metrics_input.exists():
        raise FileNotFoundError(f"Missing metrics input JSON: {metrics_input}")

    raw_rows = pd.read_csv(rows_input)
    metrics = json.loads(metrics_input.read_text(encoding="utf-8"))

    sensor_names = _detect_sensors(list(raw_rows.columns))
    data_dictionary = _build_data_dictionary(list(raw_rows.columns), sensor_names)
    reduction_analysis = _build_reduction_analysis(metrics)

    _write_csv_atomic(data_dictionary, data_dictionary_output)
    _write_csv_atomic(reduction_analysis, analysis_output)

    raw_output.parent.mkdir(parents=True, exist_ok=True)
    raw_tmp = raw_output.with_suffix(raw_output.suffix + ".tmp")
    shutil.copyfile(rows_input, raw_tmp)
    raw_tmp.replace(raw_output)

    return {
        "data_dictionary": data_dictionary_output,
        "sensor_reduction_analysis": analysis_output,
        "raw_row_results": raw_output,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create CSV-first Phase 2 report outputs: data dictionary, "
            "sensor reduction analysis, and raw row results copy."
        )
    )
    parser.add_argument(
        "--rows-input",
        default="artifacts/phase2_temperature_sensors.csv",
        help="Path to Phase 2 raw rows CSV.",
    )
    parser.add_argument(
        "--metrics-input",
        default="artifacts/phase2_temperature_metrics.json",
        help="Path to Phase 2 metrics JSON.",
    )
    parser.add_argument(
        "--data-dictionary-output",
        default="artifacts/phase2_data_dictionary.csv",
        help="Output CSV path for data dictionary.",
    )
    parser.add_argument(
        "--analysis-output",
        default="artifacts/phase2_sensor_reduction_analysis.csv",
        help="Output CSV path for sensor reduction analysis.",
    )
    parser.add_argument(
        "--raw-output",
        default="artifacts/phase2_raw_row_results.csv",
        help="Output CSV path for raw row passthrough.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    outputs = export_phase2_report_csvs(
        rows_input=Path(args.rows_input),
        metrics_input=Path(args.metrics_input),
        data_dictionary_output=Path(args.data_dictionary_output),
        analysis_output=Path(args.analysis_output),
        raw_output=Path(args.raw_output),
    )

    print("Wrote CSV report outputs:")
    for key, value in outputs.items():
        print(f"- {key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
