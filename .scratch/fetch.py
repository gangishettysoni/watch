"""Scratch: fetch a URL with the project Client and save raw text; also list script/link refs."""
import sys
from pathlib import Path

from pricewatch.http import Client
from bs4 import BeautifulSoup

urls = sys.argv[1:]
c = Client(min_interval=0.0)
outdir = Path(".scratch/pages")
outdir.mkdir(parents=True, exist_ok=True)

for url in urls:
    r = c.get(url)
    safe = url.replace("://", "_").replace("/", "_").replace("?", "_").replace(":", "_")
    p = outdir / (safe[:120] + ".txt")
    p.write_text(r.text, encoding="utf-8")
    print(f"== {url}\n   status={r.status_code} len={len(r.text)} ct={r.headers.get('content-type')} -> {p}")
    if "html" in (r.headers.get("content-type") or ""):
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup.find_all("script", src=True):
            print("   script:", s["src"])
        for meta in soup.find_all("meta"):
            if meta.get("name") or meta.get("http-equiv"):
                print(f"   meta: {meta.get('name') or meta.get('http-equiv')} = {meta.get('content')}")
