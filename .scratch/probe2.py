"""Scratch: probe zon's behaviour-based price withholding."""
import re
import time

from pricewatch.http import Client

BASE = "http://localhost:4000"
PID = "/stores/zon/dp/XM0GA7X1"


def has_price(text):
    return bool(re.search(r"\$\s*\d", text))


print("A: cold product x3 (clear cookie each time)")
c = Client(min_interval=0.0)
for i in range(3):
    r = c.get(BASE + PID)
    print(f"   hit{i}: {r.status_code} price={has_price(r.text)} cookies={list(c.session.cookies.get_dict())}")
    c.session.cookies.clear()

print("B: index then product")
c = Client(min_interval=0.0)
c.get(BASE + "/stores/zon/")
r = c.get(BASE + PID)
print(f"   {r.status_code} price={has_price(r.text)} cookies={list(c.session.cookies.get_dict())}")

print("C: product kept cookie, twice")
c = Client(min_interval=0.0)
r1 = c.get(BASE + PID)
r2 = c.get(BASE + PID)
print(f"   first price={has_price(r1.text)} second price={has_price(r2.text)}")

print("D: with Referer header")
c = Client(min_interval=0.0)
r = c.get(BASE + PID, headers={"Referer": BASE + "/stores/zon/"})
print(f"   {r.status_code} price={has_price(r.text)}")

print("E: empty UA")
c = Client(min_interval=0.0)
r = c.get(BASE + PID, headers={"User-Agent": ""})
r2 = c.get(BASE + PID, headers={"User-Agent": ""})
print(f"   first={has_price(r.text)} second={has_price(r2.text)}")

print("F: burst of 15 product fetches in one session")
c = Client(min_interval=0.0)
t0 = time.time()
for i in range(15):
    r = c.get(BASE + PID)
    print(f"   {i}: {r.status_code} price={has_price(r.text)} t={time.time()-t0:.2f}")
