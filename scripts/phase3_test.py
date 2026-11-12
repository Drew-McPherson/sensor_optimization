"""Canonical Phase 3 behavioral, saved-output, and replay verification."""

import argparse
import ast
import contextlib
import copy
import csv
import hashlib
import io
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import phase3_implement as history_module
from scripts import phase3_implement as implementation
import scripts.phase3_implement as equivalence_runner
from scripts.phase3_implement import (
    ALPHA_LABELS,
    DiscountedFirstMoment,
    DiscountedSecondMoment,
    RUN_PATH,
    FMICMonitor,
    MESSAGE_CATEGORIES,
    PHASE3_PEER_CATEGORIES,
    _build_comparisons,
    _composition,
    _configuration_table,
    _fixed_singletons,
    _load_engine,
    _protected_hashes,
    _run_monitor,
    _validate_alpha_grid,
    compare_decisions,
    fmic_allocation,
    load_phase3_monitor,
    run_phase3_control,
    run_phase3a_alpha_sweep,
    run_phase3a_fmic,
    run_phase3a_smic,
    run_us325,
    smic_allocation,
)
from scripts.shared_monitoring_engine import (
    build_phase2_trace,
    evaluate_root_states,
    root_correctness_summary,
    prepare_monitoring,
)


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "phase3a_experiment_config.json"
PHASE3A_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
normalize_sensor_histories = history_module.normalize_sensor_histories
build_alpha_clustering_inputs = history_module.build_alpha_clustering_inputs
PHASE3_ALPHA_VALUES = history_module.PHASE3_ALPHA_VALUES
PHASE3A_DEFAULT_ALPHA_VALUES = history_module.PHASE3A_DEFAULT_ALPHA_VALUES
cluster_quality = history_module.cluster_quality
partition_quality = history_module.partition_quality
evaluate_alpha_clustering = history_module.evaluate_alpha_clustering


class ClusteringTests(unittest.TestCase):
    def evaluate(self, histories, alpha=0.1):
        snapshot = normalize_sensor_histories(histories, tuple(histories))
        item = history_module.AlphaClusteringInput(1, 1, alpha, snapshot)
        return evaluate_alpha_clustering(item)

    def test_quality_formulas_preserve_signed_cancellation(self):
        values = {"A": 1.0, "B": -1.0, "C": 0.5}
        self.assertAlmostEqual(cluster_quality(("A", "B"), values, 0.1), 0.2)
        self.assertAlmostEqual(cluster_quality(("A", "C"), values, 0.1), 0.95)
        self.assertAlmostEqual(
            partition_quality((("A", "B"), ("C",)), values, 0.1), 0.6
        )
        self.assertNotEqual(cluster_quality(("A", "B"), values, 0.1), 1.2)

    def test_hand_calculated_merge_sequence_and_candidate_quality(self):
        result = self.evaluate({"A": 1.0, "B": -1.0, "C": 0.5, "D": -0.5})
        candidates = result["candidate_partitions"]
        self.assertEqual(
            [item["partition"] for item in candidates],
            [
                (("A",), ("B",), ("C",), ("D",)),
                (("A", "B"), ("C",), ("D",)),
                (("A", "B"), ("C", "D")),
            ],
        )
        for item, quality in zip(candidates, (1.1, 0.6, 0.2)):
            self.assertAlmostEqual(item["partition_quality"], quality)
        self.assertEqual(result["merge_steps"][0]["selected_partner"], ("B",))
        self.assertEqual(result["merge_steps"][1]["selected_partner"], ("D",))
        self.assertEqual(result["selected_partition"], (("A", "B"), ("C", "D")))
        self.assertAlmostEqual(result["partition_quality"], 0.2)

    def test_partner_minimizes_merged_cluster_quality(self):
        result = self.evaluate({"A": 1.0, "B": -0.1, "C": -0.2, "D": 0.9})
        first = result["merge_steps"][0]
        self.assertEqual(first["worst_cluster"], ("A",))
        self.assertEqual(first["selected_partner"], ("C",))
        self.assertAlmostEqual(first["partner_scores"][0]["merged_quality"], 0.65)
        self.assertAlmostEqual(first["partner_scores"][1]["merged_quality"], 0.6)

    def test_earliest_minimum_wins_and_ties_are_deterministic(self):
        histories = {"A": 1.0, "B": -1.0, "C": 0.5, "D": -0.5}
        result = self.evaluate(histories, 0.9)
        self.assertEqual(result["selected_candidate_index"], 1)
        self.assertEqual(result["cluster_count"], 3)
        self.assertAlmostEqual(result["partition_quality"], 1.8)

        tied = self.evaluate({"A": 1.0, "B": -1.0, "C": -1.0, "D": 1.0})
        self.assertEqual(tied["merge_steps"][0]["worst_cluster"], ("A",))
        self.assertEqual(tied["merge_steps"][0]["selected_partner"], ("B",))

    def test_alpha_sweep_remains_available_explicitly(self):
        snapshot = normalize_sensor_histories(
            {"A": 0.6, "B": -0.3, "C": 0.15}, ("A", "B", "C")
        )
        baseline = build_alpha_clustering_inputs(2, snapshot)
        sweep = build_alpha_clustering_inputs(
            2, snapshot, alpha_values=PHASE3_ALPHA_VALUES
        )
        self.assertEqual(
            [item.alpha for item in baseline],
            list(PHASE3A_DEFAULT_ALPHA_VALUES),
        )
        self.assertEqual([item.alpha for item in sweep], list(PHASE3_ALPHA_VALUES))
        self.assertEqual(len(sweep), 19)
        self.assertTrue(all(item.normalization_snapshot is snapshot for item in sweep))
        results = [evaluate_alpha_clustering(item) for item in sweep]
        self.assertTrue(
            all(set(item["cluster_assignments"]) == {"A", "B", "C"} for item in results)
        )

    def test_alpha_changes_partition_on_constructed_history_fixture(self):
        histories = {
            "A": 0.4440125386327938,
            "B": 0.39679908060749325,
            "C": 0.7919116588589972,
            "D": 0.9158279911487557,
        }
        snapshot = normalize_sensor_histories(histories, tuple(histories))
        partitions = {
            alpha: evaluate_alpha_clustering(
                build_alpha_clustering_inputs(1, snapshot, (alpha,))[0]
            )["selected_partition"]
            for alpha in (0.05, 0.50)
        }
        self.assertEqual(partitions[0.05], (("A", "C"), ("B", "D")))
        self.assertEqual(partitions[0.50], (("A",), ("B",), ("C",), ("D",)))

    def test_invalid_quality_inputs_raise_explicit_errors(self):
        for alpha in (True, "0.1", float("nan"), float("inf"), -0.1, 1.1):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                cluster_quality(("A",), {"A": 1.0}, alpha)
        for cluster in ((), ("A", "A"), ("missing",), "A"):
            with self.subTest(cluster=cluster), self.assertRaises(ValueError):
                cluster_quality(cluster, {"A": 1.0}, 0.1)
        for partition in ((), (("A",),), (("A", "B"), ("A",))):
            with self.subTest(partition=partition), self.assertRaises(ValueError):
                partition_quality(partition, {"A": 1.0, "B": -1.0}, 0.1)


class NormalizationTests(unittest.TestCase):
    def test_all_zero_histories_use_deterministic_singleton_fallback(self):
        histories = {"B": 0.0, "A": 0.0}
        snapshot = normalize_sensor_histories(histories, ("B", "A"))
        inputs = build_alpha_clustering_inputs(7, snapshot)

        self.assertEqual(snapshot.maximum_history_magnitude, 0.0)
        self.assertIsNone(snapshot.normalized_histories)
        self.assertEqual(snapshot.fallback_partition, (("A",), ("B",)))
        self.assertTrue(snapshot.zero_history_fallback)
        self.assertEqual(
            [item.alpha for item in inputs], list(PHASE3A_DEFAULT_ALPHA_VALUES)
        )
        self.assertEqual(histories, {"B": 0.0, "A": 0.0})

    def test_signed_normalization_uses_maximum_history_magnitude(self):
        snapshot = normalize_sensor_histories(
            {"A": 0.60, "B": -0.30, "C": 0.15, "D": 0.0},
            ("A", "B", "C", "D"),
        )
        self.assertEqual(snapshot.maximum_history_magnitude, 0.60)
        self.assertEqual(
            dict(snapshot.normalized_histories),
            {"A": 1.0, "B": -0.5, "C": 0.25, "D": 0.0},
        )
        self.assertEqual(dict(snapshot.raw_histories)["B"], -0.30)

    def test_normalization_handles_tied_maximum_magnitudes(self):
        snapshot = normalize_sensor_histories(
            {"A": 0.6, "B": -0.6, "C": 0.3}, ("A", "B", "C")
        )
        self.assertEqual(snapshot.maximum_history_magnitude, 0.6)
        self.assertEqual(
            dict(snapshot.normalized_histories),
            {"A": 1.0, "B": -1.0, "C": 0.5},
        )

    def test_normalization_rejects_missing_or_nonfinite_histories(self):
        for histories in ({"A": 1.0}, {"A": float("inf"), "B": 0.0}):
            with self.subTest(histories=histories), self.assertRaises(ValueError):
                normalize_sensor_histories(histories, ("A", "B"))


class Phase3AExecutionTests(unittest.TestCase):
    def setUp(self):
        self.sensor_ids = ("A", "C", "D", "E", "F", "G")
        self.start = pd.Timestamp("2022-02-24T18:50:00+00:00")
        self.config = json.loads(json.dumps(PHASE3A_CONFIG))
        self.config["start_timestamp_utc"] = self.start.isoformat()
        self.config["end_timestamp_utc"] = (
            self.start + pd.Timedelta(minutes=2)
        ).isoformat()
        self.config["expected_bucket_count"] = 3
        self.config["expected_elapsed_minutes"] = 2
        self.config["threshold"].update(
            {
                "statistic": "p90",
                "p90_value": 100.0,
                "status": "authoritative",
                "production_script": "scripts/shared_monitoring_engine.py",
            }
        )
        self.frame = self.build_frame(3)

    def build_frame(self, count):
        rows = []
        for offset in range(count):
            timestamp = self.start + pd.Timedelta(minutes=offset)
            row = {
                "bucket_epoch": int(timestamp.timestamp()),
                "bucket_time_utc": timestamp.isoformat(),
            }
            row.update(
                {f"{sensor}_temperature": 20.0 + offset for sensor in self.sensor_ids}
            )
            rows.append(row)
        return pd.DataFrame(rows)

    def runtime(self, phase2_builder):
        def build_events(*args, **kwargs):
            return history_module.build_phase3a_history_events(
                *args, phase2_builder=phase2_builder, **kwargs
            )

        return {
            **vars(history_module),
            "build_phase3a_history_events": build_events,
        }

    @staticmethod
    def controlled_phase2_builder(selected, _sensor_columns, _threshold):
        return pd.DataFrame(
            {
                "bucket_epoch": selected.bucket_epoch,
                "global_state_evaluable": [True] * len(selected),
                "observed_online_sensor_count": [6] * len(selected),
                "event_membership_changed": [0] * len(selected),
                "event_resync_triggered_by_membership_change": [0] * len(selected),
                "event_resync_performed": [1, 0, 1],
                "trigger_message_count": [0, 0, 1],
                "request_message_count": [6, 0, 6],
                "response_message_count": [6, 0, 6],
                "broadcast_message_count": [6, 0, 6],
                "total_message_count": [18, 0, 19],
                "global_violation": [0, 0, 1],
                "event_resync_causes": [
                    "initialization",
                    "",
                    "monitoring_trigger",
                ],
            }
        )

    def build_events(self, threshold=100.0, **kwargs):
        runtime = self.runtime(self.controlled_phase2_builder)
        return runtime["build_phase3a_history_events"](
            self.frame,
            threshold=threshold,
            experiment_config=self.config,
            **kwargs,
        )

    def test_production_baseline_alpha_and_history(self):
        events, baseline = self.build_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events.clustering_event_id.tolist(), [1, 2])
        self.assertEqual(events.alpha.tolist(), [0.10, 0.10])
        self.assertEqual(
            events.iloc[0].normalization_status, "all_zero_history_fallback"
        )
        self.assertEqual(
            json.loads(events.iloc[0].raw_sensor_histories),
            {sensor: 0.0 for sensor in self.sensor_ids},
        )
        self.assertEqual(events.iloc[-1].synchronization_causes, "monitoring_trigger")
        self.assertEqual(
            json.loads(events.iloc[-1].raw_sensor_histories),
            {sensor: 2.5 for sensor in self.sensor_ids},
        )
        self.assertTrue(baseline.event_membership_changed.eq(0).all())
        self.assertNotIn("alpha_clustering_evaluations", events.columns)
        self.assertTrue(events.threshold_status.eq("authoritative").all())

    def test_phase2_rejects_a_threshold_that_disagrees_with_config(self):
        with self.assertRaisesRegex(ValueError, "does not match the authoritative"):
            self.build_events(threshold=100.5)

    def test_full_alpha_sweep_can_be_requested_for_tuning(self):
        events, _ = self.build_events(alpha_values=PHASE3_ALPHA_VALUES)
        self.assertEqual(len(events), 2 * len(PHASE3_ALPHA_VALUES))
        self.assertEqual(
            events.groupby("clustering_event_id").size().tolist(), [19, 19]
        )
        self.assertEqual(
            sorted(events.alpha.unique().tolist()), list(PHASE3_ALPHA_VALUES)
        )

    def test_phase3a_input_rejects_invalid_timestamps_and_values(self):
        prepare = self.runtime(lambda *_: None)["prepare_phase3a_input"]
        selected = prepare(self.frame, self.config)
        self.assertEqual(len(selected), 3)
        self.assertEqual(
            selected.columns.tolist(),
            [
                "bucket_epoch",
                "bucket_time_utc",
                *[f"{sensor}_temperature" for sensor in self.sensor_ids],
            ],
        )

        gap = self.frame.copy()
        gap.loc[1, "bucket_time_utc"] = (
            self.start + pd.Timedelta(seconds=90)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "exactly 60 seconds"):
            prepare(gap, self.config)

        duplicate = self.frame.copy()
        duplicate.loc[1, "bucket_time_utc"] = duplicate.loc[0, "bucket_time_utc"]
        with self.assertRaisesRegex(ValueError, "duplicate timestamps"):
            prepare(duplicate, self.config)

        out_of_order = self.frame.iloc[[0, 2, 1]].reset_index(drop=True)
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            prepare(out_of_order, self.config)

        wrong_start = self.frame.copy()
        wrong_start.loc[0, "bucket_time_utc"] = (
            self.start + pd.Timedelta(seconds=5)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "first timestamp"):
            prepare(wrong_start, self.config)

        wrong_end = self.frame.copy()
        wrong_end.loc[2, "bucket_time_utc"] = (
            self.start + pd.Timedelta(minutes=2) - pd.Timedelta(seconds=5)
        ).isoformat()
        with self.assertRaisesRegex(ValueError, "final timestamp"):
            prepare(wrong_end, self.config)

        with self.assertRaisesRegex(ValueError, "requires 3 buckets"):
            prepare(self.frame.iloc[:-1], self.config)

        mismatch = self.frame.copy()
        mismatch.loc[1, "bucket_epoch"] += 60
        with self.assertRaisesRegex(ValueError, "do not match"):
            prepare(mismatch, self.config)

        missing = self.frame.copy()
        missing.loc[1, "C_temperature"] = np.nan
        with self.assertRaisesRegex(ValueError, "C_temperature"):
            prepare(missing, self.config)

        for value in (np.inf, -np.inf):
            nonfinite = self.frame.copy()
            nonfinite.loc[1, "D_temperature"] = value
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "D_temperature"
            ):
                prepare(nonfinite, self.config)

        missing_column = self.frame.drop(columns=["F_temperature"])
        with self.assertRaisesRegex(ValueError, "F_temperature"):
            prepare(missing_column, self.config)

    def test_config_locks_cohort_and_authoritative_threshold_provenance(self):
        validate = self.runtime(lambda *_: None)["validate_phase3a_config"]
        self.assertEqual(validate(PHASE3A_CONFIG)[0], ("A", "C", "D", "E", "F", "G"))
        self.assertEqual(PHASE3A_CONFIG["baseline_alpha"], 0.1)
        self.assertEqual(
            PHASE3A_CONFIG["threshold"]["source_series"],
            "phase3a_stable_cohort",
        )
        self.assertEqual(PHASE3A_CONFIG["threshold"]["statistic"], "p90")
        self.assertNotIn("p90_value", PHASE3A_CONFIG["threshold"])
        self.assertEqual(PHASE3A_CONFIG["threshold"]["status"], "derived_from_aligned_input")

        modified = json.loads(json.dumps(self.config))
        modified["selected_sensor_ids"] = list("ABDEFG")
        modified["selected_sensor_temperature_columns"] = [
            f"{sensor}_temperature" for sensor in "ABDEFG"
        ]
        with self.assertRaisesRegex(ValueError, "cohort must remain exactly"):
            validate(modified)

    def test_matched_phase2_summary_counts_and_reconciles_messages(self):
        runtime = self.runtime(self.controlled_phase2_builder)
        trace = self.controlled_phase2_builder(self.frame, [], 100.0)
        summary = runtime["build_phase3a_phase2_baseline_summary"](trace, self.config)
        self.assertEqual(summary["bucket_count"], 3)
        self.assertEqual(summary["algorithm"], "phase2")
        self.assertEqual(summary["threshold_value"], 100.0)
        self.assertEqual(summary["total_messages"], 37)
        self.assertEqual(summary["resynchronization_count"], 2)
        self.assertEqual(summary["membership_change_event_count"], 0)
        self.assertEqual(summary["global_evaluation_count"], 3)
        self.assertEqual(
            summary["boundary_convention"], self.config["boundary_convention"]
        )
        self.assertTrue(summary["message_counts_reconcile"])
        self.assertEqual(summary["correctness_status"], "passed")

        bad_trace = trace.copy()
        bad_trace.loc[0, "event_membership_changed"] = 1
        with self.assertRaisesRegex(ValueError, "membership changes"):
            runtime["build_phase3a_phase2_baseline_summary"](bad_trace, self.config)

        bad_trace = trace.copy()
        bad_trace.loc[0, "total_message_count"] = 17
        with self.assertRaisesRegex(ValueError, "do not reconcile"):
            runtime["build_phase3a_phase2_baseline_summary"](bad_trace, self.config)


def paired_clustering(_):
    return {"selected_partition": (("A", "B"),), "partition_quality": 0.2}


class FirstMomentTests(unittest.TestCase):
    def test_discounted_arithmetic_mean_is_not_history_or_ema(self):
        """Chapter section 1.4, printed p.10/PDF p.14: arithmetic mean of V'_n."""
        state = DiscountedFirstMoment(("A", "B"))
        self.assertEqual(state.count, 0)
        self.assertEqual(state.sums, {"A": 0, "B": 0})
        self.assertEqual(state.means(), {"A": 0, "B": 0})
        hand_calculations = (
            ({"A": 2, "B": -4}, {"A": [2], "B": [-4]}, {"A": 2, "B": -4}),
            ({"A": 4, "B": 2}, {"A": [1, 4], "B": [-2, 2]}, {"A": 5, "B": 0}),
            ({"A": 6, "B": 3}, {"A": [0.5, 2, 6], "B": [-1, 1, 3]}, {"A": 8.5, "B": 3}),
        )
        for count, (reading, source_vectors, expected_sums) in enumerate(hand_calculations, start=1):
            with self.subTest(observation=count):
                state.update(reading)
                self.assertEqual(state.count, count)
                self.assertEqual(state.sums, expected_sums)
                for sensor in ("A", "B"):
                    self.assertEqual(sum(source_vectors[sensor]), expected_sums[sensor])
                    self.assertAlmostEqual(
                        state.means()[sensor], expected_sums[sensor] / count, delta=1e-12
                    )
        self.assertNotAlmostEqual(state.means()["A"], 8.5 / (0.25 + 0.5 + 1))

    def test_hand_calculated_weights_and_cluster_allowances(self):
        result = fmic_allocation(
            {"A": -1, "B": 2, "C": 3}, (("A", "B"), ("C",)), 4
        )
        self.assertEqual(result["raw_weights"], {"A": 1, "B": 2, "C": 3})
        self.assertEqual(result["scaled_weights"], {"A": 0.5, "B": 1, "C": 1.5})
        self.assertEqual(result["node_allowances"], {"A": 2, "B": 4, "C": 6})
        self.assertEqual(result["coordinator_allowances"], {"B": 3, "C": 6})
        self.assertEqual(result["weight_status"], "source_first_moment")
        self.assertEqual(sum(result["scaled_weights"].values()), 3)
        self.assertEqual(sum(result["node_allowances"].values()), 3 * 4)
        self.assertEqual(
            2 * result["coordinator_allowances"]["B"] + result["coordinator_allowances"]["C"],
            3 * 4,
        )

    def test_project_all_zero_fallback_and_individual_zero(self):
        result = fmic_allocation({"A": 0, "B": 0}, (("A", "B"),), 3)
        self.assertEqual(result["scaled_weights"], {"A": 1, "B": 1})
        self.assertEqual(result["node_allowances"], {"A": 3, "B": 3})
        self.assertEqual(result["coordinator_allowances"], {"B": 3})
        self.assertEqual(result["weight_status"], "project_all_zero_equal_weight_fallback")
        result = fmic_allocation({"A": 0, "B": 2}, (("A", "B"),), 3)
        self.assertEqual(result["scaled_weights"], {"A": 0, "B": 2})
        self.assertEqual(result["node_allowances"], {"A": 0, "B": 6})
        self.assertEqual(result["weight_status"], "source_first_moment")

    def test_invalid_inputs_are_explicit(self):
        for moments, partition, allowance in (
            ({}, (), 1),
            ({"A": math.nan}, (("A",),), 1),
            ({"A": 1}, (("A",),), -1),
            ({"A": 1}, (("A", "A"),), 1),
            ({"A": 1}, ((), ("A",)), 1),
        ):
            with self.subTest(moments=moments, partition=partition):
                with self.assertRaises(ValueError):
                    fmic_allocation(moments, partition, allowance)


class SecondMomentTests(unittest.TestCase):
    def test_source_discounted_squared_deviations_and_weights_by_hand(self):
        """Appendix 1 pp.22,24/PDF 26,28: sigma^2 has NO m or m-1 divisor."""
        state = DiscountedSecondMoment(("A", "B"))
        first_only = DiscountedFirstMoment(("A", "B"))
        calculations = (
            ({"A": 2, "B": -4}, {"A": [2], "B": [-4]},
             {"A": 2, "B": -4}, {"A": [0], "B": [0]},
             {"A": 0, "B": 0}, {"A": 2, "B": 4}),
            ({"A": 4, "B": 2}, {"A": [1, 4], "B": [-2, 2]},
             {"A": 5 / 2, "B": 0}, {"A": [9 / 4, 9 / 4], "B": [4, 4]},
             {"A": 9 / 2, "B": 8}, {"A": 4, "B": 2}),
            ({"A": 6, "B": 3}, {"A": [0.5, 2, 6], "B": [-1, 1, 3]},
             {"A": 17 / 6, "B": 1}, {"A": [49 / 9, 25 / 36, 361 / 36], "B": [4, 0, 4]},
             {"A": 97 / 6, "B": 8}, {"A": 17 / 6 + math.sqrt(97 / 9), "B": 1 + math.sqrt(16 / 3)}),
        )
        for count, (reading, vectors, means, squares, seconds, weights) in enumerate(calculations, 1):
            with self.subTest(count=count):
                state.update(reading)
                first_only.update(reading)
                self.assertEqual(state.count, count)
                self.assertEqual(state.sums, first_only.sums)
                allocation = smic_allocation(state.means(), state.second_moments, count, (("A", "B"),), 3)
                for sensor in state.sums:
                    self.assertAlmostEqual(sum(vectors[sensor]) / count, means[sensor], delta=1e-12)
                    for observation, square in zip(vectors[sensor], squares[sensor]):
                        self.assertAlmostEqual((observation - means[sensor]) ** 2, square, delta=1e-12)
                    self.assertAlmostEqual(sum(squares[sensor]), seconds[sensor], delta=1e-12)
                    self.assertAlmostEqual(state.means()[sensor], means[sensor], delta=1e-12)
                    self.assertAlmostEqual(state.second_moments[sensor], seconds[sensor], delta=1e-12)
                    self.assertAlmostEqual(
                        allocation["conservative_terms"][sensor],
                        math.sqrt((count - 1) / count * seconds[sensor]), delta=1e-12,
                    )
                    self.assertAlmostEqual(allocation["raw_weights"][sensor], weights[sensor], delta=1e-12)

    def test_running_state_matches_explicit_discounted_set(self):
        state = DiscountedSecondMoment(("A",))
        vectors = []
        generator = random.Random(320)
        for index in range(250):
            value = generator.uniform(-50, 50)
            vectors = [item / 2 for item in vectors] + [value]
            state.update({"A": value})
            mean = math.fsum(vectors) / len(vectors)
            second = math.fsum((item - mean) ** 2 for item in vectors)
            with self.subTest(index=index):
                self.assertAlmostEqual(state.means()["A"], mean, delta=1e-12)
                self.assertAlmostEqual(state.second_moments["A"], second, delta=1e-10)
                self.assertGreaterEqual(state.second_moments["A"], 0)
        self.assertEqual(set(vars(state)), {"sums", "count", "second_moments"})

    def test_initialization_singleton_zero_fallback_and_individual_zero(self):
        state = DiscountedSecondMoment(("A", "B"))
        for count in (0, 1, 2):
            if count:
                state.update({"A": 0, "B": 0})
            result = smic_allocation(state.means(), state.second_moments, state.count, (("A", "B"),), 3)
            self.assertEqual(result["weight_status"], "project_all_zero_equal_weight_fallback")
            self.assertEqual(result["scaled_weights"], {"A": 1, "B": 1})
            self.assertEqual(result["node_allowances"], {"A": 3, "B": 3})
            self.assertEqual(result["conservative_terms"], {"A": 0, "B": 0})
        state = DiscountedSecondMoment(("A", "B"))
        state.update({"A": 0, "B": 2})
        result = smic_allocation(state.means(), state.second_moments, 1, (("A", "B"),), 3)
        self.assertEqual(result["scaled_weights"], {"A": 0, "B": 2})
        self.assertEqual(result["node_allowances"], {"A": 0, "B": 6})
        self.assertEqual(result["weight_status"], "source_first_plus_second_moment")
        # A zero signed mean need not imply a zero SMIC weight.
        result = smic_allocation({"A": 0, "B": 2}, {"A": 8, "B": 0}, 2, (("A", "B"),), 3)
        self.assertEqual(result["raw_weights"], {"A": 2, "B": 2})

    def test_hand_calculated_budget_and_cluster_means(self):
        result = smic_allocation(
            {"A": -1, "B": 2, "C": 3}, {"A": 2, "B": 8, "C": 18},
            2, (("A", "B"), ("C",)), 4,
        )
        self.assertEqual(result["raw_weights"], {"A": 2, "B": 4, "C": 6})
        self.assertEqual(result["scaled_weights"], {"A": 0.5, "B": 1, "C": 1.5})
        self.assertEqual(sum(result["scaled_weights"].values()), 3)
        self.assertEqual(result["node_allowances"], {"A": 2, "B": 4, "C": 6})
        self.assertEqual(sum(result["node_allowances"].values()), 12)
        self.assertEqual(result["coordinator_allowances"], {"B": 3, "C": 6})

    def test_invalid_second_moments_counts_and_overflow_are_explicit(self):
        for means, seconds, count in (
            ({"A": 1}, {"A": -1e-16}, 2),
            ({"A": 1}, {"A": math.inf}, 2),
            ({"A": math.nan}, {"A": 0}, 2),
            ({"A": 1}, {"B": 0}, 2),
            ({"A": 0}, {"A": 0}, -1),
            ({"A": 0}, {"A": 0}, True),
            ({"A": 0}, {"A": 0}, 1.5),
            ({"A": 1}, {"A": 0}, 0),
            ({"A": 0}, {"A": 1}, 0),
            ({"A": 1}, {"A": 1}, 1),
        ):
            with self.subTest(means=means, seconds=seconds, count=count):
                with self.assertRaises(ValueError):
                    smic_allocation(means, seconds, count, (("A",),), 1)
        state = DiscountedSecondMoment(("A",))
        for invalid in ({}, {"A": math.inf}, {"A": True}):
            with self.assertRaises(ValueError):
                state.update(invalid)
            self.assertEqual(state.count, 0)
        state.update({"A": 1e150})
        with self.assertRaisesRegex(ValueError, "second moments"):
            state.update({"A": -1e308})


class FMICProtocolTests(unittest.TestCase):
    weight_method = "FMIC"

    def monitor(self, threshold=1):
        return FMICMonitor(
            ("A", "B"), threshold, clustering=paired_clustering,
            weight_method=self.weight_method,
        )

    def step(self, monitor, a, b):
        index = monitor.rows
        return monitor.step({"A": a, "B": b}, f"row-{index}", index * 60)

    def test_no_trigger_and_initialization(self):
        monitor = self.monitor()
        initial = self.step(monitor, 0, 0)
        self.assertEqual(initial["total_messages"], 6)
        self.assertTrue(initial["synchronized"])
        self.assertEqual(monitor.events[0]["weight_status"], "project_all_zero_equal_weight_fallback")
        self.assertEqual(json.loads(monitor.events[0]["raw_sensor_histories"]), {"A": 0, "B": 0})
        for a, b in ((0.1, 0.2), (-0.5, 0.3)):
            row = self.step(monitor, a, b)
            self.assertEqual(row["total_messages"], 0)
            self.assertEqual(row["node_triggers"], 0)
            self.assertFalse(row["synchronized"])
            self.assertEqual(monitor.allocation["node_allowances"], {"A": 1, "B": 1})
        self.assertEqual(monitor.summary()["root_synchronization_count"], 1)

    def test_decision_trace_captures_entry_state_triggers_and_next_bucket_updates(self):
        monitor = FMICMonitor(
            ("A", "B"), 1, clustering=paired_clustering, capture_decisions=True
        )
        self.step(monitor, 0, 0)
        self.step(monitor, 1.5, -0.75)
        self.step(monitor, 3, 0)

        initial, silent, synchronized = monitor.decision_trace
        self.assertIsNone(initial["entry_known_state"])
        self.assertEqual(initial["root_known_state"], "SAFE")
        self.assertEqual(silent["entry_references"], {"A": 0.0, "B": 0.0})
        self.assertEqual(silent["entry_node_allowances"], {"A": 1.0, "B": 1.0})
        self.assertEqual(silent["triggering_sensor_ids"], ("A",))
        self.assertFalse(silent["synchronized"])
        self.assertEqual(synchronized["triggering_sensor_ids"], ("A",))
        self.assertTrue(synchronized["synchronized"])
        self.assertEqual(synchronized["post_references"], {"A": 3.0, "B": 0.0})
        self.assertEqual(synchronized["total_messages"], sum(synchronized["messages"].values()))

    def test_global_mean_uses_phase2_ordered_builtin_sum(self):
        def singleton_partition(_):
            return {
                "selected_partition": (("A",), ("B",), ("C",)),
                "partition_quality": 0.0,
            }

        monitor = FMICMonitor(
            ("C", "A", "B"), 0.5, clustering=singleton_partition,
            capture_decisions=True,
        )
        monitor.step({"A": 0, "B": 0, "C": 0}, "initial", 0)
        readings = {"A": 1e16, "B": 1.0, "C": -1e16}
        monitor.step(readings, "ordered-sum", 60)

        expected_mean = sum(readings[sensor] for sensor in sorted(readings)) / 3
        self.assertEqual(monitor.decision_trace[-1]["observed_global_average"], expected_mean)
        self.assertEqual(
            monitor.decision_trace[-1]["global_violated"], expected_mean >= monitor.threshold
        )

    def test_fresh_alpha_runs_are_independent_of_iteration_order(self):
        alphas = tuple(step / 20 for step in range(1, 20))
        observations = ((0, 0), (0.1, -0.1), (0.25, -0.2), (-0.1, 0.3))

        def run_in_order(values):
            output = {}
            for alpha in values:
                monitor = FMICMonitor(
                    ("A", "B"), 10, alpha, clustering=paired_clustering,
                    weight_method=self.weight_method,
                )
                steps = [
                    monitor.step({"A": a, "B": b}, f"row-{index}", index * 60)
                    for index, (a, b) in enumerate(observations)
                ]
                output[alpha] = {
                    "steps": steps,
                    "events": monitor.events,
                    "summary": monitor.summary(),
                }
            return output

        forward = run_in_order(alphas)
        reverse = run_in_order(reversed(alphas))
        self.assertEqual(forward, reverse)

    def test_safe_cancellation_and_unsafe_partial_cancellation_hand_count(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        safe = self.step(monitor, 1.5, -0.75)
        self.assertEqual(safe["node_triggers"], 1)
        self.assertEqual(safe["coordinator_checks"], 1)
        self.assertEqual(safe["messages"]["node_trigger_messages"], 1)
        self.assertEqual(safe["messages"]["cluster_check_requests"], 0)
        self.assertEqual(safe["messages"]["cluster_check_responses"], 0)
        self.assertEqual(safe["coordinator_escalations"], 0)
        self.assertFalse(safe["synchronized"])
        unsafe = self.step(monitor, 3, 0)
        self.assertTrue(unsafe["synchronized"])
        self.assertTrue(unsafe["global_violated"])
        self.assertEqual(unsafe["messages"]["coordinator_root_escalations"], 1)
        self.assertEqual(unsafe["total_messages"], 8)
        summary = monitor.summary()
        self.assertEqual(summary["message_category_totals"], {
            "node_trigger_messages": 2, "cluster_check_requests": 0,
            "cluster_check_responses": 0, "coordinator_root_escalations": 1,
            "root_sync_requests": 4, "root_sync_responses": 4, "root_state_updates": 4,
        })
        self.assertEqual(summary["total_messages"], 15)
        self.assertEqual(summary["total_messages"], sum(summary["message_category_totals"].values()))
        self.assertEqual(summary["root_synchronization_count"], 2)

    def test_coordinator_trigger_collects_peer_not_itself(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        row = self.step(monitor, -0.75, 1.5)
        self.assertEqual(row["messages"]["node_trigger_messages"], 0)
        self.assertEqual(row["messages"]["cluster_check_requests"], 1)
        self.assertEqual(row["messages"]["cluster_check_responses"], 1)
        self.assertEqual(row["total_messages"], 2)
        self.assertFalse(row["synchronized"])

    def test_collection_and_escalation_complete_hand_count(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)  # 2 requests + 2 responses + 2 updates.
        self.step(monitor, -0.75, 1.5)  # Coordinator asks A: request + response.
        self.step(monitor, 3, 0)  # A reports, B escalates, root exchanges six.
        self.assertEqual(monitor.messages, {
            "node_trigger_messages": 1, "cluster_check_requests": 1,
            "cluster_check_responses": 1, "coordinator_root_escalations": 1,
            "root_sync_requests": 4, "root_sync_responses": 4, "root_state_updates": 4,
        })
        self.assertEqual(monitor.summary()["total_messages"], 16)

    def test_explicit_transmission_ledger_matches_categories(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        self.step(monitor, 1.5, -0.75)
        self.step(monitor, 3, 0)
        ledger = [
            ("root", "A", "initial synchronization request", "root_sync_requests"),
            ("root", "B", "initial synchronization request", "root_sync_requests"),
            ("A", "root", "initial synchronization response", "root_sync_responses"),
            ("B", "root", "initial synchronization response", "root_sync_responses"),
            ("root", "A", "initial root state update", "root_state_updates"),
            ("root", "B", "initial root state update", "root_state_updates"),
            ("A", "B", "safe-cancellation node trigger", "node_trigger_messages"),
            ("A", "B", "escalating node trigger", "node_trigger_messages"),
            ("B", "root", "coordinator escalation", "coordinator_root_escalations"),
            ("root", "A", "root synchronization request", "root_sync_requests"),
            ("root", "B", "root synchronization request", "root_sync_requests"),
            ("A", "root", "root synchronization response", "root_sync_responses"),
            ("B", "root", "root synchronization response", "root_sync_responses"),
            ("root", "A", "root state update", "root_state_updates"),
            ("root", "B", "root state update", "root_state_updates"),
        ]
        self.assertTrue(all(sender != recipient for sender, recipient, _, _ in ledger))
        expected = dict.fromkeys(monitor.messages, 0)
        expected.update(Counter(category for _, _, _, category in ledger))
        self.assertEqual(expected, monitor.messages)
        self.assertEqual(len(ledger), monitor.summary()["total_messages"])

    def test_singleton_cluster_does_not_send_peer_or_self_messages(self):
        monitor = FMICMonitor(("A",), 1, weight_method=self.weight_method)
        initial = monitor.step({"A": 0}, "row-0", 0)
        self.assertEqual(initial["total_messages"], 3)
        row = monitor.step({"A": 1}, "row-1", 60)
        self.assertTrue(row["synchronized"])
        self.assertEqual(row["node_triggers"], 1)
        self.assertEqual(row["coordinator_checks"], 1)
        self.assertEqual(row["coordinator_escalations"], 1)
        self.assertEqual(row["messages"], {
            "node_trigger_messages": 0,
            "cluster_check_requests": 0,
            "cluster_check_responses": 0,
            "coordinator_root_escalations": 1,
            "root_sync_requests": 1,
            "root_sync_responses": 1,
            "root_state_updates": 1,
        })
        self.assertEqual(row["total_messages"], 4)

    def test_simultaneous_triggers_do_not_duplicate_cluster_or_root_checks(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        row = self.step(monitor, 1, 1)
        self.assertEqual(row["node_triggers"], 2)
        self.assertEqual(row["coordinator_checks"], 1)
        self.assertEqual(row["coordinator_escalations"], 1)
        self.assertEqual(row["total_messages"], 8)
        monitor = FMICMonitor(("A", "B"), 1)
        self.step(monitor, 0, 0)
        row = self.step(monitor, 1, 1)
        self.assertEqual(row["coordinator_checks"], 2)
        self.assertEqual(row["coordinator_escalations"], 2)
        self.assertEqual(row["messages"]["root_sync_requests"], 2)
        self.assertEqual(row["total_messages"], 8)

    def test_coordinator_and_node_boundary_below_equal_above(self):
        for value, expected in (
            (math.nextafter(1.0, 0), False), (1.0, True),
            (math.nextafter(1.0, math.inf), True),
        ):
            with self.subTest(value=value):
                monitor = self.monitor()
                self.step(monitor, 0, 0)
                row = self.step(monitor, value, value)
                self.assertEqual(row["synchronized"], expected)
                self.assertEqual(row["global_violated"], expected)

    def test_global_boundary_and_violated_to_safe_crossing(self):
        monitor = self.monitor()
        self.step(monitor, 2, 2)
        self.assertTrue(monitor.known_violated)
        no_trigger = self.step(monitor, 1.5, 1.5)
        self.assertFalse(no_trigger["synchronized"])
        boundary = self.step(monitor, 1, 1)
        self.assertTrue(boundary["synchronized"])
        self.assertTrue(boundary["known_violated"])
        self.assertEqual(monitor.events[-1]["root_allowance"], 0)
        below = self.step(monitor, math.nextafter(1, 0), math.nextafter(1, 0))
        self.assertTrue(below["synchronized"])
        self.assertFalse(below["known_violated"])

    def test_history_and_first_moment_persist_across_sync(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        self.step(monitor, 1.5, -0.75)
        self.step(monitor, 3, 0)
        event = monitor.events[-1]
        self.assertEqual(json.loads(event["raw_sensor_histories"]), {"A": 3.75, "B": -0.375})
        self.assertEqual(json.loads(event["first_moments"]), {"A": 1.875, "B": -0.1875})
        self.assertEqual(monitor.references, {"A": 3, "B": 0})
        self.assertEqual(monitor.moment.count, 2)
        self.step(monitor, 4, 1)
        self.assertEqual(monitor.history.histories, {"A": 2.875, "B": 0.8125})
        self.assertEqual(monitor.moment.count, 3)
        self.assertEqual(monitor.moment.means(), {"A": 5.875 / 3, "B": 0.8125 / 3})

    def test_centralized_truth_never_drives_protocol_and_false_safe_blocks(self):
        monitor = self.monitor()
        self.step(monitor, 0, 0)
        monitor.allocation["node_allowances"] = {"A": 100, "B": 100}
        with self.assertRaisesRegex(RuntimeError, "false-safe"):
            self.step(monitor, 2, 2)
        self.assertEqual(len(monitor.events), 1)
        summary = monitor.summary()
        self.assertEqual(summary["false_safe_count"], 1)
        self.assertEqual(summary["correctness_status"], "failed")

    def test_many_synthetic_crossings_use_real_clustering_and_zero_false_safe(self):
        generator = random.Random(7319)
        monitor = FMICMonitor(tuple("ACDEFG"), 0.5)
        violations = 0
        for index in range(500):
            values = {sensor: generator.uniform(-2, 2) for sensor in monitor.sensors}
            truth = math.fsum(values.values()) / 6 >= 0.5
            result = monitor.step(values, str(index), index * 60)
            self.assertEqual(result["global_violated"], truth)
            self.assertEqual(result["known_violated"], truth)
            self.assertFalse(result["false_safe"])
            violations += truth
        summary = monitor.summary()
        self.assertEqual(summary["global_threshold_violation_count"], violations)
        self.assertEqual(summary["false_safe_count"], 0)
        self.assertEqual(summary["correctness_status"], "passed")
        self.assertEqual(set(summary["message_category_totals"]), set(MESSAGE_CATEGORIES))
        self.assertEqual(summary["total_messages"], sum(monitor.messages.values()))

    def test_correctness_status_requires_zero_mismatches_in_both_directions(self):
        for false_safe, false_violated, expected in (
            (0, 0, "passed"),
            (1, 0, "failed"),
            (0, 1, "failed"),
            (1, 1, "failed"),
        ):
            with self.subTest(false_safe=false_safe, false_violated=false_violated):
                monitor = self.monitor()
                self.step(monitor, 0, 0)
                monitor.false_safe = false_safe
                monitor.false_violated = false_violated
                summary = monitor.summary()
                self.assertEqual(summary["false_safe_count"], false_safe)
                self.assertEqual(summary["false_violated_count"], false_violated)
                self.assertEqual(summary["correctness_status"], expected)

    def test_false_violated_observation_fails_summary_without_false_safe(self):
        monitor = self.monitor()
        self.step(monitor, 2, 2)
        monitor.allocation["node_allowances"] = {"A": 100, "B": 100}
        row = self.step(monitor, 0, 0)
        self.assertFalse(row["synchronized"])
        self.assertFalse(row["global_violated"])
        self.assertTrue(row["known_violated"])
        summary = monitor.summary()
        self.assertEqual(summary["false_safe_count"], 0)
        self.assertEqual(summary["false_violated_count"], 1)
        self.assertEqual(summary["correctness_status"], "failed")

    def test_invalid_readings_fail_before_processing(self):
        monitor = self.monitor()
        for readings in (
            {"A": 1}, {"A": 1, "B": math.inf},
            {"A": True, "B": 0}, {"A": "1", "B": 0},
        ):
            with self.assertRaises(ValueError):
                monitor.step(readings, "invalid", 0)
        self.assertEqual(monitor.rows, 0)


class ProductionIntegrationTests(unittest.TestCase):
    def test_only_three_phase3_executable_files_remain(self):
        repository = Path(__file__).resolve().parents[1]
        self.assertEqual(
            {path.name for path in (repository / "scripts").iterdir()
             if "phase3" in path.stem and path.suffix in (".py", ".ipynb")
             and not path.name.startswith("test_phase1_")},
            {"phase3_implement.py", "phase3_test.py", "phase3_analyze.ipynb"},
        )
        for name in (
            "Phase3AHistoryTracker", "evaluate_alpha_clustering",
            "fmic_allocation", "FMICMonitor", "run_phase3a_fmic",
            "build_phase3a_history_events", "build_phase3a_phase2_baseline_summary",
        ):
            self.assertEqual(getattr(history_module, name).__module__, "scripts.phase3_implement")

    def test_clean_process_import_does_not_read_inputs_or_execute_or_write_outputs(self):
        repository = Path(__file__).resolve().parents[1]
        code = """
import builtins
import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import numpy
import pandas
import scripts.shared_monitoring_engine

def forbidden(*args, **kwargs):
    raise AssertionError("Import performed runtime I/O or launched a process")

def guarded_open(original):
    def guard(file, mode="r", *args, **kwargs):
        if isinstance(file, (str, bytes, os.PathLike)):
            path = str(file)
            if not path.endswith((".py", ".pyc")) or any(flag in mode for flag in "wax+"):
                return forbidden(file, mode)
        return original(file, mode, *args, **kwargs)
    return guard

with patch.object(builtins, "open", guarded_open(builtins.open)), \\
     patch.object(io, "open", guarded_open(io.open)), \\
     patch.object(pandas, "read_csv", forbidden), \\
     patch.object(pandas.DataFrame, "to_csv", forbidden), \\
     patch.object(Path, "mkdir", forbidden), \\
     patch.object(subprocess, "run", forbidden), \\
     patch.object(subprocess, "Popen", forbidden):
    import scripts.phase3_implement as implementation
assert callable(implementation.main)
assert "matplotlib.pyplot" not in sys.modules
print("import-safe")
"""
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ, PYTHONPATH=str(repository))
            result = subprocess.run(
                [sys.executable, "-B", "-c", code],
                cwd=temporary, env=environment, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "import-safe")
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_runner_validates_provenance_preserves_baseline_and_exports_only_compact_files(self):
        repository = Path(__file__).resolve().parents[1]
        config = json.loads((repository / "config" / "phase3a_experiment_config.json").read_text())
        baseline = {
            key: config[key] for key in (
                "experiment_name", "input_source", "selected_sensor_ids",
                "start_timestamp_utc", "end_timestamp_utc", "endpoint_convention",
                "boundary_convention",
            )
        }
        baseline.update({
            "algorithm": "phase2", "threshold_source_series": "phase3a_stable_cohort",
            "correctness_status": "passed", "total_messages": 36,
            "message_category_totals": {
                "trigger_message_count": 0, "request_message_count": 12,
                "response_message_count": 12, "broadcast_message_count": 12,
            },
            "resynchronization_count": 2,
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config").mkdir()
            (root / "artifacts").mkdir()
            references = implementation._phase3_reference_directory(root)
            references.mkdir(parents=True)
            legacy_runs = implementation._phase3_operational_directory(root) / "legacy_runs"
            times = pd.date_range(config["start_timestamp_utc"], periods=3, freq="min")
            config["end_timestamp_utc"] = times[-1].isoformat()
            config["expected_bucket_count"] = 3
            config["expected_elapsed_minutes"] = 2
            (root / "config" / "phase3a_experiment_config.json").write_text(json.dumps(config))
            frame = pd.DataFrame({
                "bucket_epoch": [int(time.timestamp()) for time in times],
                "bucket_time_utc": [time.isoformat() for time in times],
                **{f"{sensor}_temperature": [0.0, 0.1, 2.0] for sensor in config["selected_sensor_ids"]},
            })
            (root / config["input_source"]).parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(root / config["input_source"], index=False)
            publication = root / "artifacts" / "phase1_operational" / "phase1_run.json"
            publication.parent.mkdir(parents=True, exist_ok=True)
            (root / "scripts").mkdir()
            for relative in ("scripts/phase1_implement.ipynb", "config/transformation_defaults.yaml"):
                (root / relative).write_bytes((Path(__file__).resolve().parents[1] / relative).read_bytes())
            publication.write_text(json.dumps({
                "schema_version": 1, "limited_run": False, "status": "passed", "hashes": {
                    "phase1_aligned_sha256": hashlib.sha256((root / config["input_source"]).read_bytes()).hexdigest(),
                },
                "implementation_sha256": hashlib.sha256((root / "scripts" / "phase1_implement.ipynb").read_bytes()).hexdigest(),
                "config_sha256": hashlib.sha256((root / "config" / "transformation_defaults.yaml").read_bytes()).hexdigest(),
            }))
            baseline.update({
                "end_timestamp_utc": config["end_timestamp_utc"], "bucket_count": 3,
                "threshold_value": 0.1 * (1 - 0.8) + 2.0 * 0.8, "global_violation_count": 1,
            })
            baseline_path = references / "phase3a_phase2_baseline.json"
            baseline_path.write_text(json.dumps(baseline))
            original = baseline_path.read_bytes()
            summary = run_phase3a_fmic(root)
            self.assertEqual(summary["bucket_count"], 3)
            self.assertEqual(summary["global_threshold_violation_count"], 1)
            self.assertEqual(summary["false_safe_count"], 0)
            self.assertEqual(summary["root_synchronization_count"], 2)
            self.assertEqual(baseline_path.read_bytes(), original)
            events = pd.read_csv(legacy_runs / "phase3a_fmic_events.csv")
            self.assertEqual(len(events), 2)
            self.assertTrue(events["algorithm"].eq("FMIC").all())
            self.assertTrue(events["alpha"].eq(0.1).all())
            persisted = json.loads((legacy_runs / "phase3a_fmic_summary.json").read_text())
            self.assertEqual(summary, persisted)
            self.assertEqual(
                {path.name for path in (root / "artifacts").iterdir()},
                {
                    "phase1_operational",
                    "phase3_operational",
                },
            )
            fmic_files = {
                name: (legacy_runs / name).read_bytes()
                for name in ("phase3a_fmic_events.csv", "phase3a_fmic_summary.json")
            }
            smic = run_phase3a_smic(root)
            self.assertEqual(smic["algorithm"], "SMIC")
            self.assertEqual(smic["bucket_count"], 3)
            self.assertEqual(smic["false_safe_count"], 0)
            self.assertEqual(smic["false_violated_count"], 0)
            self.assertEqual(smic["correctness_status"], "passed")
            self.assertEqual(smic["root_synchronization_count"], 2)
            for category in ("root_sync_requests", "root_sync_responses", "root_state_updates"):
                self.assertEqual(smic["message_category_totals"][category], 12)
            self.assertIn("fixed-alpha", smic["comparison_status"])
            self.assertEqual(smic["total_messages"], sum(smic["message_category_totals"].values()))
            smic_events = pd.read_csv(legacy_runs / "phase3a_smic_events.csv")
            self.assertTrue(smic_events["algorithm"].eq("SMIC").all())
            self.assertEqual(len(smic_events), smic["root_synchronization_count"])
            self.assertTrue({"second_moments", "conservative_terms"}.issubset(smic_events.columns))
            self.assertEqual(
                json.loads((legacy_runs / "phase3a_smic_summary.json").read_text()), smic
            )
            self.assertEqual(baseline_path.read_bytes(), original)
            for name in ("phase3a_fmic_events.csv", "phase3a_fmic_summary.json"):
                shutil.copy2(legacy_runs / name, references / name)
            for name in ("phase3a_smic_events.csv", "phase3a_smic_summary.json"):
                shutil.copy2(legacy_runs / name, references / name)
            for name, content in fmic_files.items():
                self.assertEqual((legacy_runs / name).read_bytes(), content)
            self.assertEqual(
                {path.name for path in (root / "artifacts").iterdir()},
                {
                    "phase1_operational",
                    "phase3_operational",
                },
            )
            with self.assertRaisesRegex(ValueError, "explicit output directory"):
                run_phase3a_fmic(root, 0.2)
            (references / "phase3a_validation_summary.json").write_text(json.dumps({
                "story": "US-3.21",
                "test_result": {"status": "passed", "tests": 91},
                "production_replays": [
                    {"correctness_status": "passed", "message_counts_reconcile": True},
                    {"correctness_status": "passed", "message_counts_reconcile": True},
                ],
            }))
            protected = {
                name: (references / name).read_bytes()
                for name in (
                    "phase3a_phase2_baseline.json",
                    "phase3a_fmic_events.csv",
                    "phase3a_fmic_summary.json",
                    "phase3a_smic_events.csv",
                    "phase3a_smic_summary.json",
                )
            }
            sweep = run_phase3a_alpha_sweep(root)
            self.assertEqual(sweep["run_count"], 38)
            self.assertEqual(sweep["alpha_grid"][0], "0.05")
            self.assertEqual(sweep["alpha_grid"][-1], "0.95")
            self.assertEqual(sweep["us321_validation"]["status"], "passed")
            results_path = legacy_runs / "phase3a_alpha_results.csv"
            results = pd.read_csv(results_path, dtype={"alpha_label": str})
            self.assertEqual(len(results), 38)
            self.assertEqual(results.groupby("algorithm")["alpha_label"].nunique().to_dict(), {
                "FMIC": 19, "SMIC": 19,
            })
            self.assertTrue(results["correctness_status"].eq("passed").all())
            self.assertTrue(
                all(
                    json.loads(value) == config["selected_sensor_ids"]
                    for value in results["selected_sensor_ids"]
                )
            )
            self.assertTrue(results["start_timestamp_utc"].eq(config["start_timestamp_utc"]).all())
            self.assertTrue(results["end_timestamp_utc"].eq(config["end_timestamp_utc"]).all())
            self.assertTrue(
                results["endpoint_convention"].eq(config["endpoint_convention"]).all()
            )
            self.assertTrue(
                results["reconciled_total_messages"].eq(results["total_messages"]).all()
            )
            sweep_events = pd.read_csv(
                legacy_runs / "phase3a_alpha_events.csv",
                dtype={"alpha_label": str},
            )
            self.assertEqual(set(sweep_events["alpha_label"].unique()), set(sweep["alpha_grid"]))
            for row in results.itertuples():
                selected_events = sweep_events.loc[
                    (sweep_events["algorithm"] == row.algorithm)
                    & (sweep_events["alpha_label"] == row.alpha_label)
                ]
                partitions = [
                    json.loads(value) for value in selected_events["selected_partition"]
                ]
                cluster_sizes = [
                    len(cluster) for partition in partitions for cluster in partition
                ]
                self.assertAlmostEqual(
                    row.cluster_size_mean_across_sync_clusters,
                    sum(cluster_sizes) / len(cluster_sizes),
                )
                self.assertAlmostEqual(
                    row.cluster_count_mean_per_sync_event,
                    sum(len(partition) for partition in partitions) / len(partitions),
                )
            for name, content in protected.items():
                self.assertEqual((references / name).read_bytes(), content)
            for plot in sweep["outputs"]["plots"]:
                self.assertTrue((legacy_runs / plot).is_file())
            baseline["threshold_value"] = 2
            baseline_path.write_text(json.dumps(baseline))
            with self.assertRaisesRegex(ValueError, "Invalid matched Phase 2"):
                run_phase3a_fmic(root)
            with self.assertRaisesRegex(ValueError, "Invalid matched Phase 2"):
                run_phase3a_smic(root)
            baseline_path.write_bytes(original)
            publication.write_text('{"status":"failed"}')
            with self.assertRaisesRegex(ValueError, "publication"):
                run_phase3a_fmic(root)
            with self.assertRaisesRegex(ValueError, "publication"):
                run_phase3a_smic(root)

    def test_fmic_synthetic_protocol_matches_pre_smic_fingerprint(self):
        generator = random.Random(7320)
        monitor = FMICMonitor(tuple("ACDEFG"), 0.5)
        rows = []
        for index in range(500):
            values = {sensor: generator.uniform(-2, 2) for sensor in monitor.sensors}
            rows.append(monitor.step(values, str(index), index * 60))
        payload = {"steps": rows, "events": monitor.events, "summary": monitor.summary()}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        self.assertEqual(digest, "674fe5379e9ff0554a36367750555625f932bafb7ccc802dea801d5961eba5bb")


class SMICProtocolTests(FMICProtocolTests):
    """Run the same hand-counted protocol/boundary/failure cases with SMIC."""

    weight_method = "SMIC"

    def monitor(self, threshold=1):
        return FMICMonitor(("A", "B"), threshold, clustering=paired_clustering, weight_method="SMIC")

    def test_history_and_first_moment_persist_across_sync(self):
        super().test_history_and_first_moment_persist_across_sync()
        monitor = self.monitor(threshold=11)
        observations = ((10, 10), (11.5, 9.25), (13, 10), (14, 11), (8, 8))
        vectors = {"A": [], "B": []}
        prior_references = {}
        histories = {"A": 0.0, "B": 0.0}
        for index, (a, b) in enumerate(observations):
            values = {"A": a, "B": b}
            if index:
                for sensor, value in values.items():
                    vectors[sensor] = [item / 2 for item in vectors[sensor]] + [value]
                    histories[sensor] = 0.5 * histories[sensor] + value - prior_references[sensor]
            row = self.step(monitor, a, b)
            self.assertEqual(monitor.moment.count, index)
            self.assertEqual(monitor.history.histories, histories)
            for sensor in values:
                mean = math.fsum(vectors[sensor]) / index if index else 0
                second = math.fsum((item - mean) ** 2 for item in vectors[sensor])
                self.assertAlmostEqual(monitor.moment.means()[sensor], mean, delta=1e-12)
                self.assertAlmostEqual(monitor.moment.second_moments[sensor], second, delta=1e-12)
            if row["synchronized"]:
                prior_references = values
                event = monitor.events[-1]
                self.assertEqual(json.loads(event["second_moments"]), monitor.moment.second_moments)
                self.assertEqual(json.loads(event["first_moments"]), monitor.moment.means())
                self.assertEqual(json.loads(event["raw_sensor_histories"]), histories)
        self.assertGreaterEqual(len(monitor.events), 3)
        self.assertNotEqual(monitor.history.histories, monitor.moment.means())

    def test_many_synthetic_crossings_use_real_clustering_and_zero_false_safe(self):
        generator = random.Random(7320)
        monitor = FMICMonitor(tuple("ACDEFG"), 0.5, weight_method="SMIC")
        for index in range(500):
            values = {sensor: generator.uniform(-2, 2) for sensor in monitor.sensors}
            result = monitor.step(values, str(index), index * 60)
            self.assertEqual(result["known_violated"], math.fsum(values.values()) / 6 >= 0.5)
        summary = monitor.summary()
        self.assertEqual(summary["false_safe_count"], 0)
        self.assertEqual(summary["false_violated_count"], 0)
        self.assertEqual(summary["correctness_status"], "passed")
        self.assertEqual(summary["total_messages"], sum(summary["message_category_totals"].values()))

    def test_identical_allocations_give_identical_shared_engine_decisions(self):
        def fixed_strategy(moment, partition, root_allowance):
            return {
                **fmic_allocation({"A": 1, "B": 1}, partition, root_allowance),
                "second_moments": dict.fromkeys(moment.sums, 0),
                "conservative_terms": dict.fromkeys(moment.sums, 0),
            }

        monitors = [
            FMICMonitor(("A", "B"), 1, clustering=paired_clustering,
                        weight_method=method, allocation_strategy=fixed_strategy)
            for method in ("FMIC", "SMIC")
        ]
        for index, (a, b) in enumerate(((0, 0), (1.5, -0.75), (3, 0), (1, 1), (-1, -1))):
            results = [monitor.step({"A": a, "B": b}, str(index), index * 60) for monitor in monitors]
            self.assertEqual(results[0], results[1])
            self.assertEqual(monitors[0].messages, monitors[1].messages)
            self.assertEqual(monitors[0].partition, monitors[1].partition)
            self.assertEqual(monitors[0].references, monitors[1].references)

    def test_weight_method_is_validated(self):
        with self.assertRaisesRegex(ValueError, "weight_method"):
            FMICMonitor(("A", "B"), 1, weight_method="OTHER")


ROOT = Path(__file__).resolve().parents[1]


FMIC_MONITOR, _ = load_phase3_monitor()


def build_fixture(values, threshold, sensor_ids=None):
    if sensor_ids is None:
        sensor_ids = tuple(chr(ord("A") + index) for index in range(len(values[0])))
    columns = [f"{sensor}_temperature" for sensor in sensor_ids]
    frame = pd.DataFrame(values, columns=columns)
    frame.insert(0, "bucket_epoch", [index * 60 for index in range(len(frame))])
    frame.insert(1, "bucket_time_utc", [f"t{index}" for index in range(len(frame))])
    phase2 = build_phase2_trace(frame, columns, threshold, round_output=False)
    phase3 = run_phase3_control(frame, columns, threshold, FMIC_MONITOR)
    comparison = compare_decisions(phase2, phase3.decision_trace, columns, phase3.events)
    return frame, columns, phase2, phase3, comparison


class SyntheticProtocolTests(unittest.TestCase):
    def test_initialization_and_silent_safe_or_violated_operation(self):
        for values, threshold, expected_state in (
            ([[1, 1], [1, 1], [1, 1]], 10, "SAFE"),
            ([[2, 2], [2, 2], [2, 2]], 0, "VIOLATED"),
        ):
            with self.subTest(expected_state=expected_state):
                _, _, phase2, phase3, comparison = build_fixture(values, threshold)
                self.assertTrue(comparison["passed"])
                self.assertEqual(phase2.event_resync_performed.tolist(), [1, 0, 0])
                self.assertEqual(
                    [row["synchronized"] for row in phase3.decision_trace],
                    [True, False, False],
                )
                self.assertEqual(
                    set(phase2["root_known_state"]), {expected_state}
                )
                self.assertEqual(phase3.summary()["root_synchronization_count"], 1)

    def test_warming_and_cooling_crossings_are_detected_on_crossing_bucket(self):
        for values, expected_initial, expected_crossing in (
            ([[9, 9], [10, 10]], "SAFE", "VIOLATED"),
            ([[11, 11], [9, 9]], "VIOLATED", "SAFE"),
        ):
            with self.subTest(values=values):
                _, _, phase2, phase3, comparison = build_fixture(values, 10)
                self.assertTrue(comparison["passed"])
                self.assertEqual(phase2.loc[0, "root_known_state"], expected_initial)
                self.assertEqual(phase2.loc[1, "root_known_state"], expected_crossing)
                self.assertEqual(phase2.loc[1, "event_triggering_sensor_names"], "A|B")
                self.assertEqual(
                    phase3.decision_trace[1]["triggering_sensor_ids"], ("A", "B")
                )
                self.assertTrue(phase3.decision_trace[1]["synchronized"])

    def test_exact_global_local_and_zero_allowance_boundaries(self):
        for value, expected_state in (
            (float.fromhex("0x1.3ffffffffffffp+4"), "SAFE"),
            (20.0, "VIOLATED"),
            (float.fromhex("0x1.4000000000001p+4"), "VIOLATED"),
        ):
            with self.subTest(global_mean=value):
                _, _, boundary_trace, _, boundary_result = build_fixture(
                    [[value, value], [value, value]], 20
                )
                self.assertTrue(boundary_result["passed"])
                self.assertEqual(boundary_trace.loc[0, "root_known_state"], expected_state)

        _, _, exact_phase2, exact_phase3, exact_comparison = build_fixture(
            [[20, 20], [20, 20], [21, 19]], 20
        )
        self.assertTrue(exact_comparison["passed"])
        self.assertEqual(exact_phase2.loc[0, "root_known_state"], "VIOLATED")
        self.assertTrue(pd.isna(exact_phase2.loc[0, "entry_root_allowance"]))
        self.assertEqual(exact_phase2.event_resync_performed.tolist(), [1, 1, 1])
        self.assertEqual(
            [row["triggering_sensor_ids"] for row in exact_phase3.decision_trace],
            [(), ("A", "B"), ("A", "B")],
        )

        _, _, local_phase2, local_phase3, local_comparison = build_fixture(
            [[10, 10], [20, 10]], 20
        )
        self.assertTrue(local_comparison["passed"])
        self.assertEqual(local_phase2.loc[1, "event_triggering_sensor_names"], "A")
        self.assertEqual(local_phase3.decision_trace[1]["triggering_sensor_ids"], ("A",))
        self.assertEqual(local_phase2.loc[1, "event_resync_performed"], 1)

        _, _, below_phase2, below_phase3, below_result = build_fixture(
            [[10, 10], [float.fromhex("0x1.3ffffffffffffp+4"), 10]], 20
        )
        self.assertTrue(below_result["passed"])
        self.assertEqual(below_phase2.loc[1, "event_triggering_sensor_names"], "")
        self.assertEqual(below_phase3.decision_trace[1]["triggering_sensor_ids"], ())

    def test_simultaneous_singleton_triggers_create_one_root_collection(self):
        _, _, phase2, phase3, comparison = build_fixture(
            [[0, 0, 0], [2, 2, 2]], 2, ("A", "B", "C")
        )
        self.assertTrue(comparison["passed"])
        row = phase3.decision_trace[1]
        self.assertEqual(row["triggering_sensor_ids"], ("A", "B", "C"))
        self.assertTrue(row["synchronized"])
        self.assertEqual(row["messages"]["coordinator_root_escalations"], 3)
        self.assertEqual(row["messages"]["root_sync_requests"], 3)
        self.assertEqual(row["messages"]["root_sync_responses"], 3)
        self.assertEqual(row["messages"]["root_state_updates"], 3)
        self.assertTrue(all(row["messages"][category] == 0 for category in PHASE3_PEER_CATEGORIES))
        self.assertEqual(row["total_messages"], 12)
        self.assertEqual(phase2.loc[1, "total_message_count"], 12)
        self.assertEqual(phase3.summary()["root_synchronization_count"], 2)

    def test_consecutive_syncs_and_long_silent_gaps(self):
        _, _, consecutive_phase2, consecutive_phase3, consecutive = build_fixture(
            [[0, 0], [1, 1], [1, 1], [1, 1]], 1
        )
        self.assertTrue(consecutive["passed"])
        self.assertEqual(consecutive_phase2.event_resync_performed.tolist(), [1, 1, 1, 1])
        self.assertEqual(
            [row["synchronized"] for row in consecutive_phase3.decision_trace],
            [True, True, True, True],
        )

        _, _, silent_phase2, silent_phase3, silent = build_fixture(
            [[0, 0], [0, 0], [0, 0], [10, 0]], 10
        )
        self.assertTrue(silent["passed"])
        self.assertEqual(silent_phase2.event_resync_performed.tolist(), [1, 0, 0, 1])
        self.assertEqual(
            [row["synchronized"] for row in silent_phase3.decision_trace],
            [True, False, False, True],
        )

    def test_hand_counted_two_sensor_transmission_ledger(self):
        _, _, phase2, phase3, comparison = build_fixture(
            [[0, 0], [1, 1]], 1, ("A", "B")
        )
        self.assertTrue(comparison["passed"])
        initial = phase3.decision_trace[0]
        second = phase3.decision_trace[1]
        self.assertEqual(initial["total_messages"], 6)
        self.assertEqual(second["messages"]["coordinator_root_escalations"], 2)
        self.assertEqual(second["total_messages"], 8)
        self.assertEqual(phase3.summary()["total_messages"], 14)
        synchronizations = int(phase2.event_resync_performed.sum())
        notifications = int(phase2.trigger_message_count.sum())
        self.assertEqual(phase3.summary()["total_messages"], 3 * 2 * synchronizations + notifications)
        self.assertEqual(
            phase3.summary()["total_messages"],
            int(phase2.total_message_count.sum()),
        )
        ledger = [
            ("root", "A", "initial root request", "root_sync_requests"),
            ("root", "B", "initial root request", "root_sync_requests"),
            ("A", "root", "initial sensor response", "root_sync_responses"),
            ("B", "root", "initial sensor response", "root_sync_responses"),
            ("root", "A", "initial state update", "root_state_updates"),
            ("root", "B", "initial state update", "root_state_updates"),
            ("A", "root", "A threshold alert", "coordinator_root_escalations"),
            ("B", "root", "B threshold alert", "coordinator_root_escalations"),
            ("root", "A", "root sync request", "root_sync_requests"),
            ("root", "B", "root sync request", "root_sync_requests"),
            ("A", "root", "root sync response", "root_sync_responses"),
            ("B", "root", "root sync response", "root_sync_responses"),
            ("root", "A", "root state update", "root_state_updates"),
            ("root", "B", "root state update", "root_state_updates"),
        ]
        self.assertTrue(all(sender != recipient for sender, recipient, _, _ in ledger))
        ledger_categories = Counter(item[3] for item in ledger)
        expected_categories = {
            "coordinator_root_escalations": 2,
            "root_sync_requests": 4,
            "root_sync_responses": 4,
            "root_state_updates": 4,
        }
        self.assertEqual(dict(ledger_categories), expected_categories)
        self.assertEqual(len(ledger), phase3.summary()["total_messages"])

    def test_checker_detects_stale_reference_dropped_alert_and_status_defects(self):
        frame, columns, phase2, phase3, passing = build_fixture(
            [[0, 0], [1, 1], [2, 0]], 1, ("A", "B")
        )
        self.assertTrue(passing["passed"])
        mutations = (
            ("entry_references", lambda trace: trace[1]["entry_references"].update({"A": 9.0})),
            ("trigger_sensor_sets", lambda trace: trace[1].update({"triggering_sensor_ids": ("A",)})),
            ("post_root_known_state", lambda trace: trace[1].update({"root_known_state": "SAFE"})),
        )
        for expected_field, mutate in mutations:
            with self.subTest(expected_field=expected_field):
                altered = copy.deepcopy(phase3.decision_trace)
                mutate(altered)
                result = compare_decisions(phase2, altered, columns, phase3.events)
                self.assertFalse(result["passed"])
                self.assertEqual(result["first_mismatch"]["field"], expected_field)

        false_safe_rows = phase2.copy()
        false_safe_rows.loc[1, "root_known_state"] = "SAFE"
        false_safe = evaluate_root_states(false_safe_rows, frame, columns, 1)
        false_safe_rows[false_safe.columns] = false_safe
        self.assertEqual(root_correctness_summary(false_safe_rows)["false_safe_count"], 1)

        false_violated_rows = phase2.copy()
        false_violated_rows.loc[0, "root_known_state"] = "VIOLATED"
        false_violated = evaluate_root_states(false_violated_rows, frame, columns, 1)
        false_violated_rows[false_violated.columns] = false_violated
        self.assertEqual(root_correctness_summary(false_violated_rows)["false_violated_count"], 1)

    def test_trace_length_mismatch_returns_failed_comparison_schema(self):
        _, columns, phase2, phase3, passing = build_fixture(
            [[0, 0], [1, 1], [2, 0]], 1, ("A", "B")
        )
        self.assertTrue(passing["passed"])

        result = compare_decisions(
            phase2, phase3.decision_trace[:-1], columns, phase3.events
        )

        self.assertFalse(result["passed"])
        self.assertTrue(result["trace_length_mismatch"])
        self.assertEqual(result["expected_trace_length"], 3)
        self.assertEqual(result["actual_trace_length"], 2)
        self.assertEqual(result["mismatch_type"], "trace_length")
        self.assertIn("phase3_peer_traffic_zero", result)
        self.assertIn("fixed_singleton_partition_and_allowances_at_every_sync", result)
        self.assertEqual(result["first_mismatch"]["field"], "decision_trace_length")
        self.assertEqual(result["first_mismatch"]["expected"], 3)
        self.assertEqual(result["first_mismatch"]["observed"], 2)

    def test_empty_sync_timeline_fails_with_diagnostic_and_numeric_tolerance_is_continuous_only(self):
        empty_phase2 = pd.DataFrame(
            columns=[
                "bucket_epoch",
                "bucket_time_utc",
                "event_resync_performed",
                "event_triggering_sensor_names",
                "root_known_state",
                "observed_global_average",
                *(
                    "trigger_message_count",
                    "request_message_count",
                    "response_message_count",
                    "broadcast_message_count",
                    "total_message_count",
                ),
            ]
        )
        empty = compare_decisions(empty_phase2, [], ["A_temperature"], [])
        self.assertFalse(empty["passed"])
        self.assertEqual(empty["first_mismatch"]["field"], "phase3_sync_event_timeline")

        _, columns, phase2, phase3, _ = build_fixture(
            [[0, 0], [1, 1]], 1, ("A", "B")
        )
        within_tolerance = copy.deepcopy(phase3.decision_trace)
        within_tolerance[1]["observed_global_average"] += 5e-13
        self.assertTrue(
            compare_decisions(phase2, within_tolerance, columns, phase3.events)["passed"]
        )

        changed_state = copy.deepcopy(within_tolerance)
        changed_state[1]["root_known_state"] = "SAFE"
        result = compare_decisions(phase2, changed_state, columns, phase3.events)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any(item["field"] == "post_root_known_state" for item in result["diagnostics"])
        )

    def test_singleton_event_and_peer_failures_have_actionable_diagnostics(self):
        _, columns, phase2, phase3, passing = build_fixture(
            [[0, 0], [1, 1], [2, 0]], 1, ("A", "B")
        )
        self.assertTrue(passing["passed"])

        mutations = (
            (
                "selected_partition",
                lambda events: events[0].update(
                    {"selected_partition": json.dumps([["A", "B"]])}
                ),
                lambda trace: trace,
            ),
            (
                "node_allowances",
                lambda events: events[0].update(
                    {"node_allowances": json.dumps({"A": 0.0, "B": 1.0})}
                ),
                lambda trace: trace,
            ),
            (
                "coordinator_allowances",
                lambda events: events[0].update(
                    {"coordinator_allowances": json.dumps({"A": 0.0, "B": 1.0})}
                ),
                lambda trace: trace,
            ),
            (
                "phase3_sync_event_timeline",
                lambda events: events[0].update({"bucket_epoch": "123"}),
                lambda trace: trace,
            ),
            (
                f"messages.{PHASE3_PEER_CATEGORIES[0]}",
                lambda events: events,
                lambda trace: trace[1]["messages"].update(
                    {PHASE3_PEER_CATEGORIES[0]: 1}
                ),
            ),
        )
        for expected_field, mutate_events, mutate_trace in mutations:
            with self.subTest(field=expected_field):
                altered_events = copy.deepcopy(phase3.events)
                altered_trace = copy.deepcopy(phase3.decision_trace)
                mutate_events(altered_events)
                mutate_trace(altered_trace)

                result = compare_decisions(
                    phase2, altered_trace, columns, altered_events
                )

                self.assertFalse(result["passed"])
                diagnostic = next(
                    item
                    for item in result["diagnostics"]
                    if item["field"] == expected_field
                )
                self.assertIsNotNone(diagnostic["bucket_index"])
                self.assertIsNotNone(diagnostic["bucket_time_utc"])
                self.assertIn("expected", diagnostic)
                self.assertIn("observed", diagnostic)
                if expected_field.startswith("messages."):
                    self.assertFalse(result["phase3_peer_traffic_zero"])
                else:
                    self.assertFalse(
                        result[
                            "fixed_singleton_partition_and_allowances_at_every_sync"
                        ]
                    )

    def test_production_runner_writes_failed_summary_and_returns_nonzero(self):
        _, phase3_categories = load_phase3_monitor()
        monitor_class, _ = load_phase3_monitor()
        final_epoch = int(pd.Timestamp("2022-03-10T15:53:00+00:00").timestamp())

        class MissingFinalDecisionMonitor(monitor_class):
            def step(self, *args, **kwargs):
                result = super().step(*args, **kwargs)
                epoch = args[2] if len(args) > 2 else kwargs["epoch"]
                if int(epoch) == final_epoch:
                    self.decision_trace.pop()
                return result

        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            with patch.object(
                equivalence_runner,
                "load_phase3_monitor",
                return_value=(MissingFinalDecisionMonitor, phase3_categories),
            ), contextlib.redirect_stdout(io.StringIO()):
                exit_code = equivalence_runner.main(
                    [
                        "--equivalence",
                        "--root",
                        str(ROOT),
                        "--output-dir",
                        str(output_dir),
                    ]
                )

            summary_path = implementation._resolve_operational_dir(output_dir) / RUN_PATH
            summary = json.loads(summary_path.read_text(encoding="utf-8"))["equivalence"]
            self.assertEqual(exit_code, 1)
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["comparison"]["expected_trace_length"], 19984)
            self.assertEqual(summary["comparison"]["actual_trace_length"], 19983)

    def test_fresh_monitors_have_independent_deterministic_state(self):
        observations = [[0, 0], [1, 1], [1.5, 0.5], [2, 0]]
        first = build_fixture(observations, 1)[3]
        second = build_fixture(observations, 1)[3]
        self.assertEqual(first.messages, second.messages)
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.decision_trace, second.decision_trace)
        self.assertIsNot(first.references, second.references)


class ProductionReproducibilityTests(unittest.TestCase):
    def test_fresh_process_reproduction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dirs = [root / "first", root / "second"]
            command = [
                sys.executable,
                "-B",
                "-m",
                "scripts.phase3_implement",
                "--equivalence",
                "--root",
                str(ROOT),
                "--output-dir",
            ]
            for output_dir in output_dirs:
                completed = subprocess.run(
                    [*command, str(output_dir)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode, 0,
                    msg=completed.stdout + completed.stderr,
                )
                summary = json.loads(
                    (implementation._resolve_operational_dir(output_dir) / RUN_PATH).read_text(
                        encoding="utf-8"
                    )
                )["equivalence"]
                self.assertEqual(summary["status"], "passed")
                self.assertEqual(summary["contract"]["bucket_count"], 19984)
                self.assertEqual(summary["validation"]["test_suite_status"], "not_run")
                self.assertIsNone(summary["validation"]["test_count"])
                self.assertEqual(
                    set(summary["provenance"]["test_sha256"]),
                    {
                        "test_shared_monitoring.py",
                        "phase3_test.py",
                    },
                )
            for name in (
                RUN_PATH,
                implementation.EQUIVALENCE_EVENTS_PATH,
            ):
                self.assertEqual(
                    (implementation._resolve_operational_dir(output_dirs[0]) / name).read_bytes(),
                    (implementation._resolve_operational_dir(output_dirs[1]) / name).read_bytes(),
                )


ENGINE = _load_engine()


def frame(rows, sensors=("A", "B")):
    columns = [f"{sensor}_temperature" for sensor in sensors]
    data = pd.DataFrame(rows, columns=columns)
    data.insert(0, "bucket_epoch", [index * 60 for index in range(len(rows))])
    data.insert(1, "bucket_time_utc", [f"t{index}" for index in range(len(rows))])
    return data, columns


def weighted_allocation(engine, weights):
    def allocate(moment, partition, root_allowance):
        result = engine.allocate_moment_weights(
            weights, partition, root_allowance, "test_fixed_moment_weights"
        )
        result["first_moments"] = moment.means()
        return result

    return allocate


class CompositionTests(unittest.TestCase):
    def test_pathway_counts_and_shares_reconcile_by_independent_arithmetic(self):
        result = _composition({
            "node_trigger_messages": 2,
            "cluster_check_requests": 3,
            "cluster_check_responses": 3,
            "coordinator_root_escalations": 4,
            "root_sync_requests": 6,
            "root_sync_responses": 6,
            "root_state_updates": 6,
        })
        self.assertEqual(result["total_messages"], 30)
        self.assertEqual(result["within_cluster_messages"], 8)
        self.assertEqual(result["coordinator_to_root_messages"], 4)
        self.assertEqual(result["root_wide_messages"], 18)
        self.assertAlmostEqual(result["within_cluster_messages_share_percent"], 8 / 30 * 100)
        self.assertAlmostEqual(result["coordinator_to_root_messages_share_percent"], 4 / 30 * 100)
        self.assertAlmostEqual(result["root_wide_messages_share_percent"], 18 / 30 * 100)
        self.assertAlmostEqual(
            result["within_cluster_messages_share_percent"]
            + result["coordinator_to_root_messages_share_percent"]
            + result["root_wide_messages_share_percent"],
            100.0,
        )

    def test_negative_or_mismatched_message_categories_fail(self):
        categories = {
            "node_trigger_messages": 0,
            "cluster_check_requests": 0,
            "cluster_check_responses": 0,
            "coordinator_root_escalations": 0,
            "root_sync_requests": 0,
            "root_sync_responses": 0,
            "root_state_updates": 0,
        }
        with self.assertRaises(ValueError):
            _composition({**categories, "unclassified": 1})
        with self.assertRaises(ValueError):
            _composition({**categories, "root_sync_requests": -1})
        zero = _composition(categories)
        self.assertEqual(zero["zero_message_share_convention"], "not_applicable")
        self.assertIsNone(zero["within_cluster_messages_share_percent"])

    def test_comparison_outputs_include_pathways_and_matched_baseline(self):
        def row(config_id, algorithm, messages):
            categories = {
                "node_trigger_messages": 1 if config_id != "C0" else 0,
                "cluster_check_requests": 1 if algorithm == "FMIC" else 0,
                "cluster_check_responses": 1 if algorithm == "FMIC" else 0,
                "coordinator_root_escalations": 2,
                "root_sync_requests": 3,
                "root_sync_responses": 3,
                "root_state_updates": 3,
            }
            composition = _composition(categories)
            return {
                "config_id": config_id,
                "algorithm": algorithm,
                "alpha_label": "0.10" if algorithm in ("FMIC", "SMIC") else "not_applicable",
                "correctness_status": "passed",
                "total_messages": messages,
                "root_synchronization_count": 1,
                "coordinator_check_count": 2,
                "checks_resolved_without_escalation": 1,
                "checks_escalated": 1,
                "repeated_coordinator_check_count": 1,
                "repeated_checks_resolved_without_escalation": 1,
                "cluster_count_mean_per_sync_event": 2.0,
                "singleton_partition_event_share_percent": 50.0,
                "centralized_reduction_percent": 90.0,
                "message_category_totals": categories,
                **categories,
                **composition,
            }

        controls = [
            row("C0", "equal_allowance", 18),
            row("C1", "FMIC", 18),
            row("C2", "SMIC", 18),
        ]
        alphas = [row("FMIC", "FMIC", 16), row("SMIC", "SMIC", 17)]
        comparisons = _build_comparisons(controls, alphas, 18, 100)
        revised = {
            "correctness_status": "passed",
            "total_messages": 18,
            "resynchronization_count": 1,
            "message_category_totals": {
                "trigger_message_count": 2,
                "request_message_count": 3,
                "response_message_count": 3,
                "broadcast_message_count": 3,
            },
        }
        table = _configuration_table(
            controls,
            alphas,
            revised,
            {
                "FMIC": {"alpha_labels": ["0.10"]},
                "SMIC": {"alpha_labels": ["0.10"]},
            },
            100,
        )
        self.assertIn("C0_minus_C1", comparisons["weighting_effects_without_clustering"][
            "matched_pathway_and_check_contrasts"
        ])
        self.assertIn("pathway_message_differences", comparisons[
            "clustering_effects_conditional_on_weighting"
        ]["FMIC"]["0.10"])
        self.assertEqual(len(table), 8)
        self.assertEqual(table[0]["config_id"], "revised_phase2")
        self.assertEqual(
            table[0]["centralized_reduction_percent"], 82.0
        )


class ControlAndDiagnosticTests(unittest.TestCase):
    def test_output_directory_is_isolated_and_cannot_target_sources_or_checkpoint(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(
            implementation._resolve_output_dir(root, None),
            root / "artifacts" / "phase3_outputs",
        )
        for path in (
            root, root.parent, root / "artifacts", root / "scripts" / "outputs",
            root / "config", root / "artifacts" / "phase3_baseline_us327" / "outputs",
            root / "artifacts" / "phase3_operational" / "outputs",
            *(root / "artifacts" / name / "outputs" for name in (
                "phase2_outputs", "phase2_operational", "phase2_archive",
            )),
        ):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "directory"):
                implementation._resolve_output_dir(root, path)

    def test_external_validation_record_rejects_missing_stale_failed_or_incomplete_evidence(self):
        root = Path(__file__).resolve().parents[1]
        modules = [
            f"scripts.{Path(name).stem}" for name in implementation.VALIDATION_TEST_MODULES
        ]
        record = {
            "schema_version": 2, "status": "passed", "returncode": 0,
            "protected_files_unchanged": True, "skipped": [], "failures": [], "errors": [],
            "test_ids": ["independently_executed_test"],
            "checks": ["behavior", "replay"],
            "cross_phase_modules": ["scripts.test_shared_monitoring"],
            "test_count": 1, "inputs_and_code_unchanged": True, "modules": modules,
            "command": ["independently_executed_tests"], "provenance": {"code": "current"},
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            implementation, "validation_provenance", return_value={"code": "current"}
        ):
            path = Path(temporary) / "validation.json"
            with self.assertRaisesRegex(ValueError, "required"):
                implementation._read_validation_record(root, None)
            path.write_text(json.dumps(record))
            self.assertEqual(
                implementation._read_validation_record(root, path)["record_sha256"],
                implementation._sha256(path),
            )
            for field, value in (
                ("status", "failed"), ("returncode", 1), ("test_count", 0),
                ("test_count", True), ("modules", []), ("command", []),
                ("inputs_and_code_unchanged", False),
                ("provenance", {"code": "stale"}),
                ("checks", ["behavior"]), ("cross_phase_modules", []),
                ("protected_files_unchanged", False), ("skipped", [["test", "reason"]]),
                ("test_ids", []), ("failures", [["test", "failed"]]),
            ):
                with self.subTest(field=field, value=value):
                    path.write_text(json.dumps({**record, field: value}))
                    with self.assertRaisesRegex(ValueError, "failed, incomplete, or stale"):
                        implementation._read_validation_record(root, path)

    def test_c0_is_regenerated_when_stale_then_reused_only_with_matching_events_and_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "artifacts").mkdir()
            output = root / "outputs"
            output.mkdir()
            expected = {"phase3_implementation_sha256": "current", "input_sha256": "input"}
            summary_path = output / RUN_PATH
            events_path = output / implementation.EQUIVALENCE_EVENTS_PATH
            summary_path.write_text(json.dumps({"status": "passed", "provenance": {"stale": True}}))

            def fresh(_root, directory):
                self.assertEqual(directory, output)
                events_path.write_text("fresh event")
                report = {
                    "status": "passed", "checks": {"equivalent": True},
                    "comparison": {"passed": True}, "provenance": dict(expected),
                    "outputs": {"events_sha256": implementation._sha256(events_path)},
                    "validation": {"test_suite_status": "not_run"},
                }
                summary_path.write_text(json.dumps({"equivalence": report}))
                return report

            with mock.patch.object(
                implementation, "_phase3a_validate_us321", return_value={"status": "historical"}
            ), mock.patch.object(
                implementation, "_equivalence_provenance", return_value=expected
            ), mock.patch.object(
                implementation, "run_phase3a_protocol_equivalence", side_effect=fresh
            ) as generate:
                args = (root, {"revised": {}}, output, {"record_sha256": "validated"})
                gates = implementation._validate_prerequisites(*args)
                self.assertFalse(gates["C0_reused"])
                self.assertEqual(generate.call_count, 1)
                self.assertTrue(implementation._validate_prerequisites(*args)["C0_reused"])
                self.assertEqual(generate.call_count, 1)
                events_path.write_text("tampered event")
                self.assertFalse(implementation._validate_prerequisites(*args)["C0_reused"])
                self.assertEqual(generate.call_count, 2)

    def test_failed_fresh_c0_blocks_controls_without_marking_tests_as_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "artifacts").mkdir()
            with mock.patch.object(
                implementation, "_phase3a_validate_us321", return_value={}
            ), mock.patch.object(
                implementation, "_equivalence_provenance", return_value={}
            ), mock.patch.object(
                implementation, "run_phase3a_protocol_equivalence",
                return_value={"status": "failed"},
            ), mock.patch.object(implementation, "_run_control") as controls:
                with self.assertRaisesRegex(ValueError, "remain blocked"):
                    implementation._validate_prerequisites(
                        root, {"revised": {}}, root / "outputs",
                        {"record_sha256": "validated"},
                    )
                controls.assert_not_called()

    def test_missing_validation_record_persists_failure_only_in_candidate_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "artifacts").mkdir()
            (root / "config").mkdir()
            (root / "config" / "phase3a_experiment_config.json").write_text("{}")
            output = root / "candidate"
            with mock.patch.object(
                implementation, "_validate_contract", return_value={}
            ), mock.patch.object(implementation, "_validate_prerequisites") as gates, mock.patch.object(
                implementation.subprocess, "run",
                side_effect=AssertionError("Production must not launch tests before validation"),
            ):
                with self.assertRaisesRegex(ValueError, "validation-record"):
                    run_us325(root, output)
                gates.assert_not_called()
            run = json.loads((implementation._resolve_operational_dir(output) / RUN_PATH).read_text())
            failure = run["failures"]
            self.assertEqual(failure["failures"][0]["stage"], "external_regression_validation")
            self.assertEqual(
                run["completion"]["status"],
                "failed",
            )
            self.assertEqual(list((root / "artifacts").iterdir()), [])
            self.assertNotIn("comparison", run)

    def test_production_has_no_test_import_or_test_suite_launcher(self):
        tree = ast.parse(Path(implementation.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn("test_", node.module or "")
            if isinstance(node, ast.Import):
                self.assertFalse(any("test_" in name.name or name.name == "unittest" for name in node.names))
        self.assertFalse(hasattr(implementation, "_run_validation_tests"))

    def test_validation_producer_records_real_test_outcome_and_input_stability(self):
        def fail():
            raise AssertionError("injected fixture failure")

        def skipped():
            raise unittest.SkipTest("injected missing prerequisite")

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "validation.json"
            for fixture, after, expected in (
                (lambda: None, {"code": "current"}, "passed"),
                (fail, {"code": "current"}, "failed"),
                (skipped, {"code": "current"}, "failed"),
                (lambda: None, {"code": "changed"}, "failed"),
            ):
                with self.subTest(expected=expected, fixture=fixture):
                    suite = unittest.TestSuite([unittest.FunctionTestCase(fixture)])
                    with mock.patch.object(
                        implementation, "validation_provenance",
                        side_effect=[{"code": "current"}, after],
                    ), mock.patch.object(
                        sys.modules[__name__], "_build_suite", return_value=suite,
                    ), mock.patch("sys.stdout", io.StringIO()):
                        returncode = record_validation(path)
                    record = json.loads(path.read_text())
                    self.assertEqual(record["status"], expected)
                    self.assertEqual(record["test_count"], 1)
                    self.assertEqual(returncode, 0 if expected == "passed" else 1)

    def test_prerequisite_gate_requires_current_implementation_hash(self):
        expected = {"phase3_implementation_sha256": "current", "input_sha256": "input"}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.csv"
            path.write_text("event")
            for value in (None, "stale", "current"):
                with self.subTest(implementation_hash=value):
                    report = {
                        "status": "passed", "checks": {"equivalent": True},
                        "comparison": {"passed": True},
                        "provenance": {**expected, "phase3_implementation_sha256": value},
                        "outputs": {"events_sha256": implementation._sha256(path)},
                    }
                    self.assertEqual(
                        implementation._equivalence_is_current(report, path, expected),
                        value == "current",
                    )
            path.write_text("altered")
            self.assertFalse(implementation._equivalence_is_current(report, path, expected))

    def test_singleton_weighting_controls_keep_alpha_out_of_decisions(self):
        data, columns = frame([[0, 0], [1.5, -0.75], [2, 0]])
        outputs = []
        for alpha in (0.05, 0.95):
            summary, _, events = _run_monitor(
                ENGINE.FMICMonitor,
                data,
                columns,
                1.0,
                "FMIC",
                alpha=alpha,
                fixed_singletons=True,
            )
            outputs.append((
                summary["message_category_totals"],
                summary["total_messages"],
                [event["selected_partition"] for event in events],
            ))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(len(ALPHA_LABELS), 19)
        self.assertEqual(
            outputs[0][2],
            ['[["A"], ["B"]]', '[["A"], ["B"]]', '[["A"], ["B"]]'],
        )

    def test_same_weights_distinct_partition_changes_only_check_protocol(self):
        columns = ["A_temperature", "B_temperature"]
        allocate = weighted_allocation(ENGINE, {"A": 1.0, "B": 1.0})
        scenarios = (
            (
                (1.5, -1.5),
                {
                    "node_trigger_messages": 0,
                    "cluster_check_requests": 0,
                    "cluster_check_responses": 0,
                    "coordinator_root_escalations": 2,
                    "root_sync_requests": 4,
                    "root_sync_responses": 4,
                    "root_state_updates": 4,
                },
                {
                    "node_trigger_messages": 1,
                    "cluster_check_requests": 0,
                    "cluster_check_responses": 0,
                    "coordinator_root_escalations": 0,
                    "root_sync_requests": 2,
                    "root_sync_responses": 2,
                    "root_state_updates": 2,
                },
                1,
            ),
            (
                (1.5, 0.75),
                {
                    "node_trigger_messages": 0,
                    "cluster_check_requests": 0,
                    "cluster_check_responses": 0,
                    "coordinator_root_escalations": 1,
                    "root_sync_requests": 4,
                    "root_sync_responses": 4,
                    "root_state_updates": 4,
                },
                {
                    "node_trigger_messages": 1,
                    "cluster_check_requests": 0,
                    "cluster_check_responses": 0,
                    "coordinator_root_escalations": 1,
                    "root_sync_requests": 4,
                    "root_sync_responses": 4,
                    "root_state_updates": 4,
                },
                2,
            ),
        )
        for (
            values,
            expected_singleton_categories,
            expected_cluster_categories,
            expected_cluster_syncs,
        ) in scenarios:
            data, _ = frame([[0, 0], list(values)])
            singleton_summary, _, _ = _run_monitor(
                ENGINE.FMICMonitor,
                data,
                columns,
                1.0,
                "FMIC",
                alpha=0.1,
                fixed_singletons=True,
                allocation_strategy=allocate,
            )
            clustered_summary, _, _ = _run_monitor(
                ENGINE.FMICMonitor,
                data,
                columns,
                1.0,
                "FMIC",
                alpha=0.1,
                fixed_singletons=False,
                clustering=lambda _: {
                    "selected_partition": (("A", "B"),),
                    "partition_quality": 0.0,
                },
                allocation_strategy=allocate,
            )
            self.assertEqual(
                singleton_summary["message_category_totals"],
                expected_singleton_categories,
            )
            self.assertEqual(
                clustered_summary["message_category_totals"],
                expected_cluster_categories,
            )
            self.assertEqual(
                clustered_summary["root_synchronization_count"],
                expected_cluster_syncs,
            )
            self.assertEqual(
                clustered_summary["total_messages"],
                sum(expected_cluster_categories.values()),
            )
            self.assertEqual(
                singleton_summary["total_messages"],
                sum(singleton_summary["message_category_totals"].values()),
            )
            self.assertNotEqual(
                singleton_summary["message_category_totals"],
                clustered_summary["message_category_totals"],
            )

    def test_alpha_sensitive_source_clustering_receives_alpha(self):
        sensor_ids = ("A", "B", "C", "D", "E", "F")
        histories = dict(zip(sensor_ids, (1.0, -0.5, 0.25, 0.5, -1.0, 0.75)))
        snapshot = ENGINE.normalize_sensor_histories(histories, sensor_ids)
        alpha_inputs = ENGINE.build_alpha_clustering_inputs(
            1, snapshot, (0.05, 0.95)
        )
        results = [
            ENGINE.evaluate_alpha_clustering(alpha_input)
            for alpha_input in alpha_inputs
        ]
        self.assertEqual([result["alpha"] for result in results], [0.05, 0.95])
        self.assertIs(alpha_inputs[0].normalization_snapshot, snapshot)
        self.assertNotEqual(
            results[0]["selected_partition"], results[1]["selected_partition"]
        )

    def test_alpha_runs_are_independent_of_execution_order(self):
        sensor_ids = ("A", "B", "C", "D", "E", "F")
        readings = [
            [0, 0, 0, 0, 0, 0],
            [1, -0.5, 0.25, 0.5, -1, 0.75],
            [0.8, -0.4, 0.2, 0.4, -0.8, 0.6],
            [-0.7, 0.35, -0.175, -0.35, 0.7, -0.525],
        ]
        data, columns = frame(readings, sensor_ids)

        def replay(order):
            output = {}
            for alpha in order:
                summary, _, events = _run_monitor(
                    ENGINE.FMICMonitor,
                    data,
                    columns,
                    1.0,
                    "FMIC",
                    alpha=alpha,
                    fixed_singletons=False,
                )
                output[alpha] = (
                    summary["message_category_totals"],
                    summary["events_fingerprint"],
                    [event["selected_partition"] for event in events],
                )
            return output

        forward = replay((0.05, 0.25, 0.95))
        reverse = replay((0.95, 0.25, 0.05))
        self.assertEqual(forward, reverse)
        self.assertTrue(all(result[1] for result in forward.values()))
        self.assertTrue(
            all(len(result[2]) > 1 for result in forward.values())
        )

    def test_alpha_grid_is_complete_and_excludes_invalid_runs(self):
        rows = []
        for method in ("FMIC", "SMIC"):
            for alpha in ALPHA_LABELS:
                row = {
                    "config_id": method,
                    "algorithm": method,
                    "alpha_label": alpha,
                    "correctness_status": "passed",
                    "message_counts_reconcile": True,
                    "false_safe_count": 0,
                    "false_violated_count": 0,
                    "total_messages": 0,
                }
                row.update(dict.fromkeys(MESSAGE_CATEGORIES, 0))
                rows.append(row)
        _validate_alpha_grid(rows)
        self.assertEqual(len(ALPHA_LABELS), 19)
        self.assertEqual(len({(row["algorithm"], row["alpha_label"]) for row in rows}), 38)
        self.assertFalse(any(row["config_id"] in {"C0", "C1", "C2"} for row in rows))
        invalid_rows = [dict(row) for row in rows]
        invalid_rows[0]["correctness_status"] = "failed"
        with self.assertRaisesRegex(ValueError, "cannot enter alpha ranking"):
            _validate_alpha_grid(invalid_rows)

    def test_failed_runner_persists_diagnostic_without_success_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "artifacts").mkdir()
            (root / "config").mkdir()
            (root / "config" / "phase3a_experiment_config.json").write_text(
                "{}", encoding="utf-8"
            )
            call_order = []
            original_hashes = _protected_hashes

            def record_hashes(path):
                call_order.append("protected_hashes")
                return original_hashes(path)

            def fail_contract(_path):
                call_order.append("contract_validation")
                raise ValueError("injected prerequisite failure")

            with mock.patch(
                "scripts.phase3_implement._protected_hashes", side_effect=record_hashes
            ), mock.patch(
                "scripts.phase3_implement._validate_contract", side_effect=fail_contract
            ):
                with self.assertRaisesRegex(
                    ValueError, "injected prerequisite failure"
                ):
                    run_us325(root, root / "candidate")
            self.assertEqual(
                call_order,
                ["protected_hashes", "contract_validation", "protected_hashes"],
            )
            diagnostic = json.loads(
                (implementation._resolve_operational_dir(root / "candidate") / RUN_PATH).read_text(
                    encoding="utf-8"
                )
            )["failures"]
            self.assertEqual(diagnostic["status"], "failed")
            self.assertEqual(diagnostic["failure_count"], 1)
            self.assertIn("injected prerequisite failure", diagnostic["failures"][0]["failure_reason"])
            self.assertEqual(
                diagnostic["protected_artifact_integrity"]["status"], "unchanged"
            )
            self.assertFalse(
                (root / "artifacts" / "phase3a_us325_comparison_summary.json").exists()
            )

    def test_repeated_local_checks_count_once_and_reset_after_sync(self):
        data, columns = frame([
            [8, 8, 8],
            [10, 6, 8],
            [10, 6, 8],
            [10, 6, 8],
            [16, 6, 8],
            [16, 6, 8],
        ], ("A", "B", "C"))
        summary, by_size, _ = _run_monitor(
            ENGINE.FMICMonitor,
            data,
            columns,
            10.0,
            "FMIC",
            alpha=0.1,
            fixed_singletons=False,
            clustering=lambda _: {
                "selected_partition": (("A", "B", "C"),),
                "partition_quality": 0.0,
            },
            allocation_strategy=weighted_allocation(
                ENGINE, {"A": 0.25, "B": 1.1, "C": 1.65}
            ),
        )
        size_three = next(item for item in by_size if item["cluster_size"] == 3)
        self.assertEqual(summary["coordinator_check_count"], 5)
        self.assertEqual(summary["checks_resolved_without_escalation"], 3)
        self.assertEqual(summary["checks_escalated"], 2)
        self.assertEqual(summary["repeated_coordinator_check_count"], 3)
        self.assertEqual(summary["repeated_checks_resolved_without_escalation"], 2)
        self.assertEqual(summary["repeated_check_share_percent"], 60.0)
        self.assertEqual(size_three["repeated_coordinator_check_count"], 3)
        self.assertEqual(size_three["repeated_checks_resolved_without_escalation"], 2)
        self.assertEqual(size_three["node_trigger_messages"], 6)
        self.assertEqual(size_three["cluster_check_requests"], 4)
        self.assertEqual(size_three["cluster_check_responses"], 4)
        self.assertEqual(summary["message_category_totals"], {
            "node_trigger_messages": 6,
            "cluster_check_requests": 4,
            "cluster_check_responses": 4,
            "coordinator_root_escalations": 2,
            "root_sync_requests": 9,
            "root_sync_responses": 9,
            "root_state_updates": 9,
        })
        self.assertEqual(summary["total_messages"], 43)

    def test_nonconsecutive_check_is_not_counted_as_repeated(self):
        data, columns = frame([[8, 8], [10, 6], [8, 8], [10, 6]])
        summary, _, _ = _run_monitor(
            ENGINE.FMICMonitor,
            data,
            columns,
            10.0,
            "FMIC",
            alpha=0.1,
            fixed_singletons=False,
            clustering=lambda _: {
                "selected_partition": (("A", "B"),),
                "partition_quality": 0.0,
            },
            allocation_strategy=weighted_allocation(ENGINE, {"A": 1.0, "B": 3.0}),
        )
        self.assertEqual(summary["coordinator_check_count"], 2)
        self.assertEqual(summary["repeated_coordinator_check_count"], 0)

    def test_zero_allowance_unchanged_and_both_crossing_directions(self):
        data, columns = frame([[10, 10], [10, 10], [11, 11], [9, 9]])
        summary, _, events = _run_monitor(
            ENGINE.FMICMonitor,
            data,
            columns,
            10.0,
            "FMIC",
            alpha=0.1,
            fixed_singletons=True,
        )
        self.assertEqual(summary["root_synchronization_count"], 4)
        self.assertEqual(summary["coordinator_check_count"], 6)
        self.assertEqual(summary["coordinator_to_root_escalation_count"], 6)
        self.assertEqual(summary["global_threshold_violation_count"], 3)
        self.assertEqual(summary["false_safe_count"], 0)
        self.assertEqual(summary["false_violated_count"], 0)
        self.assertEqual(summary["correctness_status"], "passed")
        self.assertEqual([event["root_allowance"] for event in events], [0, 0, 1, 1])
        self.assertEqual(summary["total_messages"], 30)

    def test_zero_weight_sensor_triggers_with_positive_root_allowance(self):
        data, columns = frame([[0, 0], [0, 0]])
        summary, by_size, _ = _run_monitor(
            ENGINE.FMICMonitor,
            data,
            columns,
            1.0,
            "FMIC",
            alpha=0.1,
            fixed_singletons=False,
            clustering=lambda _: {
                "selected_partition": (("A", "B"),),
                "partition_quality": 0.0,
            },
            allocation_strategy=weighted_allocation(ENGINE, {"A": 0.0, "B": 2.0}),
        )
        self.assertEqual(summary["coordinator_check_count"], 1)
        self.assertEqual(summary["checks_resolved_without_escalation"], 1)
        self.assertEqual(summary["coordinator_to_root_escalation_count"], 0)
        self.assertEqual(summary["message_category_totals"]["node_trigger_messages"], 1)
        self.assertEqual(summary["message_category_totals"]["cluster_check_requests"], 0)
        self.assertEqual(summary["message_category_totals"]["cluster_check_responses"], 0)
        self.assertEqual(next(row for row in by_size if row["cluster_size"] == 2)["coordinator_check_count"], 1)


LEGACY_COVERAGE = {'test_phase3_history.py': ['ClusteringTests', 'NormalizationTests', 'Phase3AExecutionTests'], 'test_phase3_monitoring.py': ['FirstMomentTests', 'SecondMomentTests', 'FMICProtocolTests', 'ProductionIntegrationTests', 'SMICProtocolTests'], 'test_phase3a_protocol_equivalence.py': ['SyntheticProtocolTests', 'ProductionReproducibilityTests'], 'test_phase3a_us325.py': ['CompositionTests', 'ControlAndDiagnosticTests']}


APPROVED_ALPHAS = tuple(f"{step / 20:.2f}" for step in range(1, 20))


TRANSMISSIONS = (
    "node_trigger_messages", "cluster_check_requests", "cluster_check_responses",
    "coordinator_root_escalations", "root_sync_requests", "root_sync_responses",
    "root_state_updates",
)


RESULT_COUNTS = (
    "false_safe_count", "false_violated_count", "global_threshold_violation_count",
    "bucket_count", "total_messages", "root_synchronization_count",
    "coordinator_check_count", "checks_resolved_without_escalation", "checks_escalated",
    "node_trigger_count", "coordinator_to_root_escalation_count",
    "repeated_coordinator_check_count", "repeated_checks_resolved_without_escalation",
    "cluster_count_min", "cluster_count_max", "singleton_partition_event_count",
    *TRANSMISSIONS, "within_cluster_messages", "coordinator_to_root_messages",
    "root_wide_messages",
)


RESULT_FLOATS = (
    "repeated_check_share_percent", "cluster_count_mean_per_sync_event",
    "singleton_partition_event_share_percent", "within_cluster_messages_share_percent",
    "coordinator_to_root_messages_share_percent", "root_wide_messages_share_percent",
)


RESULT_SCHEMA = {
    *RESULT_COUNTS, *RESULT_FLOATS, "config_id", "algorithm", "allowance_method",
    "alpha", "alpha_label", "alpha_status", "result_source", "correctness_status",
    "message_counts_reconcile", "events_fingerprint", "zero_message_share_convention",
}


CONTRAST_FIELDS = {
    "reduction_vs_revised_phase2_percent", "revised_phase2_message_difference",
    "matched_singleton_message_difference", "matched_singleton_reduction_percent",
    "matched_singleton_root_synchronization_difference",
}


SIZE_COUNTS = (
    "coordinator_check_count", "checks_resolved_without_escalation", "checks_escalated",
    "repeated_coordinator_check_count", "repeated_checks_resolved_without_escalation",
    "node_trigger_messages", "cluster_check_requests", "cluster_check_responses",
    "triggered_sensor_count",
)


REPLAY_SPECS = (
    ("C1", "not_applicable", 8964, 457), ("C2", "not_applicable", 8962, 457),
    ("FMIC", "0.10", 11922, 293), ("SMIC", "0.10", 11902, 293),
    ("FMIC", "0.65", 8722, 436), ("SMIC", "0.65", 8720, 436),
)


CROSS_PHASE_MODULES = [
    "scripts.test_shared_monitoring",
]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value, label, *, integer=False, nonnegative=False):
    _require(not isinstance(value, bool), f"{label}: boolean is not a number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: required numeric value is invalid: {value!r}") from error
    _require(math.isfinite(result), f"{label}: required value is nonfinite")
    if integer:
        _require(result.is_integer(), f"{label}: expected an integer")
    if nonnegative:
        _require(result >= 0, f"{label}: expected a nonnegative value")
    return int(result) if integer else result


def _same_number(actual, expected, label):
    _require(
        math.isclose(_number(actual, label), expected, rel_tol=1e-12, abs_tol=1e-10),
        f"{label}: {actual!r} does not reconcile with {expected!r}",
    )


def _csv_rows(path, schema):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        _require(
            reader.fieldnames is not None
            and len(reader.fieldnames) == len(set(reader.fieldnames))
            and set(reader.fieldnames) == set(schema),
            f"{path.name}: schema mismatch",
        )
        rows = list(reader)
    _require(bool(rows), f"{path.name}: no saved rows")
    _require(
        all(None not in row and None not in row.values() for row in rows),
        f"{path.name}: malformed CSV row",
    )
    return rows


def _result_key(row):
    return row["config_id"], row["alpha_label"]


def _write_reference_tables(directory):
    """Build test fixtures from preserved scientific references, not candidate output."""
    root = implementation._phase3_reference_directory(ROOT)
    result_rows = []
    for kind, name in (
        ("control", "phase3a_us325_control_results.csv"),
        ("clustered", "phase3a_us325_alpha_results.csv"),
    ):
        with (root / name).open(newline="") as stream:
            result_rows.extend({**row, "configuration_kind": kind} for row in csv.DictReader(stream))
    implementation._write_csv_records(directory / implementation.RESULTS_PATH, result_rows)
    sizes = []
    for control, name in (
        (True, "phase3a_us325_control_cluster_size_summary.csv"),
        (False, "phase3a_us325_cluster_size_summary.csv"),
    ):
        with (root / name).open(newline="") as stream:
            for row in csv.DictReader(stream):
                sizes.append({**row, "alpha_label": "not_applicable"} if control else row)
    implementation._write_csv_records(directory / implementation.CLUSTER_SIZES_PATH, sizes)
    shutil.copy2(root / "phase3a_us325_event_snapshots.csv", directory / implementation.SNAPSHOTS_PATH)
    operational = implementation._resolve_operational_dir(directory)
    operational.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        root / "phase3a_protocol_equivalence_events.csv",
        operational / implementation.EQUIVALENCE_EVENTS_PATH,
    )
    (directory / implementation.SUMMARY_PATH).write_text(
        json.dumps({
            "schema_version": 1, "kind": "summary", "run_id": "run",
            "status": "passed", "comparison": {"status": "passed", "run_id": "run"},
        }),
        encoding="utf-8",
    )


def _verify_result_tables(directory, bucket_count, violation_count):
    rows = _csv_rows(
        directory / implementation.RESULTS_PATH,
        RESULT_SCHEMA | CONTRAST_FIELDS | {"configuration_kind"},
    )
    _require(
        all(row["configuration_kind"] in ("control", "clustered") for row in rows),
        "Missing or invalid configuration_kind",
    )
    controls = [row for row in rows if row["configuration_kind"] == "control"]
    alphas = [row for row in rows if row["configuration_kind"] == "clustered"]
    expected_keys = {(name, "not_applicable") for name in ("C0", "C1", "C2")} | {
        (method, alpha) for method in ("FMIC", "SMIC") for alpha in APPROVED_ALPHAS
    }
    indexed = {_result_key(row): row for row in rows}
    _require(
        len(controls) == 3 and len(alphas) == 38 and len(indexed) == 41
        and set(indexed) == expected_keys,
        "Expected exactly three unique controls and the complete 38-configuration alpha grid",
    )
    for row in rows:
        key = _result_key(row)
        for field in RESULT_COUNTS:
            row[field] = _number(row[field], f"{key}/{field}", integer=True, nonnegative=True)
        for field in RESULT_FLOATS:
            row[field] = _number(row[field], f"{key}/{field}", nonnegative=True)
        control = key[0] in ("C0", "C1", "C2")
        _require(
            row["configuration_kind"] == ("control" if control else "clustered")
            and (not control or all(row[field] == "" for field in CONTRAST_FIELDS)),
            f"{key}: configuration_kind or null contrast semantics changed",
        )
        method = {"C0": "equal_allowance", "C1": "FMIC", "C2": "SMIC"}.get(key[0], key[0])
        _require(row["algorithm"] == row["allowance_method"] == method, f"{key}: wrong method")
        _require(
            row["alpha_status"] == ("not_applicable" if control else "tested")
            and (row["alpha"] == "" if control else float(row["alpha"]) == float(key[1])),
            f"{key}: invalid alpha semantics",
        )
        _require(
            row["bucket_count"] == bucket_count
            and row["global_threshold_violation_count"] == violation_count
            and row["false_safe_count"] == row["false_violated_count"] == 0
            and row["correctness_status"] == "passed"
            and row["message_counts_reconcile"] == "True",
            f"{key}: correctness disagrees with source observations",
        )
        _require(
            row["total_messages"] > 0 and row["root_synchronization_count"] > 0
            and row["coordinator_check_count"] > 0,
            f"{key}: required production activity is missing",
        )
        _require(
            sum(row[name] for name in TRANSMISSIONS) == row["total_messages"],
            f"{key}: transmission categories do not reconcile",
        )
        groups = {
            "within_cluster_messages": sum(row[name] for name in TRANSMISSIONS[:3]),
            "coordinator_to_root_messages": row["coordinator_root_escalations"],
            "root_wide_messages": sum(row[name] for name in TRANSMISSIONS[4:]),
        }
        for field, expected in groups.items():
            _require(row[field] == expected, f"{key}/{field}: pathway mismatch")
            _same_number(
                row[field + "_share_percent"], 100 * expected / row["total_messages"],
                f"{key}/{field}_share_percent",
            )
        _require(
            row["cluster_check_requests"] == row["cluster_check_responses"]
            and all(row[name] == 6 * row["root_synchronization_count"] for name in TRANSMISSIONS[4:])
            and row["coordinator_check_count"] == row["checks_escalated"] + row["checks_resolved_without_escalation"]
            and row["checks_escalated"] == row["coordinator_to_root_escalation_count"] == row["coordinator_root_escalations"]
            and row["repeated_checks_resolved_without_escalation"] <= min(
                row["repeated_coordinator_check_count"], row["checks_resolved_without_escalation"])
            and row["repeated_coordinator_check_count"] <= row["coordinator_check_count"]
            and 1 <= row["cluster_count_min"] <= row["cluster_count_mean_per_sync_event"] <= row["cluster_count_max"] <= 6
            and row["singleton_partition_event_count"] <= row["root_synchronization_count"],
            f"{key}: check, cluster, or root-message counts do not reconcile",
        )
        _same_number(
            row["repeated_check_share_percent"],
            100 * row["repeated_coordinator_check_count"] / row["coordinator_check_count"],
            f"{key}/repeated share",
        )
        _same_number(
            row["singleton_partition_event_share_percent"],
            100 * row["singleton_partition_event_count"] / row["root_synchronization_count"],
            f"{key}/singleton share",
        )
        if control:
            _require(
                row["within_cluster_messages"] == row["checks_resolved_without_escalation"] == 0
                and row["cluster_count_min"] == row["cluster_count_max"] == 6,
                f"{key}: singleton-control contract changed",
            )
        if key[0] != "C0":
            _require(
                re.fullmatch(r"[0-9a-f]{64}", row["events_fingerprint"]) is not None,
                f"{key}: missing event fingerprint",
            )
    c0 = indexed["C0", "not_applicable"]
    _require((c0["total_messages"], c0["root_synchronization_count"]) == (9159, 467), "C0 reference mismatch")
    for method, alpha, messages, synchronizations in REPLAY_SPECS:
        row = indexed[method, alpha]
        _require(
            (row["total_messages"], row["root_synchronization_count"]) == (messages, synchronizations),
            f"{method}/{alpha}: independently preserved reference mismatch",
        )
    for row in alphas:
        control = indexed["C1" if row["algorithm"] == "FMIC" else "C2", "not_applicable"]
        differences = {
            "reduction_vs_revised_phase2_percent": 100 * (1 - row["total_messages"] / c0["total_messages"]),
            "revised_phase2_message_difference": c0["total_messages"] - row["total_messages"],
            "matched_singleton_message_difference": control["total_messages"] - row["total_messages"],
            "matched_singleton_reduction_percent": 100 * (control["total_messages"] - row["total_messages"]) / control["total_messages"],
            "matched_singleton_root_synchronization_difference": control["root_synchronization_count"] - row["root_synchronization_count"],
        }
        for field, expected in differences.items():
            _same_number(row[field], expected, f"{_result_key(row)}/{field}")
    name = implementation.CLUSTER_SIZES_PATH
    all_sizes = _csv_rows(directory / name, {"config_id", "alpha_label", "cluster_size", *SIZE_COUNTS})
    for control_table in (True, False):
        sizes = [
            row for row in all_sizes
            if (row["config_id"] in ("C0", "C1", "C2")) == control_table
        ]
        size_index = {}
        for item in sizes:
            key = item["config_id"], "not_applicable" if control_table else item["alpha_label"]
            _require(not control_table or item["alpha_label"] == "not_applicable", "Control size alpha must be not_applicable")
            size = _number(item["cluster_size"], f"{name}/cluster_size", integer=True)
            _require(key in indexed and 1 <= size <= 6 and (key, size) not in size_index, f"{name}: invalid/duplicate key")
            for field in SIZE_COUNTS:
                item[field] = _number(item[field], f"{name}/{field}", integer=True, nonnegative=True)
            _require(
                item["coordinator_check_count"] == item["checks_escalated"] + item["checks_resolved_without_escalation"]
                and item["repeated_checks_resolved_without_escalation"] <= min(
                    item["repeated_coordinator_check_count"], item["checks_resolved_without_escalation"])
                and item["repeated_coordinator_check_count"] <= item["coordinator_check_count"]
                and item["cluster_check_requests"] == item["cluster_check_responses"],
                f"{name}: invalid check outcomes",
            )
            size_index[key, size] = item
        expected = {_result_key(row) for row in (controls if control_table else alphas)}
        _require(set(size_index) == {(key, size) for key in expected for size in range(1, 7)}, f"{name}: incomplete cluster-size grid")
        for key in expected:
            for field in SIZE_COUNTS:
                target = "node_trigger_count" if field == "triggered_sensor_count" else field
                _require(
                    sum(size_index[key, size][field] for size in range(1, 7)) == indexed[key][target],
                    f"{name}/{key}/{field}: cluster-size totals do not reconcile",
                )
    return indexed


def _source_observations():
    contract = implementation._validate_contract(ROOT)
    config = contract["config"]
    data = pd.read_csv(contract["input_path"], float_precision="round_trip")
    selected = implementation.prepare_phase3a_input(data, config)
    columns = config["selected_sensor_temperature_columns"]
    averages = {
        int(row[0]): math.fsum(map(float, row[1:])) / len(columns)
        for row in selected[["bucket_epoch", *columns]].itertuples(index=False, name=None)
    }
    violations = sum(value >= contract["threshold"] for value in averages.values())
    _require(len(selected) == 19984 and violations == 1999, "Locked source cohort changed")
    return contract, selected, columns, averages, violations


def _verify_saved_provenance(directory, report):
    operational = implementation._resolve_operational_dir(directory)
    validation = report["validation"]
    _require(
        validation["provenance"] == implementation.validation_provenance(ROOT),
        "Saved production validation provenance is stale",
    )
    implementation._read_validation_record(ROOT, operational / implementation.VALIDATION_PATH)
    contract = implementation._validate_contract(ROOT)
    expected = implementation._equivalence_provenance(ROOT, contract)
    provenance = report["provenance"]
    for field in (
        "input_sha256", "preparation_sha256", "config_sha256", "phase2_monitoring_sha256",
        "phase3_implementation_sha256", "runner_sha256",
        "revised_phase2_baseline_sha256", "test_sha256",
    ):
        _require(provenance[field] == expected[field], f"Saved provenance mismatch: {field}")
    equivalence = implementation.load_phase3_run(ROOT, directory)["equivalence"]
    _require(
        provenance["equivalence_sha256"] == implementation._json_fingerprint(equivalence),
        "Saved C0 summary hash mismatch",
    )
    _require(
        implementation._equivalence_is_current(
            equivalence, operational / implementation.EQUIVALENCE_EVENTS_PATH, expected,
        ),
        "Saved C0 runtime provenance/events are stale or failed",
    )
    _require(
        implementation._sha256(operational / implementation.VALIDATION_PATH) == validation["record_sha256"],
        "Independent validation receipt hash mismatch",
    )


def _verify_snapshots(directory, indexed, contract, averages):
    fields = {
        "config_id", "alpha_label", "snapshot_type", "synchronization_id", "bucket_epoch",
        "bucket_time_utc", "algorithm", "selected_partition", "selected_partition_quality",
        "cluster_count", "coordinator_assignments", "raw_sensor_histories", "normalized_histories",
        "global_average", "global_violated", "p90_threshold", "root_allowance",
        "moment_observation_count", "weight_status", "first_moments", "second_moments",
        "conservative_terms", "raw_weights", "scaled_weights", "node_allowances", "coordinator_allowances",
    }
    rows = _csv_rows(directory / implementation.SNAPSHOTS_PATH, fields)
    expected = {("C1", "not_applicable"), ("C2", "not_applicable")}
    for method in ("FMIC", "SMIC"):
        minimum = min(row["total_messages"] for key, row in indexed.items() if key[0] == method)
        expected.add((method, "0.10"))
        expected.update(key for key, row in indexed.items() if key[0] == method and row["total_messages"] == minimum)
    seen = set()
    counts = Counter()
    sensors = contract["config"]["selected_sensor_ids"]
    threshold = contract["threshold"]
    for row in rows:
        key = _result_key(row)
        sid = _number(row["synchronization_id"], "snapshot/id", integer=True, nonnegative=True)
        epoch = _number(row["bucket_epoch"], "snapshot/epoch", integer=True)
        _require(key in expected and (key, sid) not in seen and epoch in averages, "Unexpected/duplicate snapshot")
        _require(sid == counts[key] + 1 and row["snapshot_type"] == "synchronization", "Nonsequential snapshot")
        _require(int(pd.Timestamp(row["bucket_time_utc"]).timestamp()) == epoch, "Snapshot timestamp mismatch")
        seen.add((key, sid))
        counts[key] += 1
        partition = json.loads(row["selected_partition"])
        _require(
            isinstance(partition, list)
            and all(isinstance(cluster, list) and cluster for cluster in partition),
            "Snapshot partition must contain nonempty cluster lists",
        )
        members = [sensor for cluster in partition for sensor in cluster]
        _require(
            all(partition) and sorted(members) == sensors
            and _number(row["cluster_count"], "snapshot/cluster_count", integer=True) == len(partition),
            "Snapshot partition does not cover the cohort exactly once",
        )
        _require(row["algorithm"] == indexed[key]["algorithm"], "Snapshot method mismatch")
        _number(row["selected_partition_quality"], "snapshot/partition quality", nonnegative=True)
        _require(
            _number(row["moment_observation_count"], "snapshot/moment count", integer=True, nonnegative=True)
            == (epoch - min(averages)) // 60,
            "Snapshot persistent moment count disagrees with source timeline",
        )
        assignments = json.loads(row["coordinator_assignments"])
        _require(
            assignments == {str(index): max(cluster) for index, cluster in enumerate(partition)},
            "Snapshot coordinator assignments do not match partition",
        )
        for field in (
            "raw_sensor_histories", "normalized_histories", "first_moments", "second_moments",
            "conservative_terms", "raw_weights", "scaled_weights",
        ):
            values = json.loads(row[field]) if row[field] else None
            required = field in ("raw_sensor_histories", "raw_weights", "scaled_weights")
            if required or values is not None:
                _require(
                    isinstance(values, dict) and set(values) == set(sensors),
                    f"snapshot/{field}: invalid sensor mapping",
                )
                for sensor, value in values.items():
                    _number(value, f"snapshot/{field}/{sensor}")
        scaled = json.loads(row["scaled_weights"])
        _same_number(math.fsum(scaled.values()), 6, "snapshot/scaled-weight budget")
        _same_number(row["global_average"], averages[epoch], "snapshot/source average")
        _require(float(row["p90_threshold"]) == threshold, "Snapshot threshold lost full precision")
        _require(int(row["global_violated"]) == int(averages[epoch] >= threshold), "Snapshot truth disagrees with source")
        allowance = abs(averages[epoch] - threshold)
        _same_number(row["root_allowance"], allowance, "snapshot/root allowance")
        node = json.loads(row["node_allowances"])
        coordinators = json.loads(row["coordinator_allowances"])
        _require(set(node) == set(sensors) and set(coordinators) == {max(cluster) for cluster in partition}, "Snapshot allowance membership mismatch")
        for sensor, value in node.items():
            _number(value, f"snapshot/{sensor} allowance", nonnegative=True)
        _same_number(math.fsum(node.values()), 6 * allowance, "snapshot/allowance budget")
        for cluster in partition:
            _same_number(
                coordinators[max(cluster)], math.fsum(node[sensor] for sensor in cluster) / len(cluster),
                "snapshot/coordinator allowance",
            )
        if key[0] in ("C1", "C2"):
            _require(partition == [[sensor] for sensor in sensors], "Control snapshot is not singleton")
    _require(set(counts) == expected, "Missing snapshot configurations")
    for key in expected:
        _require(counts[key] == indexed[key]["root_synchronization_count"], f"{key}: incomplete snapshot history")
    return len(rows)


def _directory_hashes(directory):
    _require(directory.is_dir(), f"Saved-output directory does not exist: {directory}")
    return {
        str(path.relative_to(directory)): implementation._sha256(path)
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def _paired_directory_hashes(directory):
    hashes = _directory_hashes(directory)
    operational = implementation._resolve_operational_dir(directory)
    if operational.is_dir() and not operational.is_relative_to(directory):
        hashes.update({
            str(Path("..") / operational.name / path.relative_to(operational)): implementation._sha256(path)
            for path in sorted(operational.rglob("*")) if path.is_file()
        })
    return hashes


def verify_saved_outputs(directory):
    """Read-only independent accounting/source checks; never refresh validation."""
    directory = directory.resolve()
    before = _paired_directory_hashes(directory)
    try:
        run = implementation.load_phase3_run(ROOT, directory)
        report, completion, failure = (run[name] for name in ("comparison", "completion", "failures"))
        _require(
            report["status"] == completion["status"] == failure["status"] == "passed"
            and bool(report["run_id"]) and report["run_id"] == completion["run_id"] == failure["run_id"]
            and failure["failure_count"] == 0 and failure["failures"] == [],
            "Saved reports do not identify the same successful current run",
        )
        _verify_saved_provenance(directory, report)
        contract, observations, columns, averages, violations = _source_observations()
        experiment = report["experiment"]
        _require(
            experiment["sensor_ids"] == contract["config"]["selected_sensor_ids"]
            and experiment["name"] == contract["config"]["experiment_name"]
            and experiment["bucket_count"] == len(observations)
            and experiment["threshold"] == contract["threshold"]
            and experiment["boundary_convention"] == contract["config"]["boundary_convention"]
            and experiment["alpha_grid"] == list(APPROVED_ALPHAS),
            "Saved experiment differs from the locked source contract",
        )
        indexed = _verify_result_tables(directory, len(observations), violations)
        _require(report["alpha_results_count"] == 38 and len(report["controls"]) == 3, "Incomplete summary grid")
        for control in report["controls"]:
            saved = indexed[control["config_id"], "not_applicable"]
            for field in (*RESULT_COUNTS, *RESULT_FLOATS):
                _same_number(control[field], saved[field], f"summary/{control['config_id']}/{field}")
        for method in ("FMIC", "SMIC"):
            minimum = min(row["total_messages"] for key, row in indexed.items() if key[0] == method)
            labels = sorted(key[1] for key, row in indexed.items() if key[0] == method and row["total_messages"] == minimum)
            _require(
                report["alpha_minima"][method]["minimum_total_messages"] == minimum
                and report["alpha_minima"][method]["alpha_labels"] == labels,
                f"{method}: saved exploratory ranking mismatch",
            )
        table = report["configuration_comparison_table"]
        keys = [(*_result_key(row), row["comparison_scope"]) for row in table]
        expected_keys = {
            ("revised_phase2", "not_applicable", "matched_primary_comparator"),
            *(("C" + str(index), "not_applicable", "singleton_control") for index in range(3)),
            *((method, "0.10", "prespecified_alpha_0.10") for method in ("FMIC", "SMIC")),
            *((method, alpha, "exploratory_in_sample_tested_grid_minimum") for method in ("FMIC", "SMIC") for alpha in report["alpha_minima"][method]["alpha_labels"]),
        }
        _require(len(keys) == len(set(keys)) and set(keys) == expected_keys, "Saved comparison table configurations mismatch")
        for row in table:
            key = _result_key(row)
            saved = indexed[("C0", "not_applicable") if key[0] == "revised_phase2" else key]
            for field in ("total_messages", "root_synchronization_count", "coordinator_check_count",
                          "checks_resolved_without_escalation", "checks_escalated"):
                _same_number(row[field], saved[field], f"comparison table/{key}/{field}")
            _same_number(
                row["centralized_reduction_percent"],
                100 * (1 - saved["total_messages"] / (len(observations) * 6)),
                f"comparison table/{key}/centralized reduction",
            )
        snapshots = _verify_snapshots(directory, indexed, contract, averages)
        # Recompute the equal-allowance trace from observations, not saved status flags.
        phase2 = build_phase2_trace(observations, columns, contract["threshold"], round_output=False)
        c0 = run_phase3_control(observations, columns, contract["threshold"], FMICMonitor)
        comparison = compare_decisions(phase2, c0.decision_trace, columns, c0.events)
        _require(comparison["passed"], "Fresh per-bucket C0/Phase 2 equivalence failed")
        with tempfile.TemporaryDirectory() as temporary:
            fresh = implementation.run_phase3a_protocol_equivalence(ROOT, Path(temporary))
            _require(fresh["status"] == "passed", "Fresh C0 runtime verification failed")
            _require(
                (Path(temporary) / implementation.EQUIVALENCE_EVENTS_PATH).read_bytes()
                == (implementation._resolve_operational_dir(directory) / implementation.EQUIVALENCE_EVENTS_PATH).read_bytes(),
                "Saved C0 events differ from fresh source-derived equivalence",
            )
        replay_records = report["reproducibility"]["fresh_process_replays"]
        _require(set(replay_records) == {f"{method}:{alpha}" for method, alpha, _, _ in REPLAY_SPECS}, "Incomplete saved replay coverage")
        for method, alpha, _, _ in REPLAY_SPECS:
            _compare_replay(replay_records[f"{method}:{alpha}"], indexed[method, alpha])
        analysis_inputs = implementation.load_phase3_analysis_results(ROOT, directory)
        _require(
            len(analysis_inputs["controls"]) == 3 and len(analysis_inputs["alphas"]) == 38,
            "Read-only analysis loader lost saved configurations",
        )
        return {
            "configuration_count": len(indexed), "source_bucket_count": len(observations),
            "source_global_violations": violations, "snapshot_count": snapshots,
            "C0_per_bucket_equivalence": True,
        }
    finally:
        _require(before == _paired_directory_hashes(directory), "Saved verification modified production outputs or operational evidence")


def _compare_replay(actual, expected):
    for field in (
        "config_id", "algorithm", "alpha_label", "correctness_status", "bucket_count",
        "global_threshold_violation_count", "total_messages", "root_synchronization_count",
        "false_safe_count", "false_violated_count", "events_fingerprint",
    ):
        _require(actual[field] == expected[field], f"Fresh replay differs at {field}")
    _require(
        actual["message_counts_reconcile"] is True
        and actual["message_category_totals"] == {field: expected[field] for field in TRANSMISSIONS},
        "Fresh replay category reconciliation failed",
    )


def verify_production_replays(directory=None):
    before = _paired_directory_hashes(directory) if directory is not None else None
    try:
        if directory is not None:
            report = implementation.load_phase3_run(ROOT, directory)["comparison"]
            _verify_saved_provenance(directory, report)
        indexed = _verify_result_tables(directory, 19984, 1999) if directory is not None else None
        for method, alpha, messages, syncs in REPLAY_SPECS:
            command = [
                sys.executable, "-B", "-m", "scripts.phase3_implement", "--root", str(ROOT),
                "--replay", "--method", method, "--alpha", alpha,
            ]
            with tempfile.TemporaryDirectory() as temporary:
                environment = dict(os.environ, PYTHONPATH=str(ROOT))
                child = subprocess.run(
                    command, cwd=temporary, env=environment, text=True, capture_output=True, check=False,
                )
                _require(child.returncode == 0, f"Replay failed:\n{child.stdout}\n{child.stderr}")
                _require(list(Path(temporary).iterdir()) == [], "Read-only replay wrote files")
            actual = json.loads(child.stdout)
            _require(
                actual["total_messages"] == messages and actual["root_synchronization_count"] == syncs
                and actual["false_safe_count"] == actual["false_violated_count"] == 0,
                f"{method}/{alpha}: preserved replay reference mismatch",
            )
            if indexed is None:
                contract = implementation._validate_contract(ROOT)
                observations, columns = implementation._read_locked_observations(contract)
                row, _, _ = (
                    implementation._run_control(implementation, observations, columns, contract["threshold"], "FMIC" if method == "C1" else "SMIC")
                    if method in ("C1", "C2") else
                    implementation._run_alpha(implementation, observations, columns, contract["threshold"], method, alpha)
                )
            else:
                row = indexed[method, alpha]
            _compare_replay(actual, row)
    finally:
        if directory is not None:
            _require(before == _paired_directory_hashes(directory), "Replay verification modified saved outputs or operational evidence")


class WeightedProductionReplayTests(unittest.TestCase):
    def test_six_fresh_process_replays_match_independent_references_and_current_process(self):
        verify_production_replays()


class AnalysisNotebookTests(unittest.TestCase):
    def test_analysis_notebook_is_saved_only_and_revised_presentation_moved(self):
        path = ROOT / "scripts" / "phase3_analyze.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        imports = []
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn("test_phase", node.module or "")
                    if node.module == "scripts.phase3_implement":
                        imports.extend(alias.name for alias in node.names)
                if isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else (
                        node.func.attr if isinstance(node.func, ast.Attribute) else ""
                    )
                    self.assertNotIn(name, {
                        "FMICMonitor", "build_phase2_trace", "run_us325", "run_phase3_control",
                        "run_phase3a_alpha_sweep", "run_phase3a_protocol_equivalence",
                        "record_validation", "run_verification", "verify_saved_outputs",
                    })
        self.assertEqual(imports, ["load_phase3_analysis_results"])
        self.assertFalse(hasattr(implementation, "_plot_results"))
        self.assertFalse(hasattr(implementation, "_interpretation"))
        self.assertEqual(
            {tag for cell in notebook["cells"] for tag in cell["metadata"].get("tags", [])},
            {"settings", "load-saved", "c0-table", "comparison-tables",
             "existing-interpretation", "alpha-charts", "composition-charts",
             "diagnostic-tables", "historical-charts", "finish"},
        )

    def test_analysis_loader_missing_inputs_fail_without_writes_or_replays(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            implementation.subprocess, "run", side_effect=AssertionError("Analysis cannot replay")
        ):
            directory = Path(temporary)
            with self.assertRaisesRegex(FileNotFoundError, "saved Phase 3 output"):
                implementation.load_phase3_analysis_results(ROOT, directory)
            self.assertEqual(list(directory.iterdir()), [])

    def test_analysis_output_cells_are_not_a_production_receipt_dependency(self):
        self.assertNotIn(
            "scripts/phase3_analyze.ipynb", implementation.validation_provenance(ROOT)
        )

    def test_cutover_provenance_covers_current_references_not_retired_entry_points(self):
        provenance = implementation.validation_provenance(ROOT)
        self.assertIn("scripts/phase3_implement.py", provenance)
        self.assertIn("scripts/phase3_test.py", provenance)
        self.assertIn("scripts/shared_monitoring_engine.py", provenance)
        self.assertNotIn("scripts/build_phase2_temperature_sensors.ipynb", provenance)
        self.assertNotIn("scripts/phase2_general_dataset_archive.ipynb", provenance)
        self.assertFalse(any("notebook_sha256" in key for key in implementation._failure_provenance(ROOT)))
        self.assertEqual(
            {name for name in provenance if "phase3" in Path(name).stem and name.startswith("scripts/")
             and not Path(name).name.startswith("test_phase1_")},
            {"scripts/phase3_implement.py", "scripts/phase3_test.py"},
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                implementation._phase2_reference_directory(root)
            current = root / "artifacts" / "phase2_outputs"
            current.mkdir(parents=True)
            self.assertEqual(implementation._phase2_reference_directory(root), current)
            with self.assertRaises(FileNotFoundError):
                implementation.validation_provenance(root)

    def test_matched_baseline_requires_current_phase2_producer(self):
        contract = implementation._validate_contract(ROOT)
        phase2_path = contract["phase2_path"]
        original_hash = implementation._sha256
        self.assertEqual(contract["revised"]["provenance"]["code_sha256"], original_hash(phase2_path))

        def changed_phase2_hash(path):
            return "0" * 64 if Path(path) == phase2_path else original_hash(path)

        with mock.patch.object(implementation, "_sha256", side_effect=changed_phase2_hash):
            with self.assertRaisesRegex(ValueError, "current producer identity"):
                implementation._validate_contract(ROOT)

    def test_equivalence_cli_requires_isolation_and_rejects_mixed_modes(self):
        for options in (
            ["--equivalence"],
            ["--equivalence", "--replay"],
            ["--equivalence", "--historical-sweep"],
            ["--equivalence", "--validation-record", "receipt.json"],
        ):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    implementation.main(options)
                self.assertEqual(error.exception.code, 2)

    def test_analysis_loader_rejects_failed_or_mixed_run_records_before_presentation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _write_reference_tables(directory)
            operational = implementation._resolve_operational_dir(directory)
            shutil.copy2(
                implementation._phase3_reference_directory(ROOT) / "phase3a_protocol_equivalence_events.csv",
                operational / implementation.EQUIVALENCE_EVENTS_PATH,
            )
            (operational / implementation.VALIDATION_PATH).write_text("{}")
            for failed in (True, False):
                run = {
                    "schema_version": 2, "kind": "production", "run_id": "run", "status": "passed",
                    "layout": implementation._phase3_layout(directory, operational),
                    "semantics": implementation._bundle_semantics(),
                    "artifacts": implementation._artifact_inventory(directory, operational),
                    "summary": {
                        "artifact": implementation.SUMMARY_PATH,
                        "sha256": implementation._sha256(directory / implementation.SUMMARY_PATH),
                    },
                    **{name: {"run_id": "run" if name != "completion" else "different",
                              "status": "failed" if failed else "passed"}
                       for name in ("completion", "failures")},
                    "equivalence": {},
                }
                (operational / RUN_PATH).write_text(json.dumps(run))
                before = _directory_hashes(directory)
                with self.assertRaisesRegex(ValueError, "same successful current run"):
                    implementation.load_phase3_analysis_results(ROOT, directory)
                self.assertEqual(before, _directory_hashes(directory))


class SavedOutputValidationTests(unittest.TestCase):
    def test_artifact_names_and_csv_serialization_preserve_nulls_integers_and_precision(self):
        self.assertEqual(len(implementation.BUNDLE_FILES), 7)
        self.assertEqual(len(set(implementation.BUNDLE_FILES)), 7)
        self.assertTrue(all(name.startswith("phase3_") for name in implementation.BUNDLE_FILES))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / implementation.RESULTS_PATH
            number = 2 ** 60 + 1
            rows = [{"count": number, "value": 22.428666649999997, "nullable": None},
                    {"count": 0, "value": 0.1, "contrast": -2}]
            implementation._write_csv_records(path, rows)
            with path.open(newline="") as stream:
                saved = list(csv.DictReader(stream))
            self.assertEqual(int(saved[0]["count"]), number)
            self.assertEqual(float(saved[0]["value"]), rows[0]["value"])
            self.assertEqual(saved[0]["nullable"], "")
            self.assertEqual(saved[0]["contrast"], "")
            self.assertEqual(saved[1]["count"], "0")

    def test_old_output_bundle_is_rejected_without_writing_or_deleting_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "phase3a_us325_comparison_summary.json").write_text("protected previous bundle")
            before = _directory_hashes(directory)
            with self.assertRaisesRegex(ValueError, "clean phase3_outputs"):
                run_us325(ROOT, directory)
            self.assertEqual(before, _directory_hashes(directory))

    def test_failed_attempt_replaces_success_identity_despite_leftover_tables(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / implementation.RESULTS_PATH).write_text("leftover successful table")
            operational = implementation._resolve_operational_dir(directory)
            operational.mkdir(parents=True)
            (operational / RUN_PATH).write_text(json.dumps({
                "status": "passed", "run_id": "old", "comparison": {"status": "passed"},
            }))
            with mock.patch.object(implementation, "_validate_contract", side_effect=ValueError("injected attempt")):
                with self.assertRaisesRegex(ValueError, "injected attempt"):
                    run_us325(ROOT, directory)
            run = json.loads((operational / RUN_PATH).read_text())
            self.assertEqual(run["status"], "failed")
            self.assertNotEqual(run["run_id"], "old")
            self.assertNotIn("comparison", run)
            self.assertEqual(run["failures"]["failure_count"], 1)
            self.assertEqual((directory / implementation.RESULTS_PATH).read_text(), "leftover successful table")
            with self.assertRaises((ValueError, FileNotFoundError)):
                implementation.load_phase3_run(ROOT, directory)

    def test_schema_inventory_and_receipt_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _write_reference_tables(directory)
            operational = implementation._resolve_operational_dir(directory)
            (operational / implementation.VALIDATION_PATH).write_text("{}")
            (directory / implementation.SUMMARY_PATH).write_text(json.dumps({
                "schema_version": 1, "kind": "summary", "status": "passed",
                "run_id": "fixture",
                "comparison": {
                    "status": "passed", "run_id": "fixture",
                    "validation": {"artifact": implementation.VALIDATION_PATH, "sha256": "wrong"},
                },
            }))
            run = {
                "schema_version": 2, "kind": "production", "status": "passed", "run_id": "fixture",
                "semantics": implementation._bundle_semantics(),
                "artifacts": implementation._artifact_inventory(directory, operational),
                "summary": {
                    "artifact": implementation.SUMMARY_PATH,
                    "sha256": implementation._sha256(directory / implementation.SUMMARY_PATH),
                },
                "completion": {"status": "passed", "run_id": "fixture"},
                "failures": {"status": "passed", "run_id": "fixture", "failure_count": 0, "failures": []},
                "equivalence": {},
            }
            for mutation in ("version", "kind", "status", "scope", "hash", "rows", "columns", "receipt", "extra"):
                record = copy.deepcopy(run)
                if mutation == "version":
                    record["schema_version"] = 3
                elif mutation == "kind":
                    record["kind"] = "equivalence"
                elif mutation == "status":
                    record["status"] = "in_progress"
                elif mutation == "scope":
                    record["semantics"]["snapshots"] = "all configurations"
                elif mutation in ("hash", "rows", "columns"):
                    field = {"hash": "sha256", "rows": "row_count", "columns": "columns"}[mutation]
                    record["artifacts"][f"outputs/{implementation.RESULTS_PATH}"][field] = "corrupted"
                elif mutation == "extra":
                    (directory / "legacy.json").write_text("{}")
                (operational / RUN_PATH).write_text(json.dumps(record))
                before = _paired_directory_hashes(directory)
                with self.subTest(mutation=mutation), mock.patch.object(
                    implementation, "_read_validation_record",
                    return_value={"record_sha256": "actual independent receipt hash"},
                ), self.assertRaises(ValueError):
                    implementation.load_phase3_run(ROOT, directory)
                self.assertEqual(before, _paired_directory_hashes(directory))
                if mutation == "extra":
                    (directory / "legacy.json").unlink()

    def test_snapshot_schema_source_values_and_finite_moments_are_verified(self):
        contract, _, _, averages, _ = _source_observations()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _write_reference_tables(directory)
            indexed = _verify_result_tables(directory, 19984, 1999)
            _verify_snapshots(directory, indexed, contract, averages)
            path = directory / implementation.SNAPSHOTS_PATH
            with path.open(newline="") as stream:
                reader = csv.DictReader(stream)
                fields, original = reader.fieldnames, list(reader)
            for field, value in (
                ("selected_partition_quality", "nan"),
                ("moment_observation_count", "100"),
                ("raw_weights", '{"A": NaN, "C": 0, "D": 0, "E": 0, "F": 0, "G": 0}'),
                ("global_average", "999"),
            ):
                with self.subTest(field=field):
                    rows = [dict(original[0], **{field: value}), *original[1:]]
                    with (directory / path.name).open("w", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(rows)
                    with self.assertRaises(ValueError):
                        _verify_snapshots(directory, indexed, contract, averages)

    def test_saved_table_mutations_fail_independently_of_passing_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _write_reference_tables(directory)
            _verify_result_tables(directory, 19984, 1999)
            path = directory / implementation.RESULTS_PATH
            original = path.read_bytes()
            for mutation in ("count", "missing", "duplicate", "nonfinite", "share", "alpha", "schema", "kind", "null"):
                with self.subTest(mutation=mutation):
                    path.write_bytes(original)
                    with path.open(newline="") as stream:
                        reader = csv.DictReader(stream)
                        fields, rows = reader.fieldnames, list(reader)
                    if mutation == "count":
                        rows[0]["total_messages"] = str(int(rows[0]["total_messages"]) + 1)
                    elif mutation == "missing":
                        rows.pop()
                    elif mutation == "duplicate":
                        rows[-1] = dict(rows[0])
                    elif mutation == "nonfinite":
                        rows[0]["cluster_count_mean_per_sync_event"] = "nan"
                    elif mutation == "share":
                        rows[0]["within_cluster_messages_share_percent"] = "50"
                    elif mutation == "alpha":
                        rows[0]["alpha_label"] = "0.01"
                    elif mutation == "kind":
                        rows[0]["configuration_kind"] = "clustered"
                    elif mutation == "null":
                        rows[0]["matched_singleton_reduction_percent"] = "0"
                    else:
                        fields = [field for field in fields if field != "total_messages"]
                        for row in rows:
                            del row["total_messages"]
                    with path.open("w", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(rows)
                    with self.assertRaises(ValueError):
                        _verify_result_tables(directory, 19984, 1999)
            path.write_bytes(original)
            size_path = directory / implementation.CLUSTER_SIZES_PATH
            with size_path.open(newline="") as stream:
                sizes = list(csv.DictReader(stream))
            next(row for row in sizes if row["config_id"] == "FMIC")["alpha_label"] = "0.01"
            implementation._write_csv_records(size_path, sizes)
            with self.assertRaises(ValueError):
                _verify_result_tables(directory, 19984, 1999)

    def test_missing_output_and_stale_saved_provenance_fail_without_recertifying(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                verify_saved_outputs(directory)
            with mock.patch.object(implementation, "validation_provenance", return_value={"code": "current"}):
                with self.assertRaisesRegex(ValueError, "stale"):
                    _verify_saved_provenance(directory, {"validation": {"provenance": {"code": "stale"}}})
            self.assertEqual(list(directory.iterdir()), [])

    def test_full_precision_threshold_is_consumed_without_rounding(self):
        config = json.loads((ROOT / "config" / "phase3a_experiment_config.json").read_text())
        preparation = prepare_monitoring(ROOT)
        threshold = preparation["p90_value"]
        self.assertEqual(threshold, 22.428666649999997)
        self.assertNotEqual(threshold, round(threshold, 8))
        monitor = FMICMonitor(("A", "B"), threshold, 0.1)
        self.assertEqual(monitor.threshold, threshold)

    def test_inherited_smic_coverage_and_legacy_mapping_are_preserved(self):
        names = set(unittest.defaultTestLoader.getTestCaseNames(FMICProtocolTests))
        inherited = set(unittest.defaultTestLoader.getTestCaseNames(SMICProtocolTests))
        self.assertTrue(names <= inherited)
        for classes in LEGACY_COVERAGE.values():
            for name in classes:
                self.assertTrue(issubclass(globals()[name], unittest.TestCase))

    def test_verification_reports_cannot_overwrite_sources_results_or_checkpoints(self):
        provenance = implementation.validation_provenance(ROOT)
        for path in (
            ROOT / "scripts" / "README_scripts.md",
            implementation._phase3_reference_directory(ROOT) / "phase3a_us325_control_results.csv",
            ROOT / "artifacts" / "phase3_baseline_us327" / "checkpoint_seal.json",
            ROOT / "artifacts" / "phase3_outputs" / "phase3_results.csv",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _validate_report_path(path, None, provenance)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(ValueError):
                _validate_report_path(directory / "verification.json", directory, provenance)


def _build_suite(checks, output_dir=None, cross_phase=False):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    if "behavior" in checks:
        for classes in LEGACY_COVERAGE.values():
            for name in classes:
                if name != "ProductionReproducibilityTests":
                    suite.addTests(loader.loadTestsFromTestCase(globals()[name]))
        suite.addTests(loader.loadTestsFromTestCase(SavedOutputValidationTests))
        suite.addTests(loader.loadTestsFromTestCase(AnalysisNotebookTests))
    if "saved" in checks:
        _require(output_dir is not None, "--checks saved requires --output-dir")
        def saved_output_check():
            return verify_saved_outputs(output_dir)
        suite.addTest(unittest.FunctionTestCase(
            saved_output_check, description="Saved schemas, source oracle, accounting, snapshots and current provenance",
        ))
    if "replay" in checks:
        suite.addTests(loader.loadTestsFromTestCase(ProductionReproducibilityTests))
        def weighted_replay_check():
            return verify_production_replays(output_dir)
        suite.addTest(unittest.FunctionTestCase(
            weighted_replay_check, description="Six read-only weighted/control fresh-process replays",
        ))
    if cross_phase:
        suite.addTests(loader.loadTestsFromNames(CROSS_PHASE_MODULES))
    return suite


def _test_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _test_ids(item)
        else:
            yield item.id()


def _validate_report_path(path, output_dir, provenance):
    target = path.resolve()
    _require(target not in {(ROOT / relative).resolve() for relative in provenance}, "Verification report cannot overwrite a validated input or source file")
    _require(
        output_dir is None or not target.is_relative_to(output_dir.resolve()),
        "Verification report must be outside the saved-output directory",
    )
    _require(
        not any(target.is_relative_to(ROOT / name) for name in ("scripts", "config", "Data", ".git")),
        "Verification report cannot overwrite source files",
    )
    artifact_root = ROOT / "artifacts"
    is_default_validation_receipt = (
        target == artifact_root / "phase3_operational" / implementation.VALIDATION_PATH
    )
    protected_artifact_directories = (
        "phase3_outputs", "phase3_archive", "phase2_current",
        "phase2_outputs", "phase2_operational", "phase2_archive",
    )
    _require(
        not any(target.is_relative_to(artifact_root / name) for name in protected_artifact_directories)
        and (not target.is_relative_to(artifact_root / "phase3_operational") or is_default_validation_receipt),
        "Verification report cannot overwrite Phase 2/Phase 3 outputs or operational evidence",
    )
    if target.is_relative_to(artifact_root):
        relative = target.relative_to(artifact_root)
        _require(
            len(relative.parts) > 1 and not target.name.startswith("phase3a_")
            and not any(part.startswith(("phase3_baseline_", "phase3_extraction_", "phase3_production_")) for part in relative.parts),
            "Verification report cannot overwrite original outputs or archived migration evidence",
        )


def run_verification(checks, output_dir=None, report_path=None, cross_phase=False):
    checks = [name for name in ("behavior", "saved", "replay") if name in checks]
    _require(bool(checks), "Select at least one check")
    before = implementation.validation_provenance(ROOT)
    if report_path is not None:
        _validate_report_path(report_path, output_dir, before)
    protected_before = implementation._protected_hashes(ROOT)
    suite = _build_suite(checks, output_dir, cross_phase)
    ids = list(_test_ids(suite))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(stream.getvalue(), end="")
    after = implementation.validation_provenance(ROOT)
    protected_unchanged = protected_before == implementation._protected_hashes(ROOT)
    passed = result.wasSuccessful() and result.testsRun > 0 and not result.skipped and before == after and protected_unchanged
    record = {
        "schema_version": 2, "status": "passed" if passed else "failed",
        "returncode": 0 if passed else 1, "test_count": result.testsRun,
        "checks": checks, "cross_phase_modules": CROSS_PHASE_MODULES if cross_phase else [],
        "modules": ["scripts.phase3_test", *CROSS_PHASE_MODULES] if cross_phase else ["scripts.phase3_test"],
        "test_ids": ids, "skipped": [(case.id(), reason) for case, reason in result.skipped],
        "failures": [(case.id(), text) for case, text in result.failures],
        "errors": [(case.id(), text) for case, text in result.errors],
        "provenance": before, "inputs_and_code_unchanged": before == after,
        "protected_files_unchanged": protected_unchanged,
        "output_dir": str(output_dir.resolve()) if output_dir is not None else None,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-B", "-m", "scripts.phase3_test", *sys.argv[1:]],
        "test_output": stream.getvalue(),
    }
    if report_path is not None:
        implementation._write_json_atomic(report_path, record)
    return record


def record_validation(path):
    """Only behavioral + replay + external Phase 1/2 tests certify production."""
    return run_verification(["behavior", "replay"], report_path=path, cross_phase=True)["returncode"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", nargs="+", choices=("behavior", "saved", "replay"), default=None)
    parser.add_argument("--output-dir", type=Path, help="Existing saved results to verify read-only.")
    parser.add_argument("--report", type=Path, help="Verification report outside saved results; not a production receipt.")
    parser.add_argument("--record-validation", type=Path, help="Run behavior/replay and external Phase 1/2 suites; write a production receipt.")
    args = parser.parse_args(argv)
    if args.record_validation:
        if args.checks or args.output_dir or args.report:
            parser.error("--record-validation cannot be combined with check/output/report selectors")
        return record_validation(args.record_validation)
    checks = args.checks or ["behavior"]
    if "saved" in checks and args.output_dir is None:
        parser.error("--checks saved requires --output-dir")
    if args.output_dir is not None and not ({"saved", "replay"} & set(checks)):
        parser.error("--output-dir requires saved or replay checks")
    return run_verification(checks, args.output_dir, args.report)["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
