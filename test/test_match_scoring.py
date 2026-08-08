"""
Sigmoid match scoring — `matching_manager.calculate_match_score`.

WHY THIS IS THE MOST IMPORTANT THING IN THE SUITE
-------------------------------------------------
This single function decides whether a worker is shown to a customer at all.
Every match in the platform is filtered by `score > SCORE_THRESHOLD`, so a
silent change to its steepness or midpoint silently changes who gets work.
That has already gone wrong once in this project's history: a curve centred
on d=0.90 scored completely unrelated trades at 86%.

These tests pin down the CURRENT calibration:

    score = clamp(round(100 / (1 + e^(11.0 * (d - 0.68))) , 2), 0, 100)
    SCORE_THRESHOLD = 70.0

They are written as characterisation tests. If someone recalibrates the
curve, several of these will fail loudly — that is the intent. The failure
is a prompt to update the constants here deliberately, together with the
threshold and any offline evaluation, rather than discovering months later
that match quality drifted.
"""

from __future__ import annotations

import math

import pytest

from backend.src.core.matching_manager import SCORE_THRESHOLD, calculate_match_score


class TestSigmoidShape:
    """The curve's defining mathematical properties."""

    def test_midpoint_scores_exactly_fifty(self):
        """
        d == 0.68 is the inflection point, so it must score exactly 50.
        This is the single most diagnostic assertion in the file: it pins
        the midpoint constant on its own, independent of steepness.
        """
        assert calculate_match_score(0.68) == 50.0

    def test_identical_vectors_score_near_perfect(self):
        """Distance 0.0 means semantically identical text."""
        assert calculate_match_score(0.0) == pytest.approx(99.94, abs=0.01)

    def test_score_decreases_monotonically_as_distance_grows(self):
        """
        A worker further away in vector space must never score higher than a
        closer one. Any violation would scramble match ranking order.
        """
        scores = [calculate_match_score(i / 200.0) for i in range(201)]
        for closer, further in zip(scores, scores[1:]):
            assert closer >= further

    @pytest.mark.parametrize(
        "distance, expected",
        [
            (0.00, 99.94),
            (0.30, 98.49),
            (0.50, 87.87),
            (0.60, 70.68),
            (0.65, 58.18),
            (0.68, 50.00),  # midpoint
            (0.70, 44.52),
            (0.75, 31.65),
            (0.80, 21.08),
            (0.87, 11.01),
            (1.00, 2.87),
        ],
    )
    def test_known_points_on_the_curve(self, distance, expected):
        """
        Characterisation of the exact calibration in use. These numbers were
        derived from the formula itself, not copied from a previous run.
        """
        assert calculate_match_score(distance) == pytest.approx(expected, abs=0.01)

    def test_matches_the_closed_form_formula(self):
        """
        Guards against a refactor that changes the arithmetic while keeping
        roughly similar outputs — recomputed independently here.
        """
        for distance in (0.1, 0.35, 0.55, 0.68, 0.72, 0.95):
            expected = round(
                (1.0 / (1.0 + math.exp(11.0 * (distance - 0.68)))) * 100.0, 2
            )
            assert calculate_match_score(distance) == expected


class TestScoreBounds:
    """A score is a percentage and must always be presentable as one."""

    @pytest.mark.parametrize(
        "distance",
        [-5.0, -1.0, 0.0, 0.5, 0.68, 1.0, 2.0, 50.0],
    )
    def test_always_within_zero_and_one_hundred(self, distance):
        score = calculate_match_score(distance)
        assert 0.0 <= score <= 100.0

    def test_very_large_distance_floors_at_zero(self):
        """Cosine distance shouldn't exceed 2.0, but the clamp must hold."""
        assert calculate_match_score(50.0) == 0.0

    def test_rounded_to_two_decimal_places(self):
        """Scores are persisted and rendered, so precision is part of the contract."""
        for distance in (0.13, 0.37, 0.64, 0.81):
            score = calculate_match_score(distance)
            assert round(score, 2) == score

    def test_infinities_are_handled_without_raising(self):
        """
        math.exp overflows to inf for large inputs rather than raising, so
        these fall through the clamp. Documented here so the behaviour is
        known rather than assumed.
        """
        assert calculate_match_score(float("inf")) == 0.0
        assert calculate_match_score(float("-inf")) == 100.0

    def test_non_numeric_input_degrades_to_zero_instead_of_crashing(self):
        """
        The function wraps its body in try/except and returns 0.0 on error.
        A bad value must never take down a whole matching run — but it must
        also never become a passing score.
        """
        assert calculate_match_score(None) == 0.0  # type: ignore[arg-type]
        assert calculate_match_score("not-a-number") == 0.0  # type: ignore[arg-type]


class TestThresholdInteraction:
    """
    `create_matches_for_job` keeps a candidate only when
    `score > SCORE_THRESHOLD`. These tests describe where that cut lands on
    the distance axis, which is the number that actually governs recall.
    """

    def test_threshold_is_seventy(self):
        assert SCORE_THRESHOLD == 70.0

    def test_distance_060_passes_the_threshold(self):
        """d=0.60 -> 70.68, just above the cut. The boundary is this tight."""
        assert calculate_match_score(0.60) > SCORE_THRESHOLD

    def test_distance_061_fails_the_threshold(self):
        """
        d=0.61 -> ~68.3. Combined with the test above this brackets the
        effective cutoff to a 0.01-wide band, so any recalibration of either
        the curve or the threshold trips one of these two tests.
        """
        assert calculate_match_score(0.61) <= SCORE_THRESHOLD

    def test_effective_cutoff_distance_is_about_061(self):
        """
        Documents the practical consequence: only workers within roughly
        0.61 cosine distance are ever persisted as matches.
        """
        first_rejected = next(
            d / 100.0
            for d in range(0, 201)
            if calculate_match_score(d / 100.0) <= SCORE_THRESHOLD
        )
        assert first_rejected == pytest.approx(0.61, abs=0.001)

    def test_midpoint_distance_is_rejected(self):
        """
        A 50% score sits well below the 70 threshold — worth stating
        explicitly, because "the midpoint passes" is an easy false
        assumption when reading the formula alone.
        """
        assert calculate_match_score(0.68) <= SCORE_THRESHOLD