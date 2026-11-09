import datetime as dt

import storage


def test_bulk_files_keep_case_and_sort(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "BULKS_DIR", tmp_path)
    (tmp_path / "ZukaBugar.txt").write_text("1 Sol Ring")
    (tmp_path / "alice.txt").write_text("1 Sol Ring")
    (tmp_path / "Bob.txt").write_text("1 Sol Ring")
    assert list(storage.bulk_files()) == ["alice", "Bob", "ZukaBugar"]


def test_save_bulk_replaces_regardless_of_case(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "BULKS_DIR", tmp_path)
    assert storage.save_bulk("Alice", "1 Sol Ring") == ("Alice", False)
    assert storage.save_bulk("alice", "2 Sol Ring") == ("alice", True)
    assert [p.name for p in tmp_path.iterdir()] == ["alice.txt"]
    assert storage.save_bulk("Đuro / Šimić?", "1 Sol Ring")[0] == "Đuro Šimić"


def test_owner_label_and_filenames():
    assert storage.owner_label("alice") == "Alice"
    assert storage.owner_label("ZukaBugar") == "ZukaBugar"
    assert storage.owner_label("ivan_k") == "Ivan k"
    assert storage.slugify("Đuro Šimić") == "duro-simic"
    assert storage.result_filename("Goblin tokens", dt.date(2026, 11, 9)) == "goblin-tokens_2026-11-09.txt"


def test_results_listing_and_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RESULTS_DIR", tmp_path / "results")
    assert storage.result_files() == []
    old = storage.save_result("old", "Deck A", dt.date(2026, 1, 1))
    new = storage.save_result("new", "Deck B", dt.date(2026, 1, 2))
    import os
    os.utime(old, (1, 1))
    assert [p.name for p in storage.result_files()] == [new.name, old.name]
    storage.delete_result("../../" + old.name)  # path parts are ignored
    assert [p.name for p in storage.result_files()] == [new.name]
