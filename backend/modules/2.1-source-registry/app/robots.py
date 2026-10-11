from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "HackathonRadarFinder/1.0"


def check_robots_txt(base_url: str) -> tuple[bool, str]:
    try:
        parsed_url = urlparse(base_url)

        robots_url = (
            f"{parsed_url.scheme}://"
            f"{parsed_url.netloc}/robots.txt"
        )

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.read()

        allowed = parser.can_fetch(
            USER_AGENT,
            base_url
        )

        if allowed:
            return True, "allowed"

        return False, "disallowed"

    except Exception:
        return False, "unreachable"