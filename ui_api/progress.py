from __future__ import annotations

from contextvars import ContextVar
from typing import Callable


_progress_cb: ContextVar[Callable[[str], None] | None] = ContextVar("progress_cb", default=None)


def set_progress_callback(callback: Callable[[str], None] | None) -> object:
    return _progress_cb.set(callback)


def reset_progress_callback(token: object) -> None:
    _progress_cb.reset(token)


def publish_progress(message: str) -> None:
    cb = _progress_cb.get()
    if cb is not None:
        cb(message)

