"""静态检查：防止重构（如模块拆分）后出现未定义名称。

背景：scraper.py 拆分为包后，flow.py 漏导入 FAILURE_GUARD / cleanup_task_images，
failure.py 漏导入 send_ntfy_notification，运行时才在爬取任务中崩溃，普通单测无法覆盖。
该测试使用 pyflakes 扫描，出现 undefined name 即失败。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_undefined_names_in_source():
    try:
        import pyflakes  # noqa: F401
    except ImportError:
        pytest.skip("pyflakes 未安装（CI 中会安装并强制执行）")

    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", "src/", "spider_v2.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    undefined = [
        line for line in result.stdout.splitlines()
        if "undefined name" in line
    ]
    assert undefined == [], "发现未定义名称（可能是拆分/重构遗漏的导入）:\n" + "\n".join(undefined)


def test_scraper_package_runtime_symbols():
    """爬取主链路依赖的模块级符号必须存在（运行时回归）。"""
    from src.scraper import flow
    from src.scraper import failure

    assert flow.FAILURE_GUARD is failure.FAILURE_GUARD
    assert callable(flow.cleanup_task_images)
    assert callable(failure.send_ntfy_notification)
    assert callable(flow.scrape_xianyu)
