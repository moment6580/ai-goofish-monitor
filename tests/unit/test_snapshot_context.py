"""增强快照上下文覆盖的回归测试。

背景：桌面浏览器导出的增强快照曾把 UA/视口覆盖为桌面环境，并且其抓包请求头
（Accept: */*、Sec-Fetch-* 等）被全局注入，导致闲鱼返回 PC 版页面、
移动端搜索接口永不触发（任务表现为 30s 等待响应超时）。
"""
from src.scraper.browser import (
    _build_context_overrides,
    _default_context_options,
    snapshot_is_mobile,
)

DESKTOP_SNAPSHOT = {
    "cookies": [{"name": "unb", "value": "1"}],
    "headers": {
        "sec-ch-ua-platform": '"Windows"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.goofish.com/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
    },
    "env": {
        "navigator": {"userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/153.0.0.0", "maxTouchPoints": 0},
        "screen": {"width": 2560, "height": 1440, "devicePixelRatio": 1.5},
        "intl": {"timeZone": "Asia/Shanghai"},
    },
}

MOBILE_SNAPSHOT = {
    "cookies": [{"name": "unb", "value": "1"}],
    "headers": {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36",
    },
    "env": {
        "navigator": {"userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/131 Mobile", "maxTouchPoints": 5},
        "screen": {"width": 412, "height": 915, "devicePixelRatio": 2.625},
        "intl": {"timeZone": "Asia/Shanghai"},
    },
}


def test_snapshot_is_mobile_detection():
    assert snapshot_is_mobile(DESKTOP_SNAPSHOT) is False
    assert snapshot_is_mobile(MOBILE_SNAPSHOT) is True
    assert snapshot_is_mobile({}) is False


def test_desktop_snapshot_keeps_mobile_emulation():
    defaults = _default_context_options()
    overrides = _build_context_overrides(DESKTOP_SNAPSHOT)

    # 桌面快照不得覆盖 UA / 视口 / is_mobile / DSR / 触屏
    assert "user_agent" not in overrides
    assert "viewport" not in overrides
    assert "is_mobile" not in overrides
    assert "device_scale_factor" not in overrides
    assert "has_touch" not in overrides

    # 语言/时区等安全参数仍可应用
    assert overrides.get("locale") == "zh-CN"
    assert overrides.get("timezone_id") == "Asia/Shanghai"

    # 合并后仍是移动端环境
    merged = {**defaults, **overrides}
    assert merged["is_mobile"] is True
    assert merged["viewport"] == {"width": 412, "height": 915}
    assert "Mobile" in merged["user_agent"]


def test_mobile_snapshot_applies_full_environment():
    overrides = _build_context_overrides(MOBILE_SNAPSHOT)

    assert "Android" in overrides["user_agent"]
    assert overrides["viewport"] == {"width": 412, "height": 915}
    assert overrides["device_scale_factor"] == 2.625
    assert overrides["has_touch"] is True
    assert overrides["is_mobile"] is True
    assert overrides.get("timezone_id") == "Asia/Shanghai"


def test_flow_does_not_inject_snapshot_request_headers():
    """快照请求头不得全局注入（会破坏页面 Fetch 元数据导致接口不触发）。"""
    import inspect

    from src.scraper import flow

    source = inspect.getsource(flow)
    assert "extra_http_headers" not in source
    assert "_build_extra_headers" not in source
