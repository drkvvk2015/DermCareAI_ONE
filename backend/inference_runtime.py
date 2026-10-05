from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar


T = TypeVar("T")
INFERENCE_CONCURRENCY = max(1, int(os.getenv("INFERENCE_CONCURRENCY", "1")))
INFERENCE_SEMAPHORE = asyncio.Semaphore(INFERENCE_CONCURRENCY)
_RECOVERY_LOCK = asyncio.Lock()


async def _run_in_worker(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a worker thread to completion even if the awaiting task is cancelled."""
    worker = asyncio.create_task(asyncio.to_thread(fn, *args, **kwargs))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        await asyncio.shield(worker)
        raise


async def run_inference(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run CPU/GPU-bound inference off the event loop with bounded concurrency."""
    async with INFERENCE_SEMAPHORE:
        return await _run_in_worker(fn, *args, **kwargs)


async def recover_exclusively(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Wait for all active inference slots before mutating shared model state."""
    async with _RECOVERY_LOCK:
        acquired = 0
        try:
            for _ in range(INFERENCE_CONCURRENCY):
                await INFERENCE_SEMAPHORE.acquire()
                acquired += 1
            return await _run_in_worker(fn, *args, **kwargs)
        finally:
            for _ in range(acquired):
                INFERENCE_SEMAPHORE.release()
