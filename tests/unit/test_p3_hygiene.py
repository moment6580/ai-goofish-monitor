import asyncio
import sqlite3
from datetime import datetime, time

import pytest

from src.infrastructure.persistence.sqlite_connection import init_schema
from src.services import result_storage_service as storage
from src.services import notification_service
from src.services.notification_service import NotificationService, _is_quiet_now
from src.infrastructure.external.notification_clients.base import NotificationClient


class _OkClient(NotificationClient):
    channel_key = "ok"
    display_name = "OK"

    async def send(self, product_data, reason):
        return None


# ---------- B1: 删除结果文件时清理孤儿快照 ----------

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    with sqlite3.connect(db_file) as conn:
        init_schema(conn)
    yield db_file


def _record(item_id: str, keyword: str, crawl_time: str) -> dict:
    return {
        "爬取时间": crawl_time,
        "搜索关键字": keyword,
        "任务名称": "task",
        "商品信息": {
            "商品ID": item_id,
            "商品标题": f"item {item_id}",
            "商品链接": f"https://x/{item_id}",
            "当前售价": "¥100",
        },
        "ai_analysis": {"is_recommended": False, "analysis_source": "ai"},
    }


def test_any_result_file_uses_keyword(isolated_db):
    storage._save_result_record_sync(_record("1", "sony a7m4", "2026-01-01T10:00:00"), "sony a7m4")
    storage._save_result_record_sync(_record("2", "canon r6", "2026-01-01T10:00:00"), "canon r6")

    # 排除自身后，sony 关键词没有别的结果文件
    assert asyncio.run(
        storage.any_result_file_uses_keyword("sony a7m4", exclude_filename="sony_a7m4_full_data.jsonl")
    ) is False
    # 不排除时存在
    assert asyncio.run(
        storage.any_result_file_uses_keyword("sony a7m4", exclude_filename="other_full_data.jsonl")
    ) is True


def test_delete_result_file_cleans_snapshots(isolated_db):
    from src.api.routes import results as results_route
    from src.services.price_history_service import load_price_snapshots, record_market_snapshots

    storage._save_result_record_sync(_record("1", "sony a7m4", "2026-01-01T10:00:00"), "sony a7m4")
    record_market_snapshots(
        keyword="sony a7m4", task_name="task",
        items=[{"商品ID": "1", "商品标题": "t", "当前售价": "¥100", "商品链接": "https://x/1"}],
        run_id="r1", snapshot_time="2026-01-01T10:00:00", seen_item_ids=set(),
    )
    assert load_price_snapshots("sony a7m4")

    response = asyncio.run(results_route.delete_result_file("sony_a7m4_full_data.jsonl"))
    assert "已成功删除" in response["message"]
    assert load_price_snapshots("sony a7m4") == []


# ---------- A7: 任务生成作业内存回收 ----------

def test_task_generation_prunes_finished_jobs():
    from src.services.task_generation_service import MAX_RETAINED_JOBS, TaskGenerationService

    service = TaskGenerationService()

    async def run():
        for _ in range(MAX_RETAINED_JOBS + 20):
            job = await service.create_job("task")
            # 模拟作业结束（直接置为 completed）
            service._jobs[job.job_id].status = "completed"

    asyncio.run(run())
    assert len(service._jobs) <= MAX_RETAINED_JOBS


# ---------- B2: 通知去重 / 静默时段 ----------

def test_notification_dedup_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOTIFICATION_DEDUP_WINDOW_SECONDS", raising=False)
    notification_service.reset_notification_dedup_cache()
    service = NotificationService([_OkClient(enabled=True)])

    first = asyncio.run(service.send_notification({"商品链接": "https://x/1"}, "r"))
    second = asyncio.run(service.send_notification({"商品链接": "https://x/1"}, "r"))

    assert first["ok"]["success"] is True
    assert second["ok"]["success"] is True


def test_notification_dedup_suppresses_repeats(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_DEDUP_WINDOW_SECONDS", "3600")
    notification_service.reset_notification_dedup_cache()
    service = NotificationService([_OkClient(enabled=True)])

    first = asyncio.run(service.send_notification({"商品链接": "https://x/1"}, "r"))
    second = asyncio.run(service.send_notification({"商品链接": "https://x/1"}, "r"))
    other = asyncio.run(service.send_notification({"商品链接": "https://x/2"}, "r"))

    assert first["ok"]["success"] is True
    assert second == {}          # 命中窗口被抑制
    assert other["ok"]["success"] is True  # 不同商品不受影响
    notification_service.reset_notification_dedup_cache()


def test_notification_quiet_hours(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_QUIET_HOURS", "23:00-07:00")

    assert _is_quiet_now(datetime(2026, 1, 1, 23, 30)) is True
    assert _is_quiet_now(datetime(2026, 1, 1, 3, 0)) is True
    assert _is_quiet_now(datetime(2026, 1, 1, 12, 0)) is False

    # 非跨天窗口
    monkeypatch.setenv("NOTIFICATION_QUIET_HOURS", "09:00-17:00")
    assert _is_quiet_now(datetime(2026, 1, 1, 10, 0)) is True
    assert _is_quiet_now(datetime(2026, 1, 1, 18, 0)) is False

    # 非法配置忽略
    monkeypatch.setenv("NOTIFICATION_QUIET_HOURS", "not-a-window")
    assert _is_quiet_now(datetime(2026, 1, 1, 10, 0)) is False


def test_test_notification_bypasses_dedup(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_DEDUP_WINDOW_SECONDS", "3600")
    notification_service.reset_notification_dedup_cache()
    service = NotificationService([_OkClient(enabled=True)])

    first = asyncio.run(service.send_test_notification())
    second = asyncio.run(service.send_test_notification())

    assert first["ok"]["success"] is True
    assert second["ok"]["success"] is True
    notification_service.reset_notification_dedup_cache()
