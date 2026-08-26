#!/usr/bin/env python3
"""Render assets/stats.svg from live GitHub contribution data.

Replaces third-party stat-card services, which time out often enough that
GitHub's image proxy caches the failure and the README shows a broken image.
Run by .github/workflows/stats.yml; needs GH_TOKEN (or GITHUB_TOKEN) in env.
"""
import json, os, sys, urllib.request
from datetime import date, datetime, timedelta

USER = os.environ.get("GH_USER", "nishchithkulal")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "stats.svg")

C = dict(base="#1e1e2e", mantle="#181825", s0="#313244", ov0="#6c7086", sub0="#a6adc8",
         text="#cdd6f4", mauve="#cba6f7", blue="#89b4fa", green="#a6e3a1",
         peach="#fab387", teal="#94e2d5")
RAMP = ["#232334", "#38406b", "#5a6cae", "#89b4fa", "#cba6f7"]
MONO = ("'JetBrains Mono','Fira Code','SFMono-Regular',ui-monospace,"
        "'DejaVu Sans Mono',monospace")

QUERY = """
{ user(login:"%s") { contributionsCollection {
    totalCommitContributions totalRepositoriesWithContributedCommits
    contributionCalendar { totalContributions
      weeks { contributionDays { date contributionCount weekday } } } } } }
"""


def fetch():
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        sys.exit("GH_TOKEN/GITHUB_TOKEN not set")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY % USER}).encode(),
        headers={"Authorization": f"bearer {tok}", "Content-Type": "application/json",
                 "User-Agent": USER})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if "errors" in d:
        sys.exit(f"GraphQL: {d['errors']}")
    return d["data"]["user"]["contributionsCollection"]


def streaks(days):
    """Current and longest run of consecutive days with >=1 contribution.

    Today counts only if it already has activity; an empty today does not break
    a streak that ran through yesterday.
    """
    today = date.today()
    cur = best = run = 0
    prev = None
    for d in days:
        day = datetime.strptime(d["date"], "%Y-%m-%d").date()
        if day > today:
            break
        if d["contributionCount"] > 0:
            run = run + 1 if prev and day - prev == timedelta(days=1) else 1
            best = max(best, run)
            prev = day
        else:
            if day < today:          # an empty past day ends the run
                run, prev = 0, None
    if prev and today - prev <= timedelta(days=1):
        cur = run
    return cur, best


def level(n, qs):
    if n <= 0:
        return 0
    for i, q in enumerate(qs):
        if n <= q:
            return i + 1
    return 4


def main():
    c = fetch()
    cal = c["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    nz = sorted(d["contributionCount"] for d in days if d["contributionCount"] > 0)
    qs = [nz[int(len(nz) * f)] for f in (0.25, 0.55, 0.80)] if nz else [1, 2, 3]
    cur, best = streaks(days)
    active = len(nz)

    W, CELL, GAP = 880, 13, 2.7
    PITCH = CELL + GAP
    GX, GY = 24, 150
    H = 300
    e = []
    a = e.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="{cal["totalContributions"]} contributions in the last year">')
    a(f'<defs><style>text{{font-family:{MONO}}}</style></defs>')
    a(f'<rect width="{W}" height="{H}" rx="12" fill="{C["base"]}"/>'
      f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="11.5" fill="none" '
      f'stroke="{C["s0"]}"/>')
    a(f'<path transform="translate(24,26)" d="M0 0 L5 4.5 L0 9" fill="none" '
      f'stroke="{C["green"]}" stroke-width="1.7" stroke-linecap="round" '
      f'stroke-linejoin="round"/>')
    a(f'<text x="40" y="34" font-size="12.5" fill="{C["text"]}">'
      f'git log --all --since=1.year</text>')
    a(f'<rect x="24" y="48" width="{W-48}" height="1" fill="{C["s0"]}"/>')

    tiles = [(f'{cal["totalContributions"]:,}', "contributions", "mauve"),
             (f'{cur}', "day streak", "peach"),
             (f'{best}', "longest streak", "green"),
             (f'{c["totalRepositoriesWithContributedCommits"]}', "repos touched", "blue")]
    tw, tg = 200, 12
    for i, (num, lab, col) in enumerate(tiles):
        x = 24 + i * (tw + tg)
        a(f'<rect x="{x}" y="64" width="{tw}" height="56" rx="8" fill="{C["mantle"]}" '
          f'stroke="{C["s0"]}"/>')
        a(f'<text x="{x+16}" y="94" font-size="21" font-weight="700" '
          f'fill="{C[col]}">{num}</text>')
        a(f'<text x="{x+16}" y="110" font-size="10" fill="{C["ov0"]}">{lab}</text>')

    seen = set()
    for wi, w in enumerate(weeks):
        m = datetime.strptime(w["contributionDays"][0]["date"], "%Y-%m-%d").strftime("%b")
        if m not in seen and wi < len(weeks) - 1:
            seen.add(m)
            a(f'<text x="{GX + wi*PITCH:.1f}" y="{GY-8}" font-size="9.5" '
              f'fill="{C["ov0"]}">{m}</text>')
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            x = GX + wi * PITCH
            y = GY + d["weekday"] * PITCH
            a(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="3" '
              f'fill="{RAMP[level(d["contributionCount"], qs)]}">'
              f'<title>{d["contributionCount"]} on {d["date"]}</title></rect>')

    ly = GY + 7 * PITCH + 18
    a(f'<text x="{GX}" y="{ly}" font-size="10" fill="{C["ov0"]}">'
      f'{active} active days</text>')
    lx = W - 24 - (5 * 16 + 74)
    a(f'<text x="{lx}" y="{ly}" font-size="10" fill="{C["ov0"]}">Less</text>')
    for i, col in enumerate(RAMP):
        a(f'<rect x="{lx + 32 + i*16}" y="{ly-9}" width="11" height="11" rx="3" '
          f'fill="{col}"/>')
    a(f'<text x="{lx + 32 + 5*16 + 4}" y="{ly}" font-size="10" '
      f'fill="{C["ov0"]}">More</text>')
    a('</svg>')

    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(e))
    print(f"stats.svg: {cal['totalContributions']} contributions, "
          f"streak {cur} (best {best}), {active} active days")


if __name__ == "__main__":
    main()
