"""Rewrites the live section of README.md from real GitHub data. Run daily by update-readme.yml."""
import datetime
import json
import os
import re
import urllib.request

USER = "Pushkraj-Space"
TOKEN = os.environ["GITHUB_TOKEN"]
README = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")


def api(path, body=None):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main():
    repos = [r for r in api(f"/users/{USER}/repos?per_page=100&type=owner")
             if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()]
    year = api("/graphql", {"query": f'{{ user(login: "{USER}") {{ contributionsCollection '
                                     f'{{ contributionCalendar {{ totalContributions }} }} }} }}'})
    total = year["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    langs = {}
    for r in repos:
        for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[lang] = langs.get(lang, 0) + n
    all_bytes = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:8]

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "```text",
        f"C:\\PUSHKRAJ> stats",
        "",
        f"  Contributions (last 12 months) ... {total:,}",
        f"  Public repositories .............. {len(repos)}",
        "",
        "  Languages across my public repos",
    ]
    for lang, n in top:
        pct = n * 100 / all_bytes
        bar = "█" * round(pct / 5) + "░" * (20 - round(pct / 5))
        lines.append(f"  {lang:<14} {bar} {pct:5.1f}%")
    lines += ["", f"  Last refreshed {now}", "```", "", "**Recently pushed**", "",
              "| Repo | Language | Last push |", "|---|---|---|"]
    for r in sorted(repos, key=lambda r: r["pushed_at"], reverse=True)[:5]:
        lines.append(f"| [{r['name']}]({r['html_url']}) | {r['language'] or '-'} | {r['pushed_at'][:10]} |")

    with open(README, encoding="utf-8") as f:
        text = f.read()
    block = "<!--LIVE:START-->\n" + "\n".join(lines) + "\n<!--LIVE:END-->"
    text = re.sub(r"<!--LIVE:START-->.*?<!--LIVE:END-->", lambda _: block, text, flags=re.S)
    with open(README, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
