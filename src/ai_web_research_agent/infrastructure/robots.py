from urllib.parse import urlparse

import httpx

from ai_web_research_agent.infrastructure.http import HTTPClient


class RobotsPolicy:
    """Determines whether a URL may be crawled."""

    def __init__(
        self,
        http_client: HTTPClient,
        user_agent: str,
    ) -> None:
        self._http_client = http_client
        self._user_agent = user_agent
        self._rules: dict[str, list[str]] = {}
        self._loaded: set[str] = set()

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)

        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin not in self._loaded:
            await self._load(origin)

        rules = self._rules.get(origin, [])

        return not any(
            self._matches_rule(
                parsed.path,
                rule,
            )
            for rule in rules
        )

    async def _load(self, origin: str) -> None:
        robots_url = f"{origin}/robots.txt"

        try:
            response = await self._http_client.get(robots_url)

            if response.status_code >= 400:
                self._rules[origin] = []
                self._loaded.add(origin)
                return

            rules = self._parse(response.text)

            self._rules[origin] = rules

        except httpx.HTTPError:
            # If robots.txt cannot be retrieved,
            # fail open for this initial crawler version.
            self._rules[origin] = []

        self._loaded.add(origin)

    def _parse(
        self,
        content: str,
    ) -> list[str]:
        rules: list[str] = []
        applies = False

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            key, separator, value = line.partition(":")

            if not separator:
                continue

            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                applies = value == "*"

            elif key == "disallow" and applies and value:
                rules.append(value)

        return rules

    @staticmethod
    def _matches_rule(
        path: str,
        rule: str,
    ) -> bool:
        return path.startswith(rule)
