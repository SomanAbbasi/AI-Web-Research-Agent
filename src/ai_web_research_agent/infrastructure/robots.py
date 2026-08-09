from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from ai_web_research_agent.infrastructure.http import HTTPClient


@dataclass(frozen=True)
class RobotsRule:
    """A single Allow/Disallow rule for a robots.txt group."""

    path: str
    allow: bool


class RobotsPolicy:
    """Determines whether a URL may be crawled based on robots.txt.

    Rules are grouped per user-agent. Groups are matched against the
    crawler's user agent with a specific group taking precedence over a
    wildcard group. Within a group the most specific (longest) rule wins,
    with Allow taking precedence on ties.
    """

    def __init__(
        self,
        http_client: HTTPClient,
        user_agent: str,
    ) -> None:
        self._http_client = http_client
        self._user_agent = user_agent
        self._groups: dict[str, dict[str, list[RobotsRule]]] = {}
        self._loaded: set[str] = set()

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)

        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin not in self._loaded:
            await self._load(origin)

        rules = self._select_group(origin)

        if not rules:
            return True

        matching = [rule for rule in rules if parsed.path.startswith(rule.path)]

        if not matching:
            return True

        best = max(
            matching,
            key=lambda rule: (len(rule.path), rule.allow),
        )

        return best.allow

    async def _load(self, origin: str) -> None:
        robots_url = f"{origin}/robots.txt"

        try:
            response = await self._http_client.get(robots_url)

            if response.status_code >= 400:
                self._groups[origin] = {}
                self._loaded.add(origin)
                return

            self._groups[origin] = self._parse(response.text)

        except httpx.HTTPError:
            # If robots.txt cannot be retrieved, fail open.
            self._groups[origin] = {}

        self._loaded.add(origin)

    def _select_group(self, origin: str) -> list[RobotsRule]:
        groups = self._groups.get(origin, {})

        user_agent_token = self._user_agent.split("/")[0].lower()

        for user_agent, rules in groups.items():
            if user_agent == "*":
                continue

            if user_agent_token.startswith(user_agent):
                return rules

        return groups.get("*", [])

    def _parse(self, content: str) -> dict[str, list[RobotsRule]]:
        groups: dict[str, list[RobotsRule]] = {}
        current_user_agents: list[str] = []
        current_rules: list[RobotsRule] = []

        def flush() -> None:
            if not current_rules:
                return

            for user_agent in current_user_agents:
                groups.setdefault(user_agent, []).extend(current_rules)

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            key, separator, value = line.partition(":")

            if not separator:
                continue

            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent" and value:
                if current_user_agents and current_rules:
                    flush()
                    current_rules = []

                current_user_agents.append(value.lower())
            elif key in {"allow", "disallow"} and current_user_agents and value:
                current_rules.append(
                    RobotsRule(
                        path=value,
                        allow=(key == "allow"),
                    )
                )

        flush()

        return groups
