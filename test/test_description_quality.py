"""
Embedding-text quality guards and the two-layer description composition.

WHY THESE MATTER
----------------
Everything in this file protects the text that becomes a worker's vector.
A bad description is not a cosmetic problem: as the module docstring puts it,
"I am an experienced and reliable plumber" embeds nowhere near a customer
typing "my tap is leaking", and that worker is then quietly unmatchable for
the rest of their time on the platform. There is no error, no log — they just
stop getting work.

Two mechanisms are covered:

  1. `_description_quality_problem` — the mechanical guard that catches
     first-person voice, sales language, list formatting, and stub text
     before it reaches the embedding. Prompt instructions alone do not
     reliably keep a small model out of sales voice, which is exactly why
     this check exists in code.

  2. `_compose_job_description` — the deterministic baseline+speciality
     layering. This is Python rather than a model instruction on purpose:
     when composition was left to the model, workers with no niche got
     invented specialist text, and workers WITH a niche lost their ordinary
     trade scope. Both failures are invisible until match quality degrades,
     so the guarantee is structural and tested here.

Also covered: `_normalise_job_category`, which is what makes two plumbers
converge on byte-identical baseline text (and drives the baseline cache key).
If normalisation breaks, baseline text fragments across workers in the same
trade and the shared half of their vectors stops overlapping.

All functions here are pure string logic — no network, no database.
"""

from __future__ import annotations

import pytest

from backend.src.ai.worker_chat_analyser_nvidia import (
    _baseline_cache_key,
    _clean_description_text,
    _compose_job_description,
    _description_quality_problem,
    _normalise_job_category,
    _slugify_tag,
)

# A realistic, well-formed baseline description: third person, concrete
# nouns, task-oriented, long enough to carry matchable detail. Used as the
# "known good" control throughout.
GOOD_DESCRIPTION = (
    "Repairs leaking taps, mixers, and water pipes in homes and shops, and "
    "clears blocked drains and sewer lines. Installs bathroom and kitchen "
    "fittings."
)


class TestDescriptionQualityGuard:
    """What must be rejected before it can poison a worker's vector."""

    def test_well_formed_description_passes(self):
        assert _description_quality_problem(GOOD_DESCRIPTION) is None

    def test_rejects_first_person_voice(self):
        """
        First person is the single worst failure mode: it shifts the vector
        toward self-description and away from the task vocabulary customers
        actually type.
        """
        text = (
            "I repair leaking taps and water pipes in homes and shops, and I "
            "clear blocked drains and sewer lines every day."
        )
        assert _description_quality_problem(text) == "uses first-person voice"

    def test_rejects_sales_and_credential_language(self):
        text = (
            "Repairs leaking taps and pipes in homes and shops, offering "
            "experienced service and quality drain clearing work throughout."
        )
        assert _description_quality_problem(text) == "uses credential or sales language"

    def test_rejects_text_too_short_to_be_matchable(self):
        assert (
            _description_quality_problem("Fixes taps.")
            == "too short to carry any matchable detail"
        )

    def test_rejects_bullet_list_formatting(self):
        text = (
            "- Repairs leaking taps and mixers in homes\n"
            "- Clears blocked drains and sewer lines\n"
            "- Installs bathroom and kitchen fittings\n"
            "- Fixes water tank and pump problems\n"
            "- Replaces pipes"
        )
        assert (
            _description_quality_problem(text)
            == "is formatted as a list rather than sentences"
        )

    @pytest.mark.parametrize("text", ["", None, "   "])
    def test_blank_text_is_rejected(self, text):
        assert _description_quality_problem(text) is not None

    def test_sixty_characters_is_the_length_floor(self):
        """
        Documents the exact boundary, so a future tweak to the minimum is a
        deliberate decision rather than an accident.
        """
        # 59 concrete characters, no banned words — rejected on length alone.
        just_short = "Repairs taps and pipes and clears drains in homes and shops"
        assert len(just_short) < 60
        assert (
            _description_quality_problem(just_short)
            == "too short to carry any matchable detail"
        )


class TestJobDescriptionComposition:
    """
    The two-layer guarantee:
        has_verified_specialty=True   -> baseline + speciality
        has_verified_specialty=False  -> baseline only
    """

    def test_without_verified_specialty_only_baseline_is_used(self):
        """
        A worker who never claimed a niche must not be credited with
        specialist text — even if some is passed in.
        """
        result = _compose_job_description(
            "Fixes taps and pipes.", "Commissions solar water heaters.", False
        )
        assert result == "Fixes taps and pipes."
        assert "solar" not in result

    def test_with_verified_specialty_both_layers_are_joined(self):
        result = _compose_job_description(
            "Fixes taps and pipes.", "Commissions solar water heaters.", True
        )
        assert result == "Fixes taps and pipes. Commissions solar water heaters."

    def test_missing_sentence_punctuation_is_added_when_joining(self):
        """Without this the two layers would run together into one sentence."""
        result = _compose_job_description("Fixes taps", "Commissions heaters", True)
        assert result == "Fixes taps. Commissions heaters."

    def test_empty_speciality_falls_back_to_baseline(self):
        """
        A worker must never end up with an empty description just because the
        speciality half failed to generate.
        """
        assert _compose_job_description("Fixes taps.", "", True) == "Fixes taps."

    def test_empty_baseline_falls_back_to_speciality(self):
        """
        If baseline generation failed, the speciality text is all there is —
        better a partial description than none, which would make the worker
        unmatchable entirely.
        """
        assert (
            _compose_job_description("", "Commissions heaters.", True)
            == "Commissions heaters."
        )

    def test_speciality_already_covered_by_baseline_is_not_duplicated(self):
        """Avoids stitching on text the baseline already contains."""
        baseline = "Fixes taps and commissions solar heaters for homes."
        result = _compose_job_description(baseline, "commissions solar heaters", True)
        assert result == baseline

    def test_composition_is_deterministic(self):
        """Same inputs, same output — every time, no model involved."""
        args = ("Fixes taps.", "Commissions heaters.", True)
        assert _compose_job_description(*args) == _compose_job_description(*args)


class TestCleanDescriptionText:
    """Stripping the wrappers a model puts around prose."""

    def test_strips_markdown_code_fences(self):
        assert _clean_description_text("```json\nHello world\n```") == "Hello world"

    def test_strips_leading_labels(self):
        assert _clean_description_text("Baseline Scope: Fixes taps") == "Fixes taps"

    def test_flattens_bullets_into_prose(self):
        assert _clean_description_text("- one\n- two\n- three") == "one two three"

    def test_flattens_numbered_lists(self):
        assert _clean_description_text("1. first\n2. second") == "first second"

    def test_strips_wrapping_quotes(self):
        assert _clean_description_text('"quoted text"') == "quoted text"

    def test_collapses_whitespace_runs(self):
        assert _clean_description_text("  spaced   out  text ") == "spaced out text"

    @pytest.mark.parametrize("text", ["", None])
    def test_blank_input_returns_empty_string(self, text):
        assert _clean_description_text(text) == ""


class TestJobCategoryNormalisation:
    """
    Why this matters: normalisation is what makes two plumbers produce
    byte-identical baseline text. If it fragments, the shared half of their
    vectors stops overlapping and ordinary-job matching degrades.
    """

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Plumber (residential)", "plumber"),
            ("plumber", "plumber"),
            ("Electrician Technician", "electrician"),
            ("  Mason Services  ", "mason"),
            ("PLUMBING WORK", "plumbing"),
        ],
    )
    def test_variants_collapse_to_a_canonical_form(self, raw, expected):
        assert _normalise_job_category(raw) == expected

    def test_equivalent_spellings_agree(self):
        """The property that actually matters, stated directly."""
        assert _normalise_job_category("Plumber (residential)") == _normalise_job_category(
            "  PLUMBER  "
        )

    def test_non_latin_input_is_not_destroyed(self):
        """
        The fallback keeps the original when stripping would empty it — a
        Nepali or Devanagari trade name must not normalise to "".
        """
        assert _normalise_job_category("विद्युत") != ""


class TestBaselineCacheKey:
    """
    The cache is what keeps baseline text stable across a batch of workers.
    Key collisions would hand one worker another's scope; over-splitting
    would defeat the stability the layer exists for.
    """

    def test_same_trade_and_exclusions_share_a_key(self):
        assert _baseline_cache_key("plumber", []) == _baseline_cache_key("Plumber", [])

    def test_exclusion_order_and_casing_do_not_affect_the_key(self):
        """Exclusions are normalised and sorted, so ordering is irrelevant."""
        assert _baseline_cache_key("plumber", ["drainage", "Tank work"]) == (
            _baseline_cache_key("plumber", ["tank work", "Drainage"])
        )

    def test_different_exclusions_produce_different_keys(self):
        """
        A worker who opted out of part of the trade scope must get their own
        variant, not the shared one.
        """
        assert _baseline_cache_key("plumber", []) != _baseline_cache_key(
            "plumber", ["drainage"]
        )

    def test_different_trades_produce_different_keys(self):
        assert _baseline_cache_key("plumber", []) != _baseline_cache_key(
            "electrician", []
        )


class TestSlugifyTag:
    """Speciality tags double as database search filters."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Solar Water Heater", "solar-water-heater"),
            ("  a  b  ", "a-b"),
            ("C++ welding!!", "c-welding"),
        ],
    )
    def test_produces_lowercase_hyphenated_slugs(self, raw, expected):
        assert _slugify_tag(raw) == expected

    def test_collapses_repeated_separators(self):
        assert "--" not in _slugify_tag("a   ///   b")

    @pytest.mark.parametrize("raw", ["---", "", None, "!!!"])
    def test_unsluggable_input_yields_empty_string(self, raw):
        assert _slugify_tag(raw) == ""
