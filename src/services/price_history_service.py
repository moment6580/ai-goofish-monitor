"""
价格历史记录与聚合服务
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Any, Iterable, Optional

from src.infrastructure.persistence.sqlite_bootstrap import bootstrap_sqlite_storage
from src.infrastructure.persistence.sqlite_connection import sqlite_connection

PRICE_HISTORY_DIR = "price_history"
DEFAULT_HISTORY_WINDOW_DAYS = 30


def normalize_keyword_slug(keyword: str) -> str:
    text = "".join(
        char for char in str(keyword or "").lower().replace(" ", "_")
        if char.isalnum() or char in "_-"
    ).rstrip("_")
    return text or "unknown"


def build_price_history_path(keyword: str) -> str:
    return os.path.join(
        PRICE_HISTORY_DIR,
        f"{normalize_keyword_slug(keyword)}_history.jsonl",
    )


def parse_price_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)

    text = str(value).strip().replace("¥", "").replace(",", "")
    if not text or text in {"价格异常", "暂无", "-", "N/A"}:
        return None
    if text.endswith("万"):
        text = str(float(text[:-1]) * 10000)
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        return None


def _safe_iso_datetime(value: Optional[str]) -> str:
    if value:
        return value
    return datetime.now().isoformat()


def _to_day(iso_text: str) -> str:
    return iso_text[:10]


def _build_snapshot_record(
    *,
    keyword: str,
    task_name: str,
    item: dict,
    run_id: str,
    snapshot_time: str,
) -> Optional[dict]:
    item_id = str(item.get("商品ID") or "").strip()
    link = str(item.get("商品链接") or "").strip()
    unique_id = item_id or link
    price_value = parse_price_value(item.get("当前售价"))
    if not unique_id or price_value is None:
        return None

    return {
        "snapshot_time": snapshot_time,
        "snapshot_day": _to_day(snapshot_time),
        "run_id": run_id,
        "task_name": task_name,
        "keyword": keyword,
        "item_id": unique_id,
        "title": item.get("商品标题") or "",
        "price": price_value,
        "price_display": item.get("当前售价") or "",
        "tags": item.get("商品标签") or [],
        "region": item.get("发货地区") or "",
        "seller": item.get("卖家昵称") or "",
        "publish_time": item.get("发布时间") or "",
        "link": link,
    }


def record_market_snapshots(
    *,
    keyword: str,
    task_name: str,
    items: Iterable[dict],
    run_id: str,
    snapshot_time: Optional[str] = None,
    seen_item_ids: Optional[set[str]] = None,
) -> list[dict]:
    snapshot_time = _safe_iso_datetime(snapshot_time)
    seen = seen_item_ids if seen_item_ids is not None else set()
    records: list[dict] = []

    for item in items:
        record = _build_snapshot_record(
            keyword=keyword,
            task_name=task_name,
            item=item,
            run_id=run_id,
            snapshot_time=snapshot_time,
        )
        if record is None or record["item_id"] in seen:
            continue
        seen.add(record["item_id"])
        records.append(record)

    if not records:
        return []

    bootstrap_sqlite_storage()
    keyword_slug = normalize_keyword_slug(keyword)
    with sqlite_connection() as conn:
        for record in records:
            conn.execute(
                """
                INSERT OR IGNORE INTO price_snapshots (
                    keyword_slug, keyword, task_name, snapshot_time, snapshot_day,
                    run_id, item_id, title, price, price_display, tags_json, region,
                    seller, publish_time, link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    keyword_slug,
                    record.get("keyword", keyword),
                    record.get("task_name", task_name),
                    record.get("snapshot_time", snapshot_time),
                    record.get("snapshot_day", _to_day(snapshot_time)),
                    record.get("run_id", run_id),
                    record.get("item_id", ""),
                    record.get("title", ""),
                    record.get("price"),
                    record.get("price_display", ""),
                    json.dumps(record.get("tags") or [], ensure_ascii=False),
                    record.get("region", ""),
                    record.get("seller", ""),
                    record.get("publish_time", ""),
                    record.get("link", ""),
                ),
            )
        conn.commit()
    return records


def _rows_to_snapshots(rows) -> list[dict]:
    snapshots: list[dict] = []
    for row in rows:
        snapshots.append(
            {
                "snapshot_time": row["snapshot_time"],
                "snapshot_day": row["snapshot_day"],
                "run_id": row["run_id"],
                "task_name": row["task_name"],
                "keyword": row["keyword"],
                "item_id": row["item_id"],
                "title": row["title"],
                "price": row["price"],
                "price_display": row["price_display"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "region": row["region"],
                "seller": row["seller"],
                "publish_time": row["publish_time"],
                "link": row["link"],
            }
        )
    return snapshots


def load_price_snapshots(keyword: str) -> list[dict]:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM price_snapshots
            WHERE keyword_slug = ?
            ORDER BY snapshot_time ASC, id ASC
            """,
            (normalize_keyword_slug(keyword),),
        ).fetchall()
    return _rows_to_snapshots(rows)


def load_price_snapshots_for_items(
    keyword: str, item_ids: Iterable[str]
) -> dict[str, list[dict]]:
    """仅取指定商品的快照，按 item_id 分组（走 (keyword_slug, item_id) 索引）。

    避免为了给一页商品算价格参考而加载该关键词的全部历史快照。
    """
    ids = [str(item_id) for item_id in item_ids if str(item_id or "").strip()]
    if not ids:
        return {}

    grouped: dict[str, list[dict]] = {}
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        # 分块 IN 查询，避免 SQLite 变量数量上限
        chunk_size = 500
        for start in range(0, len(ids), chunk_size):
            chunk = ids[start:start + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(
                f"""
                SELECT *
                FROM price_snapshots
                WHERE keyword_slug = ? AND item_id IN ({placeholders})
                ORDER BY snapshot_time ASC, id ASC
                """,
                (normalize_keyword_slug(keyword), *chunk),
            ).fetchall()
            for snapshot in _rows_to_snapshots(rows):
                grouped.setdefault(str(snapshot.get("item_id") or ""), []).append(snapshot)
    return grouped


def load_latest_market_snapshots(
    keyword: str, item_ids: Iterable[str] | None = None
) -> list[dict]:
    """仅取"最新一次运行(run)"的快照，用于市场均价/中位数。

    传入 item_ids 时，在**这些商品的范围内**寻找最新 run（与旧行为一致），
    避免最新 run 恰好不含可见商品时市场摘要变空。
    """
    bootstrap_sqlite_storage()
    slug = normalize_keyword_slug(keyword)
    ids = [str(item_id) for item_id in (item_ids or []) if str(item_id or "").strip()]
    if item_ids is not None and not ids:
        return []

    def _chunks(values: list[str], size: int = 500):
        for start in range(0, len(values), size):
            yield values[start:start + size]

    with sqlite_connection() as conn:
        latest_time: str | None = None
        run_id: str | None = None

        if ids:
            for chunk in _chunks(ids):
                placeholders = ",".join("?" for _ in chunk)
                row = conn.execute(
                    f"""
                    SELECT run_id, snapshot_time
                    FROM price_snapshots
                    WHERE keyword_slug = ? AND item_id IN ({placeholders})
                    ORDER BY snapshot_time DESC, id DESC
                    LIMIT 1
                    """,
                    (slug, *chunk),
                ).fetchone()
                if row is not None and (latest_time is None or row["snapshot_time"] > latest_time):
                    latest_time = row["snapshot_time"]
                    run_id = row["run_id"]
        else:
            row = conn.execute(
                """
                SELECT run_id, snapshot_time
                FROM price_snapshots
                WHERE keyword_slug = ?
                ORDER BY snapshot_time DESC, id DESC
                LIMIT 1
                """,
                (slug,),
            ).fetchone()
            if row is not None:
                run_id = row["run_id"]

        if run_id is None:
            return []

        if not ids:
            rows = conn.execute(
                """
                SELECT * FROM price_snapshots
                WHERE keyword_slug = ? AND run_id = ?
                ORDER BY snapshot_time ASC, id ASC
                """,
                (slug, run_id),
            ).fetchall()
            return _rows_to_snapshots(rows)

        snapshots: list[dict] = []
        for chunk in _chunks(ids):
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(
                f"""
                SELECT * FROM price_snapshots
                WHERE keyword_slug = ? AND run_id = ? AND item_id IN ({placeholders})
                ORDER BY snapshot_time ASC, id ASC
                """,
                (slug, run_id, *chunk),
            ).fetchall()
            snapshots.extend(_rows_to_snapshots(rows))
    return snapshots


def build_latest_market_summary(
    keyword: str, item_ids: Iterable[str] | None = None
) -> dict:
    """当前市场均价/中位数摘要（基于最新 run 的可见商品）。"""
    latest = load_latest_market_snapshots(keyword, item_ids)
    return _summarize_prices(_dedupe_latest(latest, "item_id"))


def load_price_snapshots_since(
    keyword: str,
    cutoff_iso: str,
    item_ids: Iterable[str] | None = None,
) -> list[dict]:
    """加载 snapshot_time >= cutoff 的快照（可按商品过滤），用于窗口内趋势/历史概览。"""
    bootstrap_sqlite_storage()
    slug = normalize_keyword_slug(keyword)
    ids = [str(item_id) for item_id in (item_ids or []) if str(item_id or "").strip()]
    if item_ids is not None and not ids:
        return []

    snapshots: list[dict] = []
    with sqlite_connection() as conn:
        if not ids:
            rows = conn.execute(
                """
                SELECT * FROM price_snapshots
                WHERE keyword_slug = ? AND snapshot_time >= ?
                ORDER BY snapshot_time ASC, id ASC
                """,
                (slug, cutoff_iso),
            ).fetchall()
            return _rows_to_snapshots(rows)

        for start in range(0, len(ids), 500):
            chunk = ids[start:start + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = conn.execute(
                f"""
                SELECT * FROM price_snapshots
                WHERE keyword_slug = ? AND snapshot_time >= ? AND item_id IN ({placeholders})
                ORDER BY snapshot_time ASC, id ASC
                """,
                (slug, cutoff_iso, *chunk),
            ).fetchall()
            snapshots.extend(_rows_to_snapshots(rows))
    return snapshots


def delete_price_snapshots(keyword: str) -> int:
    bootstrap_sqlite_storage()
    with sqlite_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM price_snapshots WHERE keyword_slug = ?",
            (normalize_keyword_slug(keyword),),
        )
        conn.commit()
    return int(cursor.rowcount or 0)


def _dedupe_latest(records: Iterable[dict], group_key: str) -> list[dict]:
    latest_by_key: dict[str, dict] = {}
    for record in records:
        key = str(record.get(group_key) or "").strip()
        if not key:
            continue
        latest_by_key[key] = record
    return list(latest_by_key.values())


def _summarize_prices(records: Iterable[dict]) -> dict:
    entries = [record for record in records if parse_price_value(record.get("price")) is not None]
    prices = [float(record["price"]) for record in entries]
    if not prices:
        return {
            "sample_count": 0,
            "avg_price": None,
            "median_price": None,
            "min_price": None,
            "max_price": None,
        }

    return {
        "sample_count": len(prices),
        "avg_price": round(sum(prices) / len(prices), 2),
        "median_price": round(float(median(prices)), 2),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
    }


def _build_daily_trend(snapshots: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[str(snapshot.get("snapshot_day") or "")].append(snapshot)

    points: list[dict] = []
    for day in sorted(grouped.keys()):
        day_records = _dedupe_latest(grouped[day], "item_id")
        summary = _summarize_prices(day_records)
        summary["day"] = day
        points.append(summary)
    return points


def _resolve_deal_label(score: int) -> str:
    if score >= 65:
        return "高性价比"
    if score >= 50:
        return "值得关注"
    if score >= 40:
        return "价格正常"
    return "价格偏高"


def build_item_price_context(
    snapshots: list[dict],
    *,
    item_id: str,
    current_price: Optional[float],
    market_snapshots: Optional[list[dict]] = None,
    item_snapshots: Optional[list[dict]] = None,
    market_summary: Optional[dict] = None,
) -> dict:
    """构建单件商品的价格参考。

    可选传入 `item_snapshots`（该商品快照）与 `market_summary`（当前市场摘要），
    供批量场景预先构建索引后 O(1) 复用，避免逐个商品重复全量扫描。
    """
    if not item_id:
        return {"observation_count": 0, "deal_score": None, "deal_label": "暂无数据"}

    if item_snapshots is None:
        item_snapshots = [record for record in snapshots if str(record.get("item_id")) == str(item_id)]
    if not item_snapshots:
        return {"observation_count": 0, "deal_score": None, "deal_label": "暂无数据"}

    latest_item_snapshot = item_snapshots[-1]
    price_now = current_price if current_price is not None else parse_price_value(latest_item_snapshot.get("price"))
    historical_prices = [float(record["price"]) for record in item_snapshots if parse_price_value(record.get("price")) is not None]

    if market_summary is None:
        source_snapshots = market_snapshots if market_snapshots is not None else snapshots
        latest_run_id = str(source_snapshots[-1].get("run_id") or "") if source_snapshots else ""
        latest_market = _dedupe_latest(
            [record for record in source_snapshots if str(record.get("run_id") or "") == latest_run_id],
            "item_id",
        )
        market_summary = _summarize_prices(latest_market)
    market_avg = market_summary.get("avg_price")
    market_median = market_summary.get("median_price")

    score = 50
    if price_now is not None and market_avg:
        score += int(((market_avg - price_now) / market_avg) * 60)
    if price_now is not None and historical_prices:
        historical_max = max(historical_prices)
        if historical_max > 0:
            score += int(((historical_max - price_now) / historical_max) * 20)
        if math.isclose(price_now, min(historical_prices), rel_tol=0.001):
            score += 8
    score = max(0, min(100, score))

    previous_price = historical_prices[-2] if len(historical_prices) >= 2 else None
    change_amount = None if previous_price is None or price_now is None else round(price_now - previous_price, 2)
    change_percent = None
    if change_amount is not None and previous_price:
        change_percent = round(change_amount / previous_price * 100, 2)

    return {
        "observation_count": len(historical_prices),
        "current_price": price_now,
        "avg_price": round(sum(historical_prices) / len(historical_prices), 2),
        "median_price": round(float(median(historical_prices)), 2),
        "min_price": round(min(historical_prices), 2),
        "max_price": round(max(historical_prices), 2),
        "first_seen_at": item_snapshots[0].get("snapshot_time"),
        "last_seen_at": latest_item_snapshot.get("snapshot_time"),
        "market_avg_price": market_avg,
        "market_median_price": market_median,
        "price_change_amount": change_amount,
        "price_change_percent": change_percent,
        "deal_score": score,
        "deal_label": _resolve_deal_label(score),
    }


def build_market_reference(
    *,
    keyword: str,
    item: dict,
    current_market_items: list[dict],
    historical_snapshots: list[dict],
) -> dict:
    current_market_records = []
    for market_item in current_market_items:
        price = parse_price_value(market_item.get("当前售价"))
        if price is None:
            continue
        current_market_records.append({"price": price})

    market_snapshot = _summarize_prices(current_market_records)
    history_summary = _summarize_prices(_dedupe_latest(historical_snapshots, "item_id"))
    item_context = build_item_price_context(
        historical_snapshots,
        item_id=str(item.get("商品ID") or ""),
        current_price=parse_price_value(item.get("当前售价")),
    )
    return {
        "当前搜索样本": market_snapshot,
        "历史价格概览": history_summary,
        "本商品价格位置": item_context,
        "关键词": keyword,
    }


def _empty_insights() -> dict:
    return {
        "market_summary": _summarize_prices([]),
        "history_summary": {"unique_items": 0, **_summarize_prices([])},
        "daily_trend": [],
        "latest_snapshot_at": None,
    }


def build_price_history_insights(
    keyword: str,
    *,
    window_days: int = DEFAULT_HISTORY_WINDOW_DAYS,
    visible_item_ids: Optional[set[str]] = None,
) -> dict:
    """行情洞察（SQL 有界读取）。

    只加载：①最新一次运行的快照（算市场均价）②窗口内的快照（算历史概览与日趋势），
    不再把该关键词的全部历史快照读进内存后做 Python 聚合。
    """
    filter_ids = None
    if visible_item_ids is not None:
        filter_ids = [str(item_id) for item_id in visible_item_ids if str(item_id or "").strip()]
        if not filter_ids:
            return _empty_insights()

    latest_market = load_latest_market_snapshots(keyword, filter_ids)
    if not latest_market:
        return _empty_insights()

    latest_snapshot_at = max(
        str(snapshot.get("snapshot_time") or "") for snapshot in latest_market
    )
    market_summary = {
        **_summarize_prices(_dedupe_latest(latest_market, "item_id")),
        "snapshot_time": latest_snapshot_at,
    }

    try:
        cutoff = (
            datetime.fromisoformat(latest_snapshot_at)
            - timedelta(days=max(0, window_days))
        ).isoformat()
    except ValueError:
        cutoff = latest_snapshot_at

    recent_snapshots = load_price_snapshots_since(keyword, cutoff, filter_ids)
    latest_records_by_item = _dedupe_latest(recent_snapshots, "item_id")

    return {
        "market_summary": market_summary,
        "history_summary": {
            "unique_items": len(latest_records_by_item),
            **_summarize_prices(latest_records_by_item),
        },
        "daily_trend": _build_daily_trend(recent_snapshots),
        "latest_snapshot_at": latest_snapshot_at,
    }
