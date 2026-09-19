import json

import pytest

from src.services import spawn_registry


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATABASE_FILE", str(tmp_path / "app.sqlite3"))
    yield


def test_record_and_load_entries():
    spawn_registry.record_spawn(1, 1234, "Sony A7M4")

    entries = spawn_registry.load_entries()
    assert len(entries) == 1
    assert entries[0]["task_id"] == "1"
    assert entries[0]["pid"] == 1234
    assert entries[0]["task_name"] == "Sony A7M4"


def test_remove_entry():
    spawn_registry.record_spawn(1, 1234, "task-a")
    spawn_registry.record_spawn(2, 2345, "task-b")

    spawn_registry.remove_entry(1)

    entries = spawn_registry.load_entries()
    assert [e["task_id"] for e in entries] == ["2"]


def test_registry_file_created_on_disk():
    spawn_registry.record_spawn(3, 3456, "task-c")

    path = spawn_registry.registry_path()
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["3"]["pid"] == 3456


def test_load_entries_ignores_corrupt_file():
    path = spawn_registry.registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json{", encoding="utf-8")

    assert spawn_registry.load_entries() == []


def test_reap_skips_dead_and_foreign_pids(monkeypatch):
    spawn_registry.record_spawn(1, 111, "dead-task")
    spawn_registry.record_spawn(2, 222, "foreign-task")
    spawn_registry.record_spawn(3, 333, "live-spider")

    monkeypatch.setattr(spawn_registry, "is_spider_process", lambda pid: pid == 333)
    kills = []
    monkeypatch.setattr(
        spawn_registry, "_kill_process_group", lambda pgid: kills.append(pgid)
    )

    def fake_kill(pid, sig):
        if pid in (111, 222):
            raise ProcessLookupError

    monkeypatch.setattr(spawn_registry.os, "kill", fake_kill)

    reaped = spawn_registry.reap_orphan_spiders()

    assert reaped == ["live-spider"]
    assert kills == [333]
    # 回收后注册表清空
    assert spawn_registry.load_entries() == []
