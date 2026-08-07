from pathlib import Path

from content_factory.utils.artifacts import ArtifactStore, new_run_id


def test_artifact_store_roundtrip(tmp_path: Path):
    rid = new_run_id()
    store = ArtifactStore(tmp_path, rid)
    store.write_json("hello.json", {"a": 1})
    store.write_text("hello.md", "# hi")
    assert store.read_json("hello.json") == {"a": 1}
    assert store.read_text("hello.md") == "# hi"
    assert "T" in rid
