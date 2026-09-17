"""Scratch: probe zon / shield / flux mechanisms."""
import hashlib
import re

from pricewatch.http import Client

BASE = "http://localhost:4000"


def show(label, r):
    print(f"-- {label}: status={r.status_code} len={len(r.text)} ct={r.headers.get('content-type')}")
    for k in ("set-cookie", "retry-after", "server", "x-powered-by"):
        if k in r.headers:
            print(f"     {k}: {r.headers[k]}")


c = Client(min_interval=0.0)

r = c.get(BASE + "/stores/zon/dp/XM0GA7X1")
show("zon product (direct)", r)
print("   cookies:", c.session.cookies.get_dict())
print("   dollar amounts:", re.findall(r"\$\s*([\d,]+)", r.text))

c2 = Client(min_interval=0.0)
show("zon index", c2.get(BASE + "/stores/zon/"))
print("   cookies after index:", c2.session.cookies.get_dict())

bundle = c.get(BASE + "/stores/flux/bundle.js").text
print("\n-- flux bundle:\n", bundle[:900])
array = re.search(r'\["([^"]*)","([^"]*)"\]', bundle)
sep = re.search(r"String\.fromCharCode\((\d+)\)", bundle)
print("   array:", array.groups() if array else None)
print("   sep:", sep.group(1) if sep else None)
secret = "".join(array.groups()) if array else ""
sepch = chr(int(sep.group(1))) if sep else "/"

for sku in ["FLX-3VP6UU", "FLX-05X99R"]:
    query = "query($sku:String!){product(sku:$sku){sku title offer{amount unit currency stock stale}}}"
    sig = hashlib.sha256(f"{secret}{sepch}{sku}".encode()).hexdigest()[:32]
    for label, headers in [
        ("no-sig", {"content-type": "application/json"}),
        ("sig32slash", {"content-type": "application/json", "x-flux-sig": sig, "x-flux-build": "b7228f8ad"}),
    ]:
        rr = c.post(BASE + "/stores/flux/api/graphql", json={"query": query, "variables": {"sku": sku}}, headers=headers)
        print(f"   flux {sku} {label}: {rr.status_code} {rr.text[:220]!r}")
