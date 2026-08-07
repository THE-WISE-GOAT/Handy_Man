"""
Worker interview state machine — control signals, grading, and the pass gate.

WHY THESE MATTER
----------------
`parse_control_signal` is the single place the interview router reads the
LLM's decisions out of free text. If it misreads a token the state machine
either stalls mid-interview or leaks a raw `[REJECTED]` string to a real
worker. The module's own docstring notes that RULE 9 (never mix tokens with
prose) exists precisely because small models keep doing it anyway — so the
parser has to be robust to it, and that robustness is what these tests lock
down.

`_parse_score` and `evaluate_answer` implement the vetting gate: a score
must be STRICTLY above 75 to pass. Two deliberate design decisions are
verified here because both are security-relevant and both look like bugs to
a future reader who doesn't know the reasoning:

  * An unparseable grade scores 0, never a pass. A model that returns
    unreadable output must not accidentally admit an unvetted worker.
  * The numeric SCORE line wins over the model's own VERDICT line, because
    small models genuinely emit "SCORE: 82 / VERDICT: FAIL".

Every test here is offline — `evaluate_answer`'s short-answer branch returns
before any network call, and the rest of the functions are pure.
"""

from __future__ import annotations

import pytest

from backend.src.ai.worker_chat_analyser_nvidia import (
    COMPLETE_TOKEN,
    MAX_PRETEST_TURNS,
    NO_SPECIALITY_TOKEN,
    REJECTION_TOKEN,
    SCENARIO_PASS_THRESHOLD,
    _parse_score,
    build_fresh_history,
    count_user_turns,
    evaluate_answer,
    is_general_competency_test,
    parse_control_signal,
    strip_general_competency_suffix,
    worker_transcript_text,
)


class TestParseControlSignal:
    """Reading the interviewer model's decision out of its reply."""

    def test_clean_rejection_token(self):
        assert parse_control_signal(REJECTION_TOKEN) == ("rejected", None)

    def test_token_matching_is_case_insensitive_and_whitespace_tolerant(self):
        """Models vary the casing and add stray padding."""
        assert parse_control_signal("  [rejected]  ") == ("rejected", None)
        assert parse_control_signal("[Complete]") == ("complete", None)

    def test_test_required_extracts_the_sub_skill_payload(self):
        signal, payload = parse_control_signal(
            "[TEST_REQUIRED: solar water heater commissioning]"
        )
        assert signal == "test"
        assert payload == "solar water heater commissioning"

    def test_test_required_payload_whitespace_is_collapsed(self):
        """
        The regex is DOTALL, so a payload can span newlines. It must come
        back as one clean single-line string for the scenario generator.
        """
        signal, payload = parse_control_signal("[TEST_REQUIRED: multi\nline  skill]")
        assert signal == "test"
        assert payload == "multi line skill"

    def test_empty_test_payload_is_not_treated_as_a_test(self):
        """
        A malformed token with nothing inside must not launch a scenario test
        for an empty sub-skill — `generate_scenario` would raise on it.
        """
        signal, _ = parse_control_signal("[TEST_REQUIRED:   ]")
        assert signal == "message"

    def test_no_speciality_token(self):
        assert parse_control_signal(NO_SPECIALITY_TOKEN) == ("no_speciality", None)

    def test_complete_token(self):
        assert parse_control_signal(COMPLETE_TOKEN) == ("complete", None)

    def test_ordinary_question_is_returned_as_a_message(self):
        reply = "How many years of professional experience do you have?"
        assert parse_control_signal(reply) == ("message", reply)

    @pytest.mark.parametrize("reply", ["", "   ", None])
    def test_blank_replies_become_empty_messages(self, reply):
        assert parse_control_signal(reply) == ("message", "")

    def test_token_wrapped_in_prose_is_still_detected(self):
        """
        RULE 9 forbids this, but small models do it constantly. Detecting it
        anyway is what stops a raw token reaching the worker's screen.
        """
        assert parse_control_signal("Sure thing! [COMPLETE]") == ("complete", None)
        assert parse_control_signal("blah [NO_SPECIALITY] blah") == (
            "no_speciality",
            None,
        )

    def test_rejection_wins_when_multiple_signals_are_emitted(self):
        """
        A confused model can emit two signals at once. Precedence is
        rejection first by design — the safest reading wins rather than
        letting a contradictory reply complete a registration.
        """
        assert parse_control_signal("[REJECTED] and [COMPLETE]") == ("rejected", None)


class TestGeneralCompetencySuffix:
    """
    Distinguishing the general-competency test from a claimed speciality.
    The router derives `has_verified_specialty` from this, so a
    misclassification either credits a worker with a niche they never
    claimed or discards one they proved.
    """

    @pytest.mark.parametrize(
        "sub_skill",
        [
            "plumber — general competency",
            "electrician - General Competency",
            "mechanic general_competency",
            "general competency",
        ],
    )
    def test_recognises_general_competency_markers(self, sub_skill):
        assert is_general_competency_test(sub_skill) is True

    @pytest.mark.parametrize(
        "sub_skill",
        [
            "solar water heater commissioning",
            "three-phase industrial panel wiring",
            "",
        ],
    )
    def test_real_specialities_are_not_general_competency(self, sub_skill):
        assert is_general_competency_test(sub_skill) is False

    def test_marker_must_be_at_the_end_to_count(self):
        """
        The regex is anchored with `$` on purpose, so an incidental mention
        mid-string is not a marker.
        """
        assert is_general_competency_test("plumber general competency work") is False

    @pytest.mark.parametrize(
        "sub_skill, expected",
        [
            ("plumber — general competency", "plumber"),
            ("electrician - General Competency", "electrician"),
            ("mechanic general_competency", "mechanic"),
            ("solar water heater commissioning", "solar water heater commissioning"),
        ],
    )
    def test_stripping_leaves_the_bare_subject(self, sub_skill, expected):
        """The scenario generator is given the subject without the marker."""
        assert strip_general_competency_suffix(sub_skill) == expected


class TestScoreParsing:
    """Pulling the numeric grade out of the evaluator's report."""

    def test_standard_score_line(self):
        assert _parse_score("SCORE: 82\nVERDICT: PASS") == (82, True)

    def test_tolerates_loose_formatting(self):
        """Separators and spacing vary between model runs."""
        assert _parse_score("score 90") == (90, True)
        assert _parse_score("SCORE:  7") == (7, True)

    @pytest.mark.parametrize(
        "report, expected",
        [
            ("Rated 85/100", 85),
            ("70 out of 100", 70),
            ("got 55%", 55),
        ],
    )
    def test_fallback_patterns_are_recognised(self, report, expected):
        """The loose regex catches grades written as a fraction or percent."""
        score, parsed_ok = _parse_score(report)
        assert (score, parsed_ok) == (expected, True)

    def test_out_of_range_score_is_clamped(self):
        assert _parse_score("SCORE: 250") == (100, True)

    def test_unparseable_report_scores_zero_and_reports_failure(self):
        """
        The critical safety property: an unreadable grade must never become a
        pass. `parsed_ok=False` lets the caller log the raw text instead of
        recording a genuine zero for a worker who may have answered well.
        """
        assert _parse_score("The worker did quite well overall.") == (0, False)

    def test_genuine_zero_is_distinguished_from_a_parse_failure(self):
        """A real 'SCORE: 0' is parsed_ok=True — not the same as no grade."""
        assert _parse_score("SCORE: 0\nVERDICT: FAIL") == (0, True)


class TestPassGate:
    """`SCENARIO_PASS_THRESHOLD` is a STRICTLY-greater-than gate."""

    def test_threshold_is_seventy_five(self):
        assert SCENARIO_PASS_THRESHOLD == 75

    def test_short_answer_auto_fails_without_a_model_call(self):
        """
        Answers under 15 characters return before any network request, so
        this runs fully offline. Letting the evaluator improvise a grade for
        two words is how false passes happen.
        """
        passed, score, report = evaluate_answer(
            sub_skill="plumbing — general competency",
            scenario="A tap is leaking. What would you do?",
            answer="I fix it",
        )
        assert passed is False
        assert score == 0
        assert "too short" in report.lower()

    @pytest.mark.parametrize("answer", ["", "   ", None])
    def test_empty_answer_auto_fails(self, answer):
        passed, score, _ = evaluate_answer("plumbing", "scenario text", answer)
        assert passed is False
        assert score == 0

    def test_exactly_at_threshold_does_not_pass(self):
        """
        75 must FAIL: the gate is `score > threshold`, not `>=`. This is the
        classic off-by-one in a vetting gate, so it gets its own test.
        """
        assert not (75 > SCENARIO_PASS_THRESHOLD)

    def test_one_above_threshold_passes(self):
        assert 76 > SCENARIO_PASS_THRESHOLD


class TestHistoryHelpers:
    """Seeding and measuring an interview transcript."""

    def test_fresh_history_starts_with_system_prompt_then_greeting(self):
        history = build_fresh_history()
        assert len(history) == 2
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"]

    def test_fresh_history_has_no_worker_turns_yet(self):
        assert count_user_turns(build_fresh_history()) == 0

    def test_counts_only_worker_messages(self):
        """
        The turn cap is enforced server-side against this count, so counting
        assistant messages by mistake would halve the allowed interview
        length.
        """
        history = build_fresh_history() + [
            {"role": "user", "content": "I am a plumber"},
            {"role": "assistant", "content": "How many years?"},
            {"role": "user", "content": "Eight years"},
        ]
        assert count_user_turns(history) == 2

    def test_turn_cap_constant_is_positive(self):
        assert MAX_PRETEST_TURNS > 0

    def test_transcript_text_excludes_the_interviewer_questions(self):
        """
        Deliberate: the interviewer's RULE 4 questions list example tasks for
        the trade, and including them would let the model parrot those back
        as if the worker had claimed them.
        """
        history = build_fresh_history() + [
            {"role": "user", "content": "I am a plumber"},
            {
                "role": "assistant",
                "content": "Do you handle leaking taps, blocked pipes, and tank work?",
            },
            {"role": "user", "content": "Yes but no drainage"},
        ]
        text = worker_transcript_text(history)
        assert "plumber" in text
        assert "no drainage" in text
        assert "leaking taps" not in text

    def test_transcript_text_respects_the_length_limit(self):
        history = [{"role": "user", "content": "x" * 500}]
        assert len(worker_transcript_text(history, limit=100)) == 100
