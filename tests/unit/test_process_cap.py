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
