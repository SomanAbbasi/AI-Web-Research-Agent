from ai_web_research_agent.services.frontier import URLFrontier


def test_frontier_add_and_pop():
    frontier = URLFrontier()

    assert frontier.add(
        "https://example.com",
        0,
    )

    assert frontier.pop() == (
        "https://example.com",
        0,
    )


def test_frontier_prevents_duplicates():
    frontier = URLFrontier()

    assert frontier.add(
        "https://example.com",
        0,
    )

    assert not frontier.add(
        "https://example.com",
        0,
    )


def test_empty_frontier():
    frontier = URLFrontier()

    assert frontier.pop() is None


def test_frontier_fifo():
    frontier = URLFrontier()

    frontier.add(
        "https://example.com/a",
        1,
    )

    frontier.add(
        "https://example.com/b",
        1,
    )

    assert frontier.pop() == (
        "https://example.com/a",
        1,
    )

    assert frontier.pop() == (
        "https://example.com/b",
        1,
    )
