"""
LLM reranker output parsing — `matching_manager._extract_json_array`.

WHY THIS MATTERS
----------------
The reranker is the final filter that drops workers from the wrong trade
before matches are persisted. Its entire contract with the LLM is "return
ONLY a JSON array of worker_id integers" — and small models routinely wrap
that in prose, markdown fences, or an object.

The failure is asymmetric and silent. If parsing returns `[]`, the reranker
produces no ordered ids, and `create_matches_for_job` persists NOTHING for
that job. There is no exception and no log line saying matching was skipped;
the customer just sees an empty result. My notes on this project record that
the reranker was already silently dead once before, from a formatting bug —
so these tests exist to make that class of failure loud.

The tests also cover the id-coercion filter applied to the parsed output,
which is what stops a hallucinated string like "worker_7" from becoming an
int and crashing the rerank loop.

Pure string/JSON logic — no network, no database.
"""

from __future__ import annotations

import pytest

from backend.src.core.matching_manager import (
    MAX_CANDIDATES_FOR_RERANK,
    RERANK_MODEL,
    _extract_json_array,
)


class TestExtractJsonArray:
    """Getting an id list out of whatever the model actually returned."""

    def test_clean_json_array(self):
        assert _extract_json_array("[1, 2, 3]") == [1, 2, 3]

    def test_strips_markdown_json_fence(self):
        """The single most common deviation from "return ONLY JSON"."""
        assert _extract_json_array("```json\n[4, 5]\n```") == [4, 5]

    def test_strips_bare_markdown_fence(self):
        assert _extract_json_array("```\n[6, 7]\n```") == [6, 7]

    def test_unwraps_an_object_containing_the_list(self):
        """Models often helpfully wrap the array in a named key."""
        assert _extract_json_array('{"kept": [7, 8]}') == [7, 8]

    def test_finds_an_array_embedded_in_prose(self):
        """
        The regex fallback. Without it, a chatty model's reply parses as
        empty and the whole job silently gets zero matches.
        """
        assert _extract_json_array("Here you go: [9, 10] hope that helps") == [9, 10]

    def test_empty_array_is_preserved(self):
        """
        A genuine "keep nobody" is a legitimate reranker verdict and must
        round-trip as an empty list.
        """
        assert _extract_json_array("[]") == []

    def test_handles_whitespace_and_newlines(self):
        assert _extract_json_array("\n\n  [11, 12]  \n") == [11, 12]

    def test_preserves_the_models_ordering(self):
        """
        Order IS the ranking — the reranker returns best-fit first, and the
        loop assigns new ranks by position.
        """
        assert _extract_json_array("[30, 10, 20]") == [30, 10, 20]

    @pytest.mark.parametrize(
        "raw",
        [
            "no array here at all",
            "",
            '{"a": 1}',
            "I could not determine a ranking.",
        ],
    )
    def test_unparseable_output_degrades_to_empty_list(self, raw):
        """
        Never raises. The caller treats an empty list as "keep nothing",
        which is why the tests above about successful extraction matter so
        much — this path is indistinguishable from a real empty verdict.
        """
        assert _extract_json_array(raw) == []

    def test_first_array_wins_when_several_are_present(self):
        """Documents the non-greedy regex behaviour rather than assuming it."""
        assert _extract_json_array("text [1, 2] more [3, 4]") == [1, 2]


class TestWorkerIdCoercion:
    """
    Mirrors the filter `create_matches_for_job` applies to parsed output:

        [int(x) for x in parsed
         if isinstance(x, (int, str)) and str(x).isdigit()]

    Tested directly because a hallucinated non-numeric id must be dropped,
    not passed to int() where it would raise mid-rerank and lose every match
    for that job.
    """

    @staticmethod
    def _coerce(parsed_ids: list) -> list[int]:
        return [
            int(x)
            for x in parsed_ids
            if isinstance(x, (int, str)) and str(x).isdigit()
        ]

    def test_integer_ids_pass_through(self):
        assert self._coerce([1, 2, 3]) == [1, 2, 3]

    def test_numeric_strings_are_converted(self):
        """Models frequently quote the numbers."""
        assert self._coerce(["4", "5"]) == [4, 5]

    def test_non_numeric_entries_are_dropped(self):
        assert self._coerce([1, "worker_7", None, 2]) == [1, 2]

    def test_dicts_and_lists_are_dropped(self):
        assert self._coerce([{"id": 1}, [2], 3]) == [3]

    def test_negative_and_decimal_strings_are_rejected(self):
        """`str.isdigit()` excludes both — no id is ever negative or fractional."""
        assert self._coerce(["-1", "1.5", "8"]) == [8]

    def test_empty_input_yields_empty_output(self):
        assert self._coerce([]) == []


class TestRerankerConfiguration:
    """Constants the rerank prompt and candidate slice depend on."""

    def test_candidate_cap_is_positive(self):
        """`rich_matches[:MAX_CANDIDATES_FOR_RERANK]` would be empty at 0."""
        assert MAX_CANDIDATES_FOR_RERANK > 0

    def test_rerank_model_is_configured(self):
        assert isinstance(RERANK_MODEL, str)
        assert RERANK_MODEL
