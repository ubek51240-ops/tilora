"""
Oddiy xotiradagi (in-memory) so'rovlar chegaralovchisi.

Bitta jarayon ichida ishlaydi (gunicorn bir nechta worker bilan ishlasa, har worker alohida
hisoblaydi — bu holda nginx `limit_req` qo'shimcha himoya beradi, qarang nginx/conf.d/default.conf).
"""
import threading
import time
from collections import deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max(1, int(max_events))
        self.window = max(1, int(window_seconds))
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> Deque[float]:
        q = self._events.setdefault(key, deque())
        cutoff = now - self.window
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def is_limited(self, key: str) -> Tuple[bool, int]:
        """(cheklanganmi, qancha soniyadan keyin ochiladi)."""
        now = time.time()
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.max_events:
                retry = int(q[0] + self.window - now) + 1
                return True, max(1, retry)
            return False, 0

    def record(self, key: str) -> None:
        now = time.time()
        with self._lock:
            q = self._prune(key, now)
            q.append(now)
            # Xotira o'sib ketmasligi uchun eski kalitlarni vaqti-vaqti bilan tozalash
            if len(self._events) > 5000:
                for k in [k for k, v in self._events.items() if not v or v[-1] < now - self.window]:
                    self._events.pop(k, None)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def check_and_record(self, key: str, detail: str) -> None:
        """Cheklov oshgan bo'lsa 429 beradi, aks holda hodisani yozadi."""
        limited, retry = self.is_limited(key)
        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={"Retry-After": str(retry)},
            )
        self.record(key)


def client_ip(request: Request) -> str:
    """Proksi orqasida bo'lsa X-Forwarded-For ning birinchi manzili, aks holda to'g'ridan-to'g'ri IP."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]
