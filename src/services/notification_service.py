"""
通知服务
统一管理所有通知渠道
"""
import asyncio
import os
import threading
import time
from datetime import datetime, time as dtime
from typing import Dict, List, Optional

from src.infrastructure.external.notification_clients.base import NotificationClient
from src.infrastructure.external.notification_clients.factory import build_notification_clients
from src.services.notification_config_service import load_notification_settings
from src.infrastructure.config.settings import NotificationSettings


# 去重缓存（模块级共享，跨 NotificationService 实例生效）
_recent_notifications: Dict[str, float] = {}
_dedup_lock = threading.Lock()


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def _dedup_window_seconds() -> int:
    """通知去重窗口（秒）。0 表示关闭（默认）。"""
    return _env_int("NOTIFICATION_DEDUP_WINDOW_SECONDS", 0)


def _notification_key(product_data: Dict) -> str:
    if not isinstance(product_data, dict):
        return ""
    for field in ("商品链接", "商品ID", "商品标题"):
        value = str(product_data.get(field) or "").strip()
        if value:
            return f"{field}:{value}"
    return ""


def _parse_quiet_hours(raw: str) -> Optional[tuple[dtime, dtime]]:
    text = str(raw or "").strip()
    if not text or "-" not in text:
        return None
    try:
        start_text, end_text = text.split("-", 1)
        start = datetime.strptime(start_text.strip(), "%H:%M").time()
        end = datetime.strptime(end_text.strip(), "%H:%M").time()
    except ValueError:
        return None
    return start, end


def _is_quiet_now(now: Optional[datetime] = None) -> bool:
    """是否处于静默时段（NOTIFICATION_QUIET_HOURS，如 "23:00-07:00"，支持跨天）。"""
    window = _parse_quiet_hours(os.getenv("NOTIFICATION_QUIET_HOURS", ""))
    if window is None:
        return False
    start, end = window
    current = (now or datetime.now()).time()
    if start == end:
        return False
    if start < end:
        return start <= current < end
    # 跨天：如 23:00-07:00
    return current >= start or current < end


def _is_duplicate(key: str) -> bool:
    window = _dedup_window_seconds()
    if window <= 0 or not key:
        return False
    now = time.monotonic()
    with _dedup_lock:
        # 顺带清理过期条目，避免长期运行内存增长
        for stale_key in [k for k, ts in _recent_notifications.items() if now - ts > window]:
            _recent_notifications.pop(stale_key, None)
        last = _recent_notifications.get(key)
        if last is not None and now - last < window:
            return True
        _recent_notifications[key] = now
        return False


def reset_notification_dedup_cache() -> None:
    """清空去重缓存（测试用）。"""
    with _dedup_lock:
        _recent_notifications.clear()


class NotificationService:
    """通知服务"""

    def __init__(self, clients: List[NotificationClient]):
        self.clients = [client for client in clients if client.is_enabled()]

    async def send_notification(
        self,
        product_data: Dict,
        reason: str,
        *,
        force: bool = False,
    ) -> Dict[str, Dict[str, str | bool]]:
        """
        发送通知到所有启用的渠道

        Args:
            force: 跳过静默时段与去重（用于测试通知）
        Returns:
            各渠道发送结果，包含成功状态和消息
        """
        if not self.clients:
            return {}

        if not force:
            if _is_quiet_now():
                print("[通知] 当前处于静默时段 (NOTIFICATION_QUIET_HOURS)，已跳过本次通知。")
                return {}
            key = _notification_key(product_data)
            if _is_duplicate(key):
                print(f"[通知] 命中去重窗口 (NOTIFICATION_DEDUP_WINDOW_SECONDS)，已跳过重复通知: {key}")
                return {}

        tasks = [
            self._send_with_result(client, product_data, reason)
            for client in self.clients
        ]
        results = await asyncio.gather(*tasks)
        return {result["channel"]: result for result in results}

    async def send_test_notification(self) -> Dict[str, Dict[str, str | bool]]:
        test_product = {
            "商品标题": "[测试通知] 闲鱼智能监控",
            "当前售价": "0",
            "商品链接": "https://www.goofish.com/",
        }
        return await self.send_notification(
            test_product,
            "这是一条测试通知，用于验证推送渠道是否可用。",
            force=True,
        )

    async def _send_with_result(
        self,
        client: NotificationClient,
        product_data: Dict,
        reason: str,
    ) -> Dict[str, str | bool]:
        try:
            await client.send(product_data, reason)
            return {
                "channel": client.channel_key,
                "label": client.display_name,
                "success": True,
                "message": "发送成功",
            }
        except Exception as exc:
            return {
                "channel": client.channel_key,
                "label": client.display_name,
                "success": False,
                "message": str(exc),
            }


def build_notification_service(
    settings: NotificationSettings | None = None,
) -> NotificationService:
    notification_settings = settings or load_notification_settings()
    return NotificationService(build_notification_clients(notification_settings))
