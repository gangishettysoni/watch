"""Scratch: determine zon's withholding trigger on a fresh container."""
import re
import time

from pricewatch.http import Client

BASE = "http://localhost:4000"
PID = "/stores/zon/dp/XM0GA7X1"


def has_price(t):
    return bool(re.search(r"\$\s*\d", t))


def get(c, url, **kw):
    r = c.get(url, **kw)
    return r


print("1. single cold product (fresh session)")
c = Client(min_interval=0.0)
r = get(c, BASE + PID)
print(f"   price={has_price(r.text)} len={len(r.text)}")
open(".scratch/pages/zon_cold1.txt", "w").write(r.text)

print("2. same session, product again immediately")
r = get(c, BASE + PID)
print(f"   price={has_price(r.text)}")

print("3. fresh session, index then product immediately")
c = Client(min_interval=0.0)
get(c, BASE + "/stores/zon/")
r = get(c, BASE + PID)
print(f"   price={has_price(r.text)}")

print("4. fresh session, product with 2.5s spacing x4")
c = Client(min_interval=0.0)
for i in range(4):
    r = get(c, BASE + PID)
    print(f"   {i}: price={has_price(r.text)}")
    time.sleep(2.5)

print("5. fresh session, product with 0.5s spacing x6")
c = Client(min_interval=0.0)
for i in range(6):
    r = get(c, BASE + PID)
    print(f"   {i}: price={has_price(r.text)}")
    time.sleep(0.5)

print("6. burst x8 no delay (fresh session)")
c = Client(min_interval=0.0)
for i in range(8):
    r = get(c, BASE + PID)
    print(f"   {i}: price={has_price(r.text)}")

print("7. cold single product again to check global state")
c = Client(min_interval=10.0)
time.sleep(10)
r = get(c, BASE + PID)
print(f"   price={has_price(r.text)}")
