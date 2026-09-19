"""
爬虫子进程注册表。

后端每次派生 spider_v2.py 时把 PID 记录到 data/running_pids.json；
后端自身异常退出后，重启时依据注册表回收仍然存活的孤儿爬虫进程，
避免 Chromium 进程泄漏和任务状态不一致。
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from src.infrastructure.persistence.sqlite_connection import get_database_path

REGISTRY_FILENAME = "running_pids.json"
SPIDER_MARKER = "spider_v2.py"
REAP_TERM_WAIT_SECONDS = 5.0


def registry_path() -> Path:
    db_path = Path(get_database_path())
    return db_path.parent / REGISTRY_FILENAME


def _load_raw(path: Path) -> Dict[str, dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_raw(path: Path, payload: Dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def record_spawn(task_id: int, pid: int, task_name: str) -> None:
    """记录一个新派生的爬虫子进程。"""
    path = registry_path()
    payload = _load_raw(path)
    pgid: Optional[int] = None
    if sys.platform != "win32":
        try:
            pgid = os.getpgid(pid)
        except ProcessLookupError:
            pgid = None
    payload[str(task_id)] = {
        "pid": pid,
        "pgid": pgid,
        "task_name": task_name,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _write_raw(path, payload)


def remove_entry(task_id: int) -> None:
    """任务运行时被清理时移除注册表条目。"""
    path = registry_path()
    payload = _load_raw(path)
    if str(task_id) not in payload:
        return
    payload.pop(str(task_id), None)
    _write_raw(path, payload)


def load_entries() -> List[dict]:
    """返回注册表中的全部条目（附带 task_id 字段）。"""
    path = registry_path()
    entries = []
    for task_id, info in _load_raw(path).items():
        if isinstance(info, dict) and isinstance(info.get("pid"), int):
            entries.append({"task_id": task_id, **info})
    return entries


def is_spider_process(pid: int) -> bool:
    """校验 PID 对应的进程是否仍是本项目的爬虫进程（防止 PID 复用误杀）。"""
    cmdline_file = Path(f"/proc/{pid}/cmdline")
    try:
        raw = cmdline_file.read_bytes()
    except OSError:
        return False
    argv = raw.decode("utf-8", errors="replace").split("\x00")
    return SPIDER_MARKER in argv or any(SPIDER_MARKER in arg for arg in argv)


def _kill_process_group(pgid: int) -> None:
    """对进程组先 SIGTERM，短暂等待后仍存活则 SIGKILL。"""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + REAP_TERM_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def reap_orphan_spiders() -> List[str]:
    """回收孤儿爬虫进程，返回被回收的任务名列表。

    - 仅回收 cmd_line 校验通过的进程（确认是 spider_v2.py）。
    - 回收后清空注册表。
    """
    entries = load_entries()
    if not entries:
        return []

    reaped: List[str] = []
    for entry in entries:
        pid = entry["pid"]
        task_name = str(entry.get("task_name", f"task-{entry.get('task_id')}"))
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            # 进程已不存在，视为已退出
            continue
        except PermissionError:
            pass

        if sys.platform == "win32":
            print(
                f"[SpawnRegistry] 检测到疑似孤儿爬虫进程 PID={pid} ({task_name})，"
                "Windows 下跳过自动回收，请手动确认。"
            )
            continue

        if not is_spider_process(pid):
            print(
                f"[SpawnRegistry] PID={pid} 已被复用为其他进程，跳过回收 ({task_name})。"
            )
            continue

        pgid = entry.get("pgid") or pid
        print(
            f"[SpawnRegistry] 回收孤儿爬虫进程 PID={pid} PGID={pgid} (任务: {task_name})..."
        )
        try:
            _kill_process_group(int(pgid))
            reaped.append(task_name)
        except Exception as exc:
            print(f"[SpawnRegistry] 回收 PID={pid} 失败: {exc}")

    # 无论回收成功与否，注册表都已过期，直接清空
    _write_raw(registry_path(), {})
    return reaped
