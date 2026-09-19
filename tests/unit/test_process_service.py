import asyncio
import sys
from types import SimpleNamespace

from src.services.process_service import ProcessService


class FakeProcess:
    def __init__(self, pid: int):
        self.pid = pid
        self.returncode = None
        self._done = asyncio.Event()

    async def wait(self):
        await self._done.wait()
        return self.returncode

    def finish(self, returncode: int = 0):
        self.returncode = returncode
        self._done.set()

    def terminate(self):
        self.finish(-15)

    def kill(self):
        self.finish(-9)


def test_process_service_marks_task_stopped_when_process_exits(monkeypatch, tmp_path):
    fake_process = FakeProcess(pid=4321)
    events = []

    async def run_scenario():
        service = ProcessService()
        service.failure_guard.should_skip_start = lambda *args, **kwargs: SimpleNamespace(
            skip=False,
            should_notify=False,
            reason="",
            consecutive_failures=0,
            paused_until=None,
        )

        stopped = asyncio.Event()

        async def on_started(task_id: int):
            events.append(("started", task_id))

        async def on_stopped(task_id: int):
            events.append(("stopped", task_id))
            stopped.set()

        service.set_lifecycle_hooks(on_started=on_started, on_stopped=on_stopped)

        async def fake_create_subprocess_exec(*_args, **_kwargs):
            return fake_process

        monkeypatch.setattr(
            "src.services.process_service.build_task_log_path",
            lambda task_id, _task_name: str(tmp_path / f"task-{task_id}.log"),
        )
        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

        started = await service.start_task(0, "task-a")
        assert started is True
        assert events == [("started", 0)]
        assert service.is_running(0) is True

        fake_process.finish(0)
        await asyncio.wait_for(stopped.wait(), timeout=1)

        assert ("stopped", 0) in events
        assert service.is_running(0) is False

    asyncio.run(run_scenario())


def test_process_service_keeps_task_ids_stable_after_cleanup():
    """清理某个任务的运行时状态后，其他任务的 ID 不得漂移。"""
    service = ProcessService()
    proc_a = object()
    proc_c = object()

    service.processes = {0: proc_a, 2: proc_c}
    service.log_paths = {0: "a.log", 2: "c.log"}
    service.task_names = {0: "A", 2: "C"}

    service._cleanup_runtime(0, proc_a)

    # 仅移除被清理任务自身的条目，任务 2 的 ID 与状态保持原样
    assert service.processes == {2: proc_c}
    assert service.log_paths == {2: "c.log"}
    assert service.task_names == {2: "C"}


def test_process_service_adds_debug_limit_arg_when_env_enabled(monkeypatch):
    monkeypatch.setenv("SPIDER_DEBUG_LIMIT", "1")
    service = ProcessService()

    command = service._build_spawn_command("task-a")

    assert command == [
        sys.executable,
        "-u",
        "spider_v2.py",
        "--task-name",
        "task-a",
        "--debug-limit",
        "1",
    ]
