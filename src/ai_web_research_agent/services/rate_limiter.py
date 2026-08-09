import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """Enforces a minimum delay between requests to the same host.

    The clock and sleeper are injectable so timing can be verified in
    tests without actually sleeping.
    """

    def __init__(
        self,
        delay: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if delay < 0:
            raise ValueError("delay must not be negative")

        self._delay = delay
        self._clock = clock
        self._sleeper = sleeper
        self._last_request: dict[str, float] = {}

    async def wait(self, host: str) -> None:
        """Block until the next request to ``host`` may be sent."""
        if self._delay <= 0:
            return

        now = self._clock()
        last = self._last_request.get(host)

        if last is not None:
            remaining = self._delay - (now - last)

            if remaining > 0:
                await self._sleeper(remaining)

        self._last_request[host] = self._clock()
