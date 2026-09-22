import asyncio
from types import SimpleNamespace

from src.services.process_service import (
    DEFAULT_MAX_CONCURRENT_PROCESSES,
    ProcessService,
    _max_concurrent_processes,
)


class FakeProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self.returncode = None

    async def wait(self):
        return self.returncode


def _make_service(tmp_path, monkeypatch):
    service = ProcessService()
    service.failure_guard.should_skip_start = lambda *args, **kwargs: SimpleNamespace(
        skip=False,
        should_notify=False,
        reason="",
        consecutive_failures=0,
        paused_until=None,
    )
    monkeypatch.setattr(
        "src.services.process_service.build_task_log_path",
        lambda task_id, _task_name: str(tmp_path / f"task-{task_id}.log"),
    )
    return service


def test_max_concurrent_processes_env_parsing(monkeypatch):
    monkeypatch.delenv("MAX_CONCURRENT_SPIDER_PROCESSES", raising=False)
    assert _max_concurrent_processes() == DEFAULT_MAX_CONCURRENT_PROCESSES

    monkeypatch.setenv("MAX_CONCURRENT_SPIDER_PROCESSES", "5")
    assert _max_concurrent_processes() == 5

    monkeypatch.setenv("MAX_CONCURRENT_SPIDER_PROCESSES", "0")
    assert _max_concurrent_processes() == DEFAULT_MAX_CONCURRENT_PROCESSES

    monkeypatch.setenv("MAX_CONCURRENT_SPIDER_PROCESSES", "abc")
    assert _max_concurrent_processes() == DEFAULT_MAX_CONCURRENT_PROCESSES


def test_start_task_skipped_when_process_cap_reached(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_SPIDER_PROCESSES", "2")

    async def run_scenario():
        service = _make_service(tmp_path, monkeypatch)

        # 预置 2 个"运行中"的进程（达到上限）
        for task_id in (1, 2):
            proc = FakeProcess(pid=1000 + task_id)
            service._register_runtime(
                task_id,
                f"running-task-{task_id}",
                proc,
                str(tmp_path / f"task-{task_id}.log"),
                None,
            )

        # 注册 runtime 会创建 exit watcher，测试中直接取消避免泄漏
        # 第 3 个任务应被跳过
        async def fail_spawn(*_args, **_kwargs):
            raise AssertionError("should not spawn when cap reached")

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fail_spawn)

        started = await service.start_task(3, "queued-task")
        assert started is False
        assert 3 not in service.processes

        # 释放一个进程后可以启动
        service.processes[1].returncode = 0
        spawned = FakeProcess(pid=3003)

        async def fake_spawn(*_args, **_kwargs):
            return spawned

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)
        started = await service.start_task(3, "queued-task")
        assert started is True
        assert service.processes[3] is spawned

    asyncio.run(run_scenario())


def test_start_task_allowed_below_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_CONCURRENT_SPIDER_PROCESSES", "3")

    async def run_scenario():
        service = _make_service(tmp_path, monkeypatch)

        proc = FakeProcess(pid=2001)
        service._register_runtime(
            1, "only-task", proc, str(tmp_path / "task-1.log"), None
        )

        spawned = FakeProcess(pid=2002)

        async def fake_spawn(*_args, **_kwargs):
            return spawned

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)

        started = await service.start_task(2, "second-task")
        assert started is True
        assert service.processes[2] is spawned

    asyncio.run(run_scenario())


def test_describe_last_skip_reports_pause_details(tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    async def run_scenario():
        service = _make_service(tmp_path, monkeypatch)
        paused_until = datetime(2026, 9, 23, 8, 0, 0)
        decision = SimpleNamespace(
            skip=True,
            should_notify=False,
            reason="Login required: redirected to passport",
            consecutive_failures=3,
            paused_until=paused_until,
        )
        service.failure_guard.should_skip_start = lambda *args, **kwargs: decision

        started = await service.start_task(0, "Mac mini M4")
        assert started is False

        description = service.describe_last_skip("Mac mini M4")
        assert description is not None
        assert "失败保护暂停" in description
        assert "3/3" in description
        assert "2026-09-23 08:00:00" in description
        assert "Login required" in description

        # 未知任务无描述
        assert service.describe_last_skip("other-task") is None

    asyncio.run(run_scenario())


def test_resolve_cookie_path_prefers_bound_account(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    bound = tmp_path / "state" / "bound.json"
    bound.parent.mkdir()
    bound.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "src.services.process_service.find_task_by_name_sync",
        lambda name: SimpleNamespace(account_state_file=str(bound)),
    )

    assert service._resolve_cookie_path("task") == str(bound)


def test_resolve_cookie_path_falls_back_to_newest_pool_state(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.services.process_service.find_task_by_name_sync",
        lambda name: SimpleNamespace(account_state_file=None),
    )
    monkeypatch.setattr(
        "src.services.process_service.STATE_FILE", str(tmp_path / "missing.json")
    )
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    older = state_dir / "old.json"
    older.write_text("{}", encoding="utf-8")
    newer = state_dir / "Default.json"
    newer.write_text("{}", encoding="utf-8")
    import os

    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    monkeypatch.setenv("ACCOUNT_STATE_DIR", str(state_dir))

    assert service._resolve_cookie_path("task") == str(newer)


def test_resolve_cookie_path_none_when_no_state_available(tmp_path, monkeypatch):
    service = _make_service(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.services.process_service.find_task_by_name_sync", lambda name: None
    )
    monkeypatch.setattr(
        "src.services.process_service.STATE_FILE", str(tmp_path / "missing.json")
    )
    monkeypatch.setenv("ACCOUNT_STATE_DIR", str(tmp_path / "no-such-dir"))

    assert service._resolve_cookie_path("task") is None


def test_start_task_auto_recovers_after_pool_state_updated(tmp_path, monkeypatch):
    """未绑定账号的任务：更新账号池中的登录态后，失败保护应自动恢复启动。"""
    import os

    from src.failure_guard import FailureGuard
    from src.services.process_service import ProcessService

    guard_path = tmp_path / "guard.json"
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    cookie = state_dir / "Default.json"
    cookie.write_text("{}", encoding="utf-8")
    os.utime(cookie, (1000, 1000))

    monkeypatch.setenv("TASK_FAILURE_GUARD_PATH", str(guard_path))
    monkeypatch.setenv("ACCOUNT_STATE_DIR", str(state_dir))
    monkeypatch.setattr(
        "src.services.process_service.STATE_FILE", str(tmp_path / "missing.json")
    )
    monkeypatch.setattr(
        "src.services.process_service.find_task_by_name_sync",
        lambda name: SimpleNamespace(account_state_file=None),
    )
    monkeypatch.setattr(
        "src.services.process_service.build_task_log_path",
        lambda task_id, _task_name: str(tmp_path / f"task-{task_id}.log"),
    )

    # 记录一次失败并进入暂停
    FailureGuard().record_failure(
        "Mac mini M4", "Login required", cookie_path=str(cookie), min_failures_to_pause=1
    )

    # 用户更新登录态（mtime 变新）
    os.utime(cookie, (2000, 2000))

    async def run_scenario():
        service = ProcessService()
        spawned = FakeProcess(pid=9100)

        async def fake_spawn(*_args, **_kwargs):
            return spawned

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)

        started = await service.start_task(0, "Mac mini M4")
        assert started is True
        assert service.processes[0] is spawned

    asyncio.run(run_scenario())
