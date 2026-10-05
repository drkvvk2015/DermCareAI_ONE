import asyncio
import threading

import inference_runtime


def test_run_inference_waits_for_worker_before_releasing_permit():
    async def exercise():
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()

        def worker() -> str:
            started.set()
            release.wait(2)
            finished.set()
            return "ok"

        task = asyncio.create_task(inference_runtime.run_inference(worker))
        assert await asyncio.to_thread(started.wait, 1)

        task.cancel()
        await asyncio.sleep(0)
        assert not finished.is_set()

        release.set()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancelled inference must propagate cancellation")

        assert finished.is_set()
        assert await inference_runtime.run_inference(lambda: "recovered") == "recovered"

    asyncio.run(exercise())


def test_recover_exclusively_releases_only_acquired_permits_on_cancellation(monkeypatch):
    async def exercise():
        semaphore = asyncio.Semaphore(2)
        monkeypatch.setattr(inference_runtime, "INFERENCE_CONCURRENCY", 2)
        monkeypatch.setattr(inference_runtime, "INFERENCE_SEMAPHORE", semaphore)
        monkeypatch.setattr(inference_runtime, "_RECOVERY_LOCK", asyncio.Lock())

        await semaphore.acquire()

        task = asyncio.create_task(
            inference_runtime.recover_exclusively(lambda: "recovered")
        )
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("cancelled recovery must propagate cancellation")

        semaphore.release()
        assert semaphore._value == 2

    asyncio.run(exercise())
