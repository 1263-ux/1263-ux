"""Generate the profile's weekly GitHub activity SVG without third-party packages."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


LOGIN = "1263-ux"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "weekly-pulse.svg"


def github_request(url: str, *, payload: dict | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "1263-ux-profile-weekly-pulse",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(payload).encode("utf-8") if payload else None
    if payload:
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - GitHub API URL is constant.
        return json.load(response)


def collect_stats() -> tuple[int, int, int, str]:
    now = datetime.now(UTC)
    since = now - timedelta(days=7)
    query = """
      query($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
          contributionsCollection(from: $from, to: $to) {
            contributionCalendar { totalContributions }
          }
        }
      }
    """
    graph = github_request(
        "https://api.github.com/graphql",
        payload={
            "query": query,
            "variables": {"login": LOGIN, "from": since.isoformat(), "to": now.isoformat()},
        },
    )
    contributions = graph["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    events = github_request(f"https://api.github.com/users/{LOGIN}/events?per_page=100")
    public_pushes = [
        event
        for event in events
        if event["type"] == "PushEvent" and datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")) >= since
    ]
    repositories = {event["repo"]["name"] for event in public_pushes}
    return contributions, len(repositories), len(public_pushes), now.strftime("%Y-%m-%d %H:%M UTC")


def render_svg(contributions: int, repositories: int, pushes: int, updated_at: str) -> str:
    cells = (("本周贡献", contributions, "次"), ("活跃仓库", repositories, "个"), ("公开推送", pushes, "次"))
    blocks = []
    for index, (label, value, suffix) in enumerate(cells):
        x = 36 + index * 336
        divider = "" if index == 0 else f'<line x1="{x}" y1="28" x2="{x}" y2="132" stroke="#D8E4FA" opacity=".42" />'
        blocks.append(
            f'''{divider}
            <text x="{x + 26}" y="59" fill="#64748B" font-family="Segoe UI, Microsoft YaHei, sans-serif" font-size="14">{label}</text>
            <text x="{x + 26}" y="105" fill="#13264A" font-family="Georgia, Noto Serif SC, serif" font-size="38">{value}</text>
            <text x="{x + 78}" y="103" fill="#B17A14" font-family="Segoe UI, Microsoft YaHei, sans-serif" font-size="14">{suffix}</text>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="160" viewBox="0 0 1080 160" role="img" aria-label="近 7 天 GitHub 公开活动">
  <rect width="1080" height="160" fill="#FCF8EE" rx="12" />
  <rect x="0.5" y="0.5" width="1079" height="159" fill="none" stroke="#DDD3BF" rx="11.5" />
  <text x="36" y="22" fill="#64748B" font-family="Cascadia Code, Consolas, monospace" font-size="11" letter-spacing="1.5">WEEKLY PULSE / GITHUB ACTIVITY</text>
{''.join(blocks).lstrip()}
  <line x1="36" y1="132" x2="1044" y2="132" stroke="#DDD3BF" />
  <circle cx="42" cy="147" r="4" fill="#D5A82C" />
  <text x="54" y="151" fill="#718096" font-family="Cascadia Code, Consolas, monospace" font-size="11">自动同步 · {updated_at}</text>
</svg>'''


def main() -> None:
    contributions, repositories, pushes, updated_at = collect_stats()
    OUTPUT.write_text(render_svg(contributions, repositories, pushes, updated_at), encoding="utf-8")


if __name__ == "__main__":
    main()
