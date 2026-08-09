from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ai_web_research_agent.domain.crawling import PageContent, PageLink


class HTMLParser:
    def parse(
        self,
        url: str,
        status_code: int,
        html: str,
    ) -> PageContent:
        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else None

        for element in soup(
            [
                "script",
                "style",
                "noscript",
            ]
        ):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True,
        )

        links: list[PageLink] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")

            if not isinstance(href, str):
                continue

            absolute_url = urljoin(url, href)

            text_content = anchor.get_text(
                " ",
                strip=True,
            )

            links.append(
                PageLink(
                    url=absolute_url,
                    text=text_content,
                )
            )

        return PageContent(
            url=url,
            status_code=status_code,
            title=title,
            text=text,
            links=links,
        )