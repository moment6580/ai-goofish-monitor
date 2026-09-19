import asyncio
import importlib
import json
import sys
import types

import pytest


@pytest.fixture()
def spider_v2(monkeypatch):
    fake_scraper = types.ModuleType("src.scraper")

    async def placeholder_scrape(task_config, debug_limit):
        return 0

    fake_scraper.scrape_xianyu = placeholder_scrape
    monkeypatch.setitem(sys.modules, "src.scraper", fake_scraper)
    sys.modules.pop("spider_v2", None)
    yield importlib.import_module("spider_v2")
    sys.modules.pop("spider_v2", None)


def _write_config(tmp_path, config_data):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config_data, ensure_ascii=False), encoding="utf-8")
    return config_path


def _write_state(tmp_path, monkeypatch, spider_v2):
    state_path = tmp_path / "state.json"
    state_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(spider_v2, "STATE_FILE", str(state_path))


def test_single_task_mode_skips_other_task_prompts(tmp_path, monkeypatch, spider_v2):
    config_data = [
        {
            "task_name": "Sony A7M4",
            "enabled": True,
            "keyword": "sony a7m4",
            "decision_mode": "ai",
            "keyword_rules": [],
            "ai_prompt_file": str(tmp_path / "a7m4_prompt.txt"),
        },
        {
            "task_name": "Canon R6",
            "enabled": True,
            "keyword": "canon r6",
            "decision_mode": "ai",
            "keyword_rules": [],
            "ai_prompt_file": str(tmp_path / "canon_prompt.txt"),
        },
    ]
    (tmp_path / "a7m4_prompt.txt").write_text("A7M4 criteria. " + "x" * 120, encoding="utf-8")
    (tmp_path / "canon_prompt.txt").write_text("Canon criteria. " + "x" * 120, encoding="utf-8")

    config_path = _write_config(tmp_path, config_data)
    _write_state(tmp_path, monkeypatch, spider_v2)

    opened = []
    real_open = open

    def fake_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    called = []

    async def fake_scrape_xianyu(task_config, debug_limit):
        called.append(task_config["task_name"])
        return 0

    monkeypatch.setattr(spider_v2, "scrape_xianyu", fake_scrape_xianyu)
    monkeypatch.setattr(sys, "argv", ["spider_v2.py", "--config", str(config_path), "--task-name", "Sony A7M4"])

    asyncio.run(spider_v2.main())

    assert called == ["Sony A7M4"]
    assert str(tmp_path / "a7m4_prompt.txt") in opened
    assert str(tmp_path / "canon_prompt.txt") not in opened


def test_max_concurrency_limits_parallel_scrapes(tmp_path, monkeypatch, spider_v2):
    monkeypatch.setenv("SPIDER_MAX_CONCURRENT_TASKS", "1")

    config_data = [
        {
            "task_name": f"Task-{index}",
            "enabled": True,
            "keyword": f"kw-{index}",
            "decision_mode": "keyword",
            "keyword_rules": [],
        }
        for index in range(3)
    ]
    config_path = _write_config(tmp_path, config_data)
    _write_state(tmp_path, monkeypatch, spider_v2)

    state = {"active": 0, "max_active": 0}

    async def fake_scrape_xianyu(task_config, debug_limit):
        state["active"] += 1
        state["max_active"] = max(state["max_active"], state["active"])
        await asyncio.sleep(0.01)
        state["active"] -= 1
        return 0

    monkeypatch.setattr(spider_v2, "scrape_xianyu", fake_scrape_xianyu)
    monkeypatch.setattr(sys, "argv", ["spider_v2.py", "--config", str(config_path)])

    asyncio.run(spider_v2.main())

    assert state["max_active"] == 1


def test_as_int_env(monkeypatch, spider_v2):
    monkeypatch.setenv("SPIDER_MAX_CONCURRENT_TASKS", "3")
    assert spider_v2._as_int_env("SPIDER_MAX_CONCURRENT_TASKS", 2) == 3

    monkeypatch.setenv("SPIDER_MAX_CONCURRENT_TASKS", "0")
    assert spider_v2._as_int_env("SPIDER_MAX_CONCURRENT_TASKS", 2) == 2

    monkeypatch.setenv("SPIDER_MAX_CONCURRENT_TASKS", "abc")
    assert spider_v2._as_int_env("SPIDER_MAX_CONCURRENT_TASKS", 2) == 2

    monkeypatch.delenv("SPIDER_MAX_CONCURRENT_TASKS")
    assert spider_v2._as_int_env("SPIDER_MAX_CONCURRENT_TASKS", 2) == 2
