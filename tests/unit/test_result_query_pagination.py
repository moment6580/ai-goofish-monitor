import asyncio

import pytest

from src.infrastructure.persistence.sqlite_connection import init_schema
from src.services import result_storage_service as storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    import sqlite3

    with sqlite3.connect(db_file) as conn:
        init_schema(conn)
    yield db_file


def _record(item_id: str, *, crawl_time: str, price: int, recommended: bool = False,
            source: str = "ai", title: str = "索尼 A7M4", status: str = "active") -> dict:
    return {
        "爬取时间": crawl_time,
        "搜索关键字": "sony a7m4",
        "任务名称": "Sony A7M4",
        "商品信息": {
            "商品ID": item_id,
            "商品标题": title,
            "商品链接": f"https://www.goofish.com/item?id={item_id}",
            "当前售价": f"¥{price}",
        },
        "ai_analysis": {
            "is_recommended": recommended,
            "analysis_source": source,
            "keyword_hit_count": 1,
            "reason": "test",
        },
        "商品状态": status,
    }


def _seed(count: int) -> None:
    for i in range(count):
        # 交错推荐来源，便于筛选测试
        recommended = i % 3 == 0
        source = "ai" if i % 2 == 0 else "keyword"
        storage._save_result_record_sync(
            _record(
                str(1000 + i),
                crawl_time=f"2026-01-01T{i // 60:02d}:{i % 60:02d}:00",
                price=100 + i,
                recommended=recommended,
                source=source,
            ),
            "sony a7m4",
        )


def test_sql_pagination_slices_and_total():
    _seed(250)

    total, page1 = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl",
        ai_recommended_only=False,
        keyword_recommended_only=False,
        sort_by="crawl_time",
        sort_order="desc",
        page=1,
        limit=100,
        include_hidden=False,
    )
    assert total == 250
    assert len(page1) == 100

    total2, page3 = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl",
        ai_recommended_only=False,
        keyword_recommended_only=False,
        sort_by="crawl_time",
        sort_order="desc",
        page=3,
        limit=100,
        include_hidden=False,
    )
    assert total2 == 250
    assert len(page3) == 50

    # 分页不重叠且并集完整
    ids = {r["商品信息"]["商品ID"] for r in page1}
    ids |= {r["商品信息"]["商品ID"] for r in page3}
    assert len(ids) == 150


def test_pagination_ordering_desc_and_price_asc():
    _seed(30)

    _, by_time = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=5, include_hidden=False,
    )
    times = [r["爬取时间"] for r in by_time]
    assert times == sorted(times, reverse=True)

    _, by_price = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="price",
        sort_order="asc", page=1, limit=5, include_hidden=False,
    )
    prices = [int(r["商品信息"]["当前售价"].lstrip("¥")) for r in by_price]
    assert prices == sorted(prices)


def test_recommended_filters_count_in_sql():
    _seed(30)

    total_ai, items_ai = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=True,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=False,
    )
    assert all((r.get("ai_analysis") or {}).get("analysis_source") == "ai" for r in items_ai)
    assert all((r.get("ai_analysis") or {}).get("is_recommended") for r in items_ai)
    assert total_ai == len(items_ai)

    total_kw, items_kw = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=True, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=False,
    )
    assert all((r.get("ai_analysis") or {}).get("analysis_source") == "keyword" for r in items_kw)
    assert total_kw == len(items_kw)


def test_rule_hidden_excluded_from_total_and_pages():
    _seed(10)
    # 加一条会被规则命中的
    storage._save_result_record_sync(
        _record("9999", crawl_time="2026-01-01T23:59:00", price=50, title="翻新机 勿拍"),
        "sony a7m4",
    )

    total_before, _ = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=False,
    )
    assert total_before == 11

    storage._save_result_blacklist_keywords_sync("sony_a7m4_full_data.jsonl", ["翻新"])

    total_after, items = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=False,
    )
    assert total_after == 10
    assert all(r["商品信息"]["商品ID"] != "9999" for r in items)

    # include_hidden 时应能看到被规则隐藏的条目
    total_hidden, items_hidden = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=True,
    )
    assert total_hidden == 11
    hidden_item = next(r for r in items_hidden if r["商品信息"]["商品ID"] == "9999")
    assert hidden_item["_hidden_reason"] == "rule"


def test_manual_hidden_status_excluded():
    _seed(5)
    storage._update_item_status_sync("sony_a7m4_full_data.jsonl", "1000", "hidden")

    total, items = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=False,
    )
    assert total == 4
    assert all(r["商品信息"]["商品ID"] != "1000" for r in items)

    total_all, _ = storage._query_result_records_sync(
        "sony_a7m4_full_data.jsonl", ai_recommended_only=False,
        keyword_recommended_only=False, sort_by="crawl_time",
        sort_order="desc", page=1, limit=100, include_hidden=True,
    )
    assert total_all == 5


def test_load_result_summary_aggregates_in_sql():
    _seed(30)

    summary = storage._load_result_summary_sync("sony_a7m4_full_data.jsonl")
    assert summary is not None
    assert summary["total_items"] == 30
    recommended = [i for i in range(30) if i % 3 == 0]
    assert summary["recommended_items"] == len(recommended)
    assert summary["ai_recommended_items"] == len([i for i in recommended if i % 2 == 0])
    assert summary["keyword_recommended_items"] == len([i for i in recommended if i % 2 != 0])
    # 最新记录应是 crawl_time 最大者（种子数据按 i 递增时间）
    expected_latest = f"2026-01-01T{29 // 60:02d}:{29 % 60:02d}:00"
    assert summary["latest_record"]["爬取时间"] == expected_latest
    assert summary["latest_recommendation"]["ai_analysis"]["is_recommended"] is True


def test_load_result_summary_none_when_empty():
    assert storage._load_result_summary_sync("empty_full_data.jsonl") is None


def test_visible_item_ids_uses_sql_and_excludes_hidden():
    _seed(6)
    storage._save_result_blacklist_keywords_sync("sony_a7m4_full_data.jsonl", ["验货宝"])
    storage._update_item_status_sync("sony_a7m4_full_data.jsonl", "1001", "hidden")

    ids = storage.load_visible_result_item_ids("sony_a7m4_full_data.jsonl")
    assert "1001" not in ids  # 手动隐藏
    assert "1000" in ids
    assert len(ids) == 5
