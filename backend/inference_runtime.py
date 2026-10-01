from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar


T = TypeVar("T")
INFERENCE_CONCURRENCY = max(1, int(os.getenv("INFERENCE_CONCURRENCY", "1")))
INFERENCE_SEMAPHORE = asyncio.Semaphore(INFERENCE_CONCURRENCY)
_RECOVERY_LOCK = asyncio.Lock()


async def run_inference(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run CPU/GPU-bound inference off the event loop with bounded concurrency."""
    async with INFERENCE_SEMAPHORE:
        return await asyncio.to_thread(fn, *args, **kwargs)


async def recover_exclusively(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Wait for all active inference slots before mutating shared model state."""
    async with _RECOVERY_LOCK:
        for _ in range(INFERENCE_CONCURRENCY):
            await INFERENCE_SEMAPHORE.acquire()
        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        finally:
            for _ in range(INFERENCE_CONCURRENCY):
                INFERENCE_SEMAPHORE.release()
