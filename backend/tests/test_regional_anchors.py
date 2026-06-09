"""Tests for the regional-anchor reference points shipped in BiasReport.

These anchors let the frontend re-anchor the political-compass view to a
specific region's median citizen, so the same source can read as
"centre-right" through a US lens but "right" through an EU lens without
re-running any analysis. The contract here is that anchors are present,
include a "global" baseline, and stay inside the valid axis range.
"""
from __future__ import annotations

from app.agents.comparator import _REGIONAL_ANCHORS, _computed_report
from app.models.bias_report import RegionalAnchor


def test_regional_anchors_are_loaded_with_required_fields():
    assert len(_REGIONAL_ANCHORS) >= 5, "Expected at least a handful of regional perspectives"
    for anchor in _REGIONAL_ANCHORS:
        assert isinstance(anchor, RegionalAnchor)
        assert anchor.id
        assert anchor.short_name
        assert -1.0 <= anchor.economic_axis <= 1.0
        assert -1.0 <= anchor.social_axis <= 1.0


def test_regional_anchors_include_a_global_baseline_at_origin():
    by_id = {a.id: a for a in _REGIONAL_ANCHORS}
    assert "global" in by_id, "A 'global' baseline anchor is required"
    global_anchor = by_id["global"]
    assert global_anchor.economic_axis == 0.0
    assert global_anchor.social_axis == 0.0


def test_regional_anchors_are_unique_by_id():
    ids = [a.id for a in _REGIONAL_ANCHORS]
    assert len(ids) == len(set(ids)), "Anchor ids must be unique"


def test_bias_report_carries_regional_anchors():
    report = _computed_report(analyses=[], topic="anchors test", articles=[], source_profiles=[])
    assert report.regional_anchors, "BiasReport should include regional_anchors"
    assert any(a.id == "global" for a in report.regional_anchors)
