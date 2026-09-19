"""
数据维护服务：结果/快照保留策略与数据库备份。

- result_items 按结果文件保留最近 N 条（默认 5000）
- price_snapshots 保留最近 N 天（默认 180）
- 每周用 sqlite backup API 全量备份数据库到 data/backups/（保留最近 5 份）

通过环境变量自定义：
  RESULT_ITEMS_MAX_PER_FILE / PRICE_SNAPSHOT_RETENTION_DAYS / DB_BACKUP_KEEP
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from src.infrastructure.persistence.sqlite_connection import (
    get_database_path,
    sqlite_connection,
)

DEFAULT_RESULT_ITEMS_MAX_PER_FILE = 5000
DEFAULT_PRICE_SNAPSHOT_RETENTION_DAYS = 180
DEFAULT_DB_BACKUP_KEEP = 5
MAINTENANCE_INTERVAL_SECONDS = 7 * 24 * 3600

BACKUP_DIR_NAME = "backups"


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def result_items_max_per_file() -> int:
    return _env_int("RESULT_ITEMS_MAX_PER_FILE", DEFAULT_RESULT_ITEMS_MAX_PER_FILE)


def price_snapshot_retention_days() -> int:
    return _env_int("PRICE_SNAPSHOT_RETENTION_DAYS", DEFAULT_PRICE_SNAPSHOT_RETENTION_DAYS)


def db_backup_keep() -> int:
    return _env_int("DB_BACKUP_KEEP", DEFAULT_DB_BACKUP_KEEP)


def prune_result_items(max_per_file: int | None = None) -> int:
    """每个结果文件仅保留最近 max_per_file 条（按爬取时间倒序），返回删除行数。"""
    limit = max_per_file if max_per_file is not None else result_items_max_per_file()
    if limit <= 0:
        return 0
    with sqlite_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM result_items
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY result_filename
                               ORDER BY crawl_time DESC, id DESC
                           ) AS rn
                    FROM result_items
                )
                WHERE rn > ?
            )
            """,
            (limit,),
        )
        deleted = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        conn.commit()
        return deleted


def prune_price_snapshots(retention_days: int | None = None) -> int:
    """删除早于保留期的价格快照，返回删除行数。"""
    days = retention_days if retention_days is not None else price_snapshot_retention_days()
    if days <= 0:
        return 0
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with sqlite_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM price_snapshots WHERE snapshot_time < ?",
            (cutoff,),
        )
        deleted = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        conn.commit()
        return deleted


def backup_database(keep: int | None = None) -> Path | None:
    """用 sqlite backup API 在线备份数据库，轮转保留最近 keep 份。"""
    source_path = Path(get_database_path())
    if not source_path.exists():
        return None

    backup_dir = source_path.parent / BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"{source_path.stem}-{timestamp}.sqlite3"

    source = sqlite3.connect(source_path)
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    _rotate_backups(backup_dir, source_path.stem, keep if keep is not None else db_backup_keep())
    return backup_path


def _rotate_backups(backup_dir: Path, stem: str, keep: int) -> None:
    if keep <= 0:
        return
    backups = sorted(
        path for path in backup_dir.glob(f"{stem}-*.sqlite3")
    )
    for stale in backups[:-keep] if len(backups) > keep else []:
        try:
            stale.unlink()
        except OSError:
            pass


def run_maintenance_once() -> dict:
    """执行一次完整维护（清理 + 备份），返回摘要。"""
    deleted_items = prune_result_items()
    deleted_snapshots = prune_price_snapshots()
    backup_path = backup_database()
    summary = {
        "deleted_result_items": deleted_items,
        "deleted_price_snapshots": deleted_snapshots,
        "backup_path": str(backup_path) if backup_path else None,
    }
    print(
        "[Maintenance] 数据维护完成："
        f"清理结果 {deleted_items} 条 / 快照 {deleted_snapshots} 条，"
        f"备份: {summary['backup_path'] or '跳过'}"
    )
    return summary
