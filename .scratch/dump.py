"""Scratch: dump a URL's raw text (utf-8) and show the region around a marker."""
import sys

from pricewatch.http import Client

url = sys.argv[1]
marker = sys.argv[2] if len(sys.argv) > 2 else None
c = Client(min_interval=0.0)
r = c.get(url)
text = r.text
print(f"status={r.status_code} len={len(text)}")
if marker and marker in text:
    i = text.index(marker)
    print(text[max(0, i - 200): i + 900])
else:
    print(text[:3000])
