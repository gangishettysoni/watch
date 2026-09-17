"""Scratch: fetch every zon product page from its index and print the body."""
import re

from bs4 import BeautifulSoup

from pricewatch.http import Client

BASE = "http://localhost:4000"
c = Client(min_interval=0.0)
idx = c.get(BASE + "/stores/zon/").text
links = list(dict.fromkeys(re.findall(r'href="(/stores/zon/dp/[^"]+)"', idx)))
print("products:", len(links))
for link in links:
    r = c.get(BASE + link)
    soup = BeautifulSoup(r.text, "html.parser")
    body = soup.body
    for t in body(["style"]):
        t.decompose()
    text = re.sub(r"\n\s*\n+", "\n", body.decode_contents())
    print("\n" + "=" * 90)
    print("URL:", link, "status:", r.status_code)
