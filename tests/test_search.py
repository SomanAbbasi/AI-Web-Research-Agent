from ai_web_research_agent.infrastructure.search import (
    parse_search_results,
)


def test_parse_search_results_unwraps_redirect_links():
    html = """
    <html><body>
      <a class="result__a"
         href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fp&rut=1">
        Example
      </a>
    </body></html>
    """

    urls = parse_search_results(html, limit=10)

    assert urls == ["https://example.com/p"]


def test_parse_search_results_accepts_plain_absolute_links():
    html = """
    <html><body>
      <a href="https://example.com/plain">Plain</a>
      <a href="/relative">Relative</a>
      <a href="mailto:x@y.z">Mail</a>
    </body></html>
    """

    urls = parse_search_results(html, limit=10)

    assert urls == ["https://example.com/plain"]


def test_parse_search_results_respects_limit():
    html = """
    <html><body>
      <a href="https://a.com">A</a>
      <a href="https://b.com">B</a>
      <a href="https://c.com">C</a>
    </body></html>
    """

    urls = parse_search_results(html, limit=2)

    assert urls == ["https://a.com", "https://b.com"]


def test_parse_search_results_deduplicates():
    html = """
    <html><body>
      <a href="https://a.com">A1</a>
      <a href="https://a.com">A2</a>
    </body></html>
    """

    urls = parse_search_results(html, limit=10)

    assert urls == ["https://a.com"]
