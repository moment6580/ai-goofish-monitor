import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.infrastructure.persistence.sqlite_connection import init_schema
from src.services import data_maintenance


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    with sqlite3.connect(db_file) as conn:
        init_schema(conn)
    yield db_file


def _insert_result_items(conn, filename: str, count: int) -> None:
    for i in range(count):
        conn.execute(
            """
            INSERT INTO result_items (
                result_filename, keyword, task_name, crawl_time, publish_time,
                price, price_display, item_id, title, link, link_unique_key,
                seller_nickname, is_recommended, analysis_source, keyword_hit_count,
                status, raw_json
            ) VALUES (?, ?, ?, ?, NULL, 100, '¥100', ?, ?, ?, ?, NULL, 0, 'ai', 0, 'active', '{}')
            """,
            (
                filename,
                "kw",
                "task",
                f"2026-01-{(i % 28) + 1:02d}T{i % 24:02d}:00:00",
                f"item-{i}",
                f"title-{i}",
                f"https://example.com/{i}",
                f"https://example.com/{i}",
            ),
        )
    conn.commit()


def test_prune_result_items_keeps_newest_per_file(isolated_db):
    with sqlite3.connect(isolated_db) as conn:
        _insert_result_items(conn, "a_full_data.jsonl", 10)
        _insert_result_items(conn, "b_full_data.jsonl", 5)

    deleted = data_maintenance.prune_result_items(max_per_file=6)

    assert deleted == 4  # a 文件删 4 条，b 文件 5 条不动
    with sqlite3.connect(isolated_db) as conn:
        counts = dict(
            conn.execute(
                "SELECT result_filename, COUNT(*) FROM result_items GROUP BY result_filename"
            ).fetchall()
        )
    assert counts == {"a_full_data.jsonl": 6, "b_full_data.jsonl": 5}


def test_prune_price_snapshots_by_age(isolated_db):
    now = datetime.now()
    with sqlite3.connect(isolated_db) as conn:
        for offset_days in (1, 100, 400):
            ts = (now - timedelta(days=offset_days)).isoformat(timespec="seconds")
            day = ts[:10]
            conn.execute(
                """
                INSERT INTO price_snapshots (
                    keyword_slug, keyword, task_name, snapshot_time, snapshot_day,
                    run_id, item_id, title, price, price_display, tags_json
                ) VALUES ('kw', 'kw', 'task', ?, ?, ?, ?, 't', 1.0, '¥1', '[]')
                """,
                (ts, day, f"run-{offset_days}", f"item-{offset_days}"),
            )
        conn.commit()

    deleted = data_maintenance.prune_price_snapshots(retention_days=180)

    assert deleted == 1
    with sqlite3.connect(isolated_db) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert remaining == 2


def test_backup_database_creates_and_rotates(isolated_db):
    # 先写入数据再备份，验证备份内容完整
    with sqlite3.connect(isolated_db) as conn:
        _insert_result_items(conn, "a_full_data.jsonl", 3)

    paths = []
    for _ in range(7):
        path = data_maintenance.backup_database(keep=3)
        assert path is not None and path.exists()
        paths.append(path)

    backup_dir = Path(isolated_db).parent / "backups"
    remaining = sorted(backup_dir.glob("app-*.sqlite3"))
    assert len(remaining) == 3

    # 备份内容可读且包含数据
    with sqlite3.connect(remaining[-1]) as conn:
        count = conn.execute("SELECT COUNT(*) FROM result_items").fetchone()[0]
    assert count == 3


def test_run_maintenance_once_summary(isolated_db):
    summary = data_maintenance.run_maintenance_once()
    assert summary["deleted_result_items"] == 0
    assert summary["deleted_price_snapshots"] == 0
    assert summary["backup_path"] is not None
