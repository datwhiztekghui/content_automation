from content_factory.gates.approval import _pick_topic_from_hint


def test_pick_topic_from_hint_fabricates():
    topic = _pick_topic_from_hint([], "Solid state batteries")
    assert topic is not None
    assert "Solid state" in topic["title"]


def test_pick_topic_matches_candidate():
    candidates = [
        {"title": "Alpha Robot Launch", "summary": "x", "why_it_matters": "y"},
        {"title": "Other", "summary": "x", "why_it_matters": "y"},
    ]
    topic = _pick_topic_from_hint(candidates, "alpha robot")
    assert topic["title"] == "Alpha Robot Launch"
