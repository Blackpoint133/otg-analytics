from pathlib import Path
import importlib.util

SPEC = importlib.util.spec_from_file_location("refresh_common_data", Path(__file__).parents[1] / "scripts" / "refresh_common_data.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sync_requires_distinct_existing_paths(tmp_path):
    source = tmp_path / "source"; target = tmp_path / "target"
    source.mkdir(); target.mkdir()
    try:
        MODULE.run(source, source)
    except ValueError:
        pass
    else:
        raise AssertionError("same source and target must be rejected")
    try:
        MODULE.run(source / "missing", target)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing source must be rejected")


def test_sales_files_are_published_without_touching_unrelated_files(tmp_path, monkeypatch):
    source = tmp_path / "source"; target = tmp_path / "target"
    (source / "sales_enriched").mkdir(parents=True); (target / "sales_enriched").mkdir(parents=True)
    (source / "sales_enriched" / "item.csv").write_text("new", encoding="utf-8")
    unrelated = target / "keep.txt"; unrelated.write_text("keep", encoding="utf-8")
    assert MODULE.sync_sales(source, target) == 1
    assert (target / "sales_enriched" / "item.csv").read_text(encoding="utf-8") == "new"
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_no_production_default_and_atomic_publisher(tmp_path):
    source = tmp_path / "source.txt"; target = tmp_path / "target.txt"
    source.write_text("fresh", encoding="utf-8")
    assert MODULE.publish_file(source, target)
    assert target.read_text(encoding="utf-8") == "fresh"
