"""Trend radar: collect what people are searching and asking about, and rank what-if topic ideas.

python -m whatif.trends --out trends/latest.md

Sources (all public, no login):
  - Google Trends daily trending searches RSS (Canada + US)
  - Reddit top posts of the week in r/hypotheticalsituation, r/AskReddit, r/NoStupidQuestions
  - Wikipedia's most-read English articles yesterday

The cloud container this was written in cannot reach these hosts, so it is meant to run
on GitHub Actions (see .github/workflows/trends.yml) or on your own computer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "clip-farm-trend-radar/0.1"}

# Premises that have worked for what-if channels for years. Trends get matched against these.
EVERGREEN = [
    "only had {n} days to live", "woke up 1,000 years in the future", "stopped sleeping", "the internet went down forever",
    "became a billionaire overnight", "were the last person on Earth", "could read minds", "fell into a black hole",
    "never aged", "lived on Mars", "swapped bodies with your pet", "had to survive in the wild",
]

HYPOTHETICAL = re.compile(r"\b(what if|what would|would you|if you could|imagine|you have|you wake up|you're given)\b", re.I)


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def google_trends(geo: str) -> list[dict]:
    xml = fetch(f"https://trends.google.com/trending/rss?geo={geo}")
    root = ET.fromstring(xml)
    ns = {"ht": "https://trends.google.com/trending/rss"}
    out = []
    for item in root.iter("item"):
        title = item.findtext("title", "")
        traffic = item.findtext("ht:approx_traffic", "0", ns)
        out.append({"source": f"google-{geo}", "title": title, "score": parse_traffic(traffic)})
    return out


def parse_traffic(s: str) -> int:
    """'200K+' -> 200000, '1M+' -> 1000000."""
    m = re.match(r"([\d.,]+)\s*([KM]?)", s.strip().upper())
    if not m:
        return 0
    n = float(m.group(1).replace(",", ""))
    return int(n * {"K": 1e3, "M": 1e6}.get(m.group(2), 1))


def reddit(sub: str) -> list[dict]:
    data = json.loads(fetch(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=40"))
    return [{"source": f"r/{sub}", "title": c["data"]["title"], "score": int(c["data"].get("score", 0))}
            for c in data["data"]["children"]]


def wikipedia(day: dt.date) -> list[dict]:
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{day:%Y/%m/%d}"
    arts = json.loads(fetch(url))["items"][0]["articles"]
    skip = ("Main_Page", "Special:", "Wikipedia:", "Portal:", "File:")
    return [{"source": "wikipedia", "title": a["article"].replace("_", " "), "score": int(a["views"])}
            for a in arts if not a["article"].startswith(skip)][:40]


def rank(items: list[dict]) -> list[dict]:
    """Score = popularity (log-scaled within each source) + a bonus for hypothetical phrasing."""
    import math

    by_src: dict[str, int] = {}
    for it in items:
        by_src[it["source"]] = max(by_src.get(it["source"], 1), it["score"] or 1)
    for it in items:
        pop = math.log1p(it["score"]) / math.log1p(by_src[it["source"]])
        it["hypothetical"] = bool(HYPOTHETICAL.search(it["title"]))
        it["rank"] = round(pop + (0.6 if it["hypothetical"] else 0), 3)
    return sorted(items, key=lambda x: x["rank"], reverse=True)


def to_markdown(items: list[dict], errors: list[str], when: dt.datetime) -> str:
    lines = [f"# Trend radar, {when:%Y-%m-%d %H:%M} UTC", "",
             "Hypothetical questions people are already asking come first; then what the world is searching.", ""]
    hyp = [i for i in items if i["hypothetical"]][:25]
    lines += ["## Questions people are asking", ""] + [f"- {i['title']} ({i['source']}, {i['score']:,})" for i in hyp]
    lines += ["", "## Trending searches and articles", ""]
    lines += [f"- {i['title']} ({i['source']}, {i['score']:,})" for i in items if not i["hypothetical"]][:40]
    lines += ["", "## Evergreen premises to pair with a trend", ""] + [f"- What if you {p}" for p in EVERGREEN]
    if errors:
        lines += ["", "## Sources that failed", ""] + [f"- {e}" for e in errors]
    return "\n".join(lines) + "\n"


def collect() -> tuple[list[dict], list[str]]:
    items, errors = [], []
    jobs = [("google CA", lambda: google_trends("CA")), ("google US", lambda: google_trends("US")),
            ("wikipedia", lambda: wikipedia(dt.date.today() - dt.timedelta(days=1)))]
    jobs += [(f"r/{s}", (lambda s=s: reddit(s))) for s in ("hypotheticalsituation", "AskReddit", "NoStupidQuestions")]
    for name, job in jobs:
        try:
            items += job()
        except Exception as e:  # one dead source should not kill the report
            errors.append(f"{name}: {e}")
    return items, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="trends/latest.md")
    a = ap.parse_args()
    items, errors = collect()
    md = to_markdown(rank(items), errors, dt.datetime.utcnow())
    import pathlib

    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(md)
    print(f"wrote {a.out}: {len(items)} items, {len(errors)} failed sources")


if __name__ == "__main__":
    main()
