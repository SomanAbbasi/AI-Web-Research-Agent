from collections import deque


class URLFrontier:
    """FIFO queue that prevents duplicate URLs."""

    def __init__(self) -> None:
        self._queue: deque[tuple[str, int]] = deque()
        self._seen: set[str] = set()

    def add(self, url: str, depth: int) -> bool:
        if url in self._seen:
            return False

        self._seen.add(url)
        self._queue.append((url, depth))

        return True

    def pop(self) -> tuple[str, int] | None:
        if not self._queue:
            return None

        return self._queue.popleft()

    def has_seen(self, url: str) -> bool:
        return url in self._seen

    def __len__(self) -> int:
        return len(self._queue)