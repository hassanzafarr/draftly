"""Pure unit tests for generator output normalization — no DB, no network."""

from apps.proposals.generator import (
    SECTION_SCHEMA,
    _normalize_sections,
    _parse_sections,
    length_preset,
    resolve_section_schema,
)


def test_parse_sections_handles_json_wrapped_in_prose():
    raw = 'Here is your proposal:\n{"executive_summary": "Summary text"}\nDone!'
    sections = _parse_sections(raw, "Gemini")
    assert sections["executive_summary"] == "Summary text"
    assert set(sections) == set(SECTION_SCHEMA)


def test_normalize_flattens_nested_structures():
    sections = _normalize_sections(
        {
            "executive_summary": ["Para one.", "Para two."],
            "pricing": {"phase_1": "10k", "phase_2": "20k"},
        }
    )
    assert sections["executive_summary"] == "Para one.\n\nPara two."
    assert "10k" in sections["pricing"]
    assert "20k" in sections["pricing"]


def test_normalize_routes_invented_keys_to_appendix():
    sections = _normalize_sections({"surprise_section": "Bonus content"})
    assert "Bonus content" in sections["appendix"]
    assert "surprise_section" not in sections


def test_resolve_section_schema_dedupes_and_slugifies():
    schema = resolve_section_schema(["Executive Summary", "Pricing", "Pricing", "  "])
    keys = [k for k, _ in schema]
    assert keys == ["executive_summary", "pricing", "pricing_2"]


def test_resolve_section_schema_empty_falls_back_to_default():
    assert len(resolve_section_schema(None)) == 10
    assert len(resolve_section_schema([])) == 10


def test_length_preset_unknown_falls_back_to_standard():
    assert length_preset("novel")["label"] == "standard"
    assert length_preset(None)["label"] == "standard"
    assert length_preset("CONCISE")["label"] == "concise"
