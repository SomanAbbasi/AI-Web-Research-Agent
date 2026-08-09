import pytest

from ai_web_research_agent.services.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def __call__(self) -> float:
        return self._now


def make_limiter(delay: float):
    clock = FakeClock()
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        clock.advance(seconds)

    return (
        RateLimiter(
            delay=delay,
            clock=clock,
            sleeper=sleeper,
        ),
        clock,
        sleeps,
    )


@pytest.mark.asyncio
async def test_first_request_does_not_wait():
    limiter, _, sleeps = make_limiter(delay=0.5)

    await limiter.wait("example.com")

    assert sleeps == []


@pytest.mark.asyncio
async def test_enforces_minimum_delay_between_requests():
    limiter, clock, sleeps = make_limiter(delay=0.5)

    await limiter.wait("example.com")
    clock.advance(0.2)
    await limiter.wait("example.com")

    assert sleeps == [0.3]


@pytest.mark.asyncio
async def test_no_wait_when_delay_elapsed():
    limiter, clock, sleeps = make_limiter(delay=0.5)

    await limiter.wait("example.com")
    clock.advance(1.0)
    await limiter.wait("example.com")

    assert sleeps == []


@pytest.mark.asyncio
async def test_delay_tracks_per_host():
    limiter, _, sleeps = make_limiter(delay=0.5)

    await limiter.wait("example.com")
    await limiter.wait("other.org")

    assert sleeps == []


@pytest.mark.asyncio
async def test_zero_delay_is_immediate():
    limiter, _, sleeps = make_limiter(delay=0.0)

    await limiter.wait("example.com")
    await limiter.wait("example.com")

    assert sleeps == []


def test_negative_delay_rejected():
    with pytest.raises(ValueError):
        RateLimiter(delay=-1.0)
