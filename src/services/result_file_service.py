"""
结果记录富化与文件名校验服务
"""

import asyncio

from src.infrastructure.persistence.storage_names import normalize_keyword_from_filename
from src.services.price_history_service import (
    build_item_price_context,
    build_latest_market_summary,
    load_price_snapshots_for_items,
    parse_price_value,
)
from src.services.result_storage_service import load_visible_result_item_ids


def validate_result_filename(filename: str) -> None:
    if not filename.endswith(".jsonl") or "/" in filename or ".." in filename:
        raise ValueError("无效的文件名")


def _extract_item_ids(records: list[dict]) -> list[str]:
    item_ids: list[str] = []
    for record in records:
        info = record.get("商品信息", {}) or {}
        item_id = str(info.get("商品ID") or "").strip()
        if item_id:
            item_ids.append(item_id)
    return item_ids


def enrich_records_with_price_insight(records: list[dict], filename: str) -> list[dict]:
    """为记录补充价格参考。

    只按需加载“当前这页商品”的快照（走 item_id 索引），市场摘要也只取最新
    一次运行的数据，避免逐条记录重新扫描全量历史快照。
    """
    if not records:
        return records

    keyword = normalize_keyword_from_filename(filename)
    item_ids = _extract_item_ids(records)
    if not item_ids:
        return records

    snapshots_by_item = load_price_snapshots_for_items(keyword, item_ids)
    if not snapshots_by_item:
        return records

    visible_item_ids = load_visible_result_item_ids(filename)
    market_summary = build_latest_market_summary(keyword, visible_item_ids)

    enriched: list[dict] = []
    for record in records:
        info = record.get("商品信息", {}) or {}
        item_id = str(info.get("商品ID") or "").strip()
        clone = dict(record)
        clone["price_insight"] = build_item_price_context(
            [],
            item_id=item_id,
            current_price=parse_price_value(info.get("当前售价")),
            item_snapshots=snapshots_by_item.get(item_id, []),
            market_summary=market_summary,
        )
        enriched.append(clone)
    return enriched


async def enrich_records_with_price_insight_async(
    records: list[dict], filename: str
) -> list[dict]:
    """异步包装：把 SQLite 读取移出事件循环，避免阻塞 WebSocket/其他请求。"""
    return await asyncio.to_thread(enrich_records_with_price_insight, records, filename)