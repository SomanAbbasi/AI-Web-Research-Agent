
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class RobotsPolicy:
    def __init__(self, user_agent: str) -> None:
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser] = {}

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)

        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        parser = self._parsers.get(robots_url)

        if parser is None:
            parser = RobotFileParser(robots_url)
            parser.read()
            self._parsers[robots_url] = parser

        return parser.can_fetch(self._user_agent, url)