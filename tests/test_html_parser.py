from ai_web_research_agent.infrastructure.html_parser import HTMLParser


def test_html_parser():
    html = """
    <html>
        <head>
            <title>Example Page</title>
            <script>
                console.log("ignore");
            </script>
        </head>

        <body>
            <h1>Hello</h1>
            <p>Research content.</p>
            <a href="/about">About</a>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        url="https://example.com/",
        status_code=200,
        html=html,
    )

    assert result.title == "Example Page"
    assert "Research content." in result.text
    assert "console.log" not in result.text

    assert len(result.links) == 1
    assert (
        result.links[0].url
        == "https://example.com/about"
    )