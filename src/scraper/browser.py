"""浏览器启动、上下文与反检测辅助。"""
from __future__ import annotations

from typing import Optional

from src.config import LOGIN_IS_EDGE, RUNNING_IN_DOCKER

EDGE_DOCKER_WARNING_PRINTED = False


def _resolve_browser_channel() -> str:
    global EDGE_DOCKER_WARNING_PRINTED
    if RUNNING_IN_DOCKER:
        if LOGIN_IS_EDGE and not EDGE_DOCKER_WARNING_PRINTED:
            print(
                "检测到 LOGIN_IS_EDGE=true，但 Docker 镜像未内置 Edge，"
                "任务运行时将改用 Chromium。"
            )
            EDGE_DOCKER_WARNING_PRINTED = True
        return "chromium"
    return "msedge" if LOGIN_IS_EDGE else "chrome"


def _default_context_options() -> dict:
    return {
        "user_agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
        "viewport": {"width": 412, "height": 915},
        "device_scale_factor": 2.625,
        "is_mobile": True,
        "has_touch": True,
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "permissions": ["geolocation"],
        "geolocation": {"longitude": 121.4737, "latitude": 31.2304},
        "color_scheme": "light",
    }


def _clean_kwargs(options: dict) -> dict:
    return {k: v for k, v in options.items() if v is not None}


def _looks_like_mobile(ua: str) -> Optional[bool]:
    if not ua:
        return None
    ua_lower = ua.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        return True
    if "windows" in ua_lower or "macintosh" in ua_lower:
        return False
    return None


def _snapshot_user_agent(snapshot: dict) -> str:
    headers = snapshot.get("headers") or {}
    navigator = (snapshot.get("env") or {}).get("navigator") or {}
    return str(
        headers.get("User-Agent")
        or headers.get("user-agent")
        or navigator.get("userAgent")
        or ""
    )


def snapshot_is_mobile(snapshot: dict) -> bool:
    """快照环境是否为移动端；无法判定时按非移动处理（保持项目默认移动端模拟）。"""
    return _looks_like_mobile(_snapshot_user_agent(snapshot)) is True


def _build_context_overrides(snapshot: dict) -> dict:
    """从增强快照提取上下文覆盖参数。

    重要：抓取链路依赖闲鱼移动端 H5 页面与接口（选择器、搜索接口均为移动端），
    因此 UA/视口/触屏等显示环境**仅在快照本身来自移动端时**才覆盖；
    桌面浏览器导出的快照会保持项目默认的移动端模拟，否则页面会走 PC 版、
    移动端搜索接口永不触发，任务表现为等待响应超时。
    """
    env = snapshot.get("env") or {}
    headers = snapshot.get("headers") or {}
    navigator = env.get("navigator") or {}
    screen = env.get("screen") or {}
    intl = env.get("intl") or {}

    overrides: dict = {}

    ua = _snapshot_user_agent(snapshot)
    mobile_flag = _looks_like_mobile(ua)

    if ua and mobile_flag is True:
        overrides["user_agent"] = ua

    accept_language = headers.get("Accept-Language") or headers.get("accept-language")
    locale = None
    if accept_language:
        locale = accept_language.split(",")[0].strip()
    elif navigator.get("language"):
        locale = navigator["language"]
    if locale:
        overrides["locale"] = locale

    tz = intl.get("timeZone")
    if tz:
        overrides["timezone_id"] = tz

    # 显示环境（视口/像素比/触屏/移动端标记）仅在移动端快照下应用
    if mobile_flag is True:
        width = screen.get("width")
        height = screen.get("height")
        if isinstance(width, (int, float)) and isinstance(height, (int, float)):
            overrides["viewport"] = {"width": int(width), "height": int(height)}

        dpr = screen.get("devicePixelRatio")
        if isinstance(dpr, (int, float)):
            overrides["device_scale_factor"] = float(dpr)

        touch_points = navigator.get("maxTouchPoints")
        if isinstance(touch_points, (int, float)):
            overrides["has_touch"] = touch_points > 0

        overrides["is_mobile"] = True

    return _clean_kwargs(overrides)
