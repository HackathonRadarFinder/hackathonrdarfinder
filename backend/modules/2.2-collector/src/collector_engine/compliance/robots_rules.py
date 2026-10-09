"""robots.txt rule parsing and matching (RFC 9309 style).

Python's urllib.robotparser ignores '*' wildcards and '$' anchors, so a rule such as
`Disallow: /competitions/*/register` would be treated as a literal path and wrongly allow the
page. This module implements the matching properly: the longest matching rule wins, and Allow
wins a tie.
"""
from __future__ import annotations

import re
from typing import NamedTuple


class Rule(NamedTuple):
    allow: bool
    pattern: str
    regex: "re.Pattern[str]"


def _compile(pattern: str) -> "re.Pattern[str]":
    anchored = pattern.endswith("$")
    body = re.escape(pattern[:-1] if anchored else pattern).replace(r"\*", ".*")
    return re.compile("^" + body + ("$" if anchored else ""))


def parse_robots(text: str, user_agent: str) -> list[Rule]:
    """Rules that apply to `user_agent`: its own group if present, otherwise the '*' group."""
    token = user_agent.split("/")[0].strip().lower()
    groups: dict[str, list[tuple[bool, str]]] = {}
    current: list[str] = []
    last_was_agent = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        field, value = (p.strip() for p in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if not last_was_agent:  # a new group starts after any rule line
                current = []
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
            last_was_agent = True
        elif field in ("allow", "disallow"):
            last_was_agent = False
            if value:  # empty "Disallow:" means allow everything - nothing to record
                for agent in current:
                    groups[agent].append((field == "allow", value))
        else:
            last_was_agent = False
    chosen = groups[token] if token in groups else groups.get("*", [])
    return [Rule(allow, pattern, _compile(pattern)) for allow, pattern in chosen]


def is_allowed(rules: list[Rule], path_and_query: str) -> bool:
    """True if the path (plus ?query, if any) may be fetched under these rules."""
    matches = [(len(r.pattern), r.allow) for r in rules if r.regex.match(path_and_query)]
    if not matches:
        return True
    best = max(length for length, _ in matches)
    return any(allow for length, allow in matches if length == best)
