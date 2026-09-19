import pytest

from src.infrastructure.persistence.sqlite_connection import init_schema
from src.services.price_history_service import (
    build_latest_market_summary,
    build_market_reference,
    build_price_history_insights,
    build_snapshot_index,
    load_latest_market_snapshots,
    load_price_snapshots_for_items,
    load_price_snapshots_since,
    record_market_snapshots,
    summarize_current_market,
    summarize_latest_run,
    summarize_snapshots_latest,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "app.sqlite3"
    monkeypatch.setenv("APP_DATABASE_FILE", str(db_file))
    import sqlite3

    with sqlite3.connect(db_file) as conn:
        init_schema(conn)
    yield db_file


def _item(item_id: str, price: int) -> dict:
    return {
        "商品ID": item_id,
        "商品标题": f"item-{item_id}",
        "当前售价": f"¥{price}",
        "商品链接": f"https://x/{item_id}",
    }


def _seed() -> None:
    record_market_snapshots(
        keyword="sony a7m4",
        task_name="task",
        items=[_item("1", 10000), _item("2", 11000)],
        run_id="run-1",
        snapshot_time="2026-01-01T12:00:00",
        seen_item_ids=set(),
    )
    record_market_snapshots(
        keyword="sony a7m4",
        task_name="task",
        items=[_item("1", 9500), _item("2", 12000), _item("3", 10500)],
        run_id="run-2",
        snapshot_time="2026-01-02T12:00:00",
        seen_item_ids=set(),
    )


def test_load_price_snapshots_for_items_filters_and_groups():
    _seed()

    grouped = load_price_snapshots_for_items("sony a7m4", ["1"])
    assert set(grouped.keys()) == {"1"}
    assert len(grouped["1"]) == 2
    assert [s["price"] for s in grouped["1"]] == [10000.0, 9500.0]

    assert load_price_snapshots_for_items("sony a7m4", []) == {}
    assert load_price_snapshots_for_items("sony a7m4", ["does-not-exist"]) == {}


def test_load_latest_market_snapshots_returns_latest_run_only():
    _seed()

    latest = load_latest_market_snapshots("sony a7m4")
    assert {s["run_id"] for s in latest} == {"run-2"}
    assert len(latest) == 3

    # 仅在可见商品范围内取最新 run
    only_item_1 = load_latest_market_snapshots("sony a7m4", ["1"])
    assert {s["run_id"] for s in only_item_1} == {"run-2"}
    assert {s["item_id"] for s in only_item_1} == {"1"}

    assert load_latest_market_snapshots("sony a7m4", []) == []
    assert load_latest_market_snapshots("unknown kw") == []


def test_build_latest_market_summary_matches_visible_scope():
    _seed()

    summary = build_latest_market_summary("sony a7m4", ["1", "2", "3"])
    assert summary["sample_count"] == 3
    assert summary["min_price"] == 9500.0
    assert summary["max_price"] == 12000.0

    only_1 = build_latest_market_summary("sony a7m4", ["1"])
    assert only_1["sample_count"] == 1
    assert only_1["avg_price"] == 9500.0


def test_load_price_snapshots_since_window():
    _seed()

    recent = load_price_snapshots_since("sony a7m4", "2026-01-02T00:00:00")
    assert len(recent) == 3
    assert all(s["snapshot_time"] >= "2026-01-02T00:00:00" for s in recent)

    scoped = load_price_snapshots_since("sony a7m4", "2026-01-01T00:00:00", ["2"])
    assert len(scoped) == 2

    assert load_price_snapshots_since("sony a7m4", "2026-01-01T00:00:00", []) == []


def test_build_price_history_insights_visible_scope():
    _seed()

    all_insights = build_price_history_insights("sony a7m4")
    assert all_insights["market_summary"]["sample_count"] == 3
    assert all_insights["history_summary"]["unique_items"] == 3

    scoped = build_price_history_insights("sony a7m4", visible_item_ids={"1", "2"})
    assert scoped["market_summary"]["sample_count"] == 2
    assert scoped["history_summary"]["unique_items"] == 2
    assert scoped["latest_snapshot_at"] == "2026-01-02T12:00:00"

    # 空可见集合 → 空洞察（不应退化为"全部商品"）
    empty = build_price_history_insights("sony a7m4", visible_item_ids=set())
    assert empty["market_summary"]["sample_count"] == 0
    assert empty["latest_snapshot_at"] is None

def test_build_market_reference_precomputed_matches_internal():
    """预计算索引路径必须与逐条内部计算路径结果完全一致（P1 优化等价性）。"""
    _seed()
    target = _item("1", 9500)
    page_items = [_item("1", 9500), _item("2", 12000), _item("3", 10500)]

    # 旧路径：不传预计算值，内部全量扫描
    baseline = build_market_reference(
        keyword="sony a7m4",
        item=target,
        current_market_items=page_items,
        historical_snapshots=load_latest_market_snapshots("sony a7m4"),
    )

    # 新路径：一次性构建索引 + 预计算摘要
    snapshots = load_latest_market_snapshots("sony a7m4")
    index = build_snapshot_index(snapshots)
    latest_by_item = {iid: rows[-1] for iid, rows in index.items() if rows}
    optimized = build_market_reference(
        keyword="sony a7m4",
        item=target,
        current_market_items=page_items,
        historical_snapshots=snapshots,
        snapshots_by_item=index,
        current_market_summary=summarize_current_market(page_items),
        history_summary=summarize_snapshots_latest(latest_by_item.values()),
        market_summary=summarize_latest_run(snapshots),
    )

    assert optimized == baseline


def test_incremental_index_matches_full_dedupe():
    """增量维护的 latest_by_item 应等价于对全量快照做 dedupe_latest。"""
    from src.services.price_history_service import _dedupe_latest

    _seed()
    snapshots = load_latest_market_snapshots("sony a7m4")
    index = build_snapshot_index(snapshots)
    latest_by_item = {iid: rows[-1] for iid, rows in index.items() if rows}

    incremental = summarize_snapshots_latest(latest_by_item.values())
    full = summarize_snapshots_latest(snapshots)

    assert incremental == full
    assert incremental["sample_count"] == len(_dedupe_latest(snapshots, "item_id"))
