"""Scratch: summarise observations by store."""
import json
import sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else ".scratch/run1.jsonl"
rows = [json.loads(l) for l in open(path) if l.strip()]
by = defaultdict(list)
for r in rows:
    by[r["store"]].append(r)

for store, obs in sorted(by.items()):
    print(f"== {store}: {len(obs)} observations")
    for o in obs[:60]:
        print(f"   {o['product_id']:<28} {str(o['price_cents']):>10} {o['currency']:<4} {o['availability']:<12} "
              f"pack={o['pack_size']} cmp={o['compare_at_cents']} name={o['name'][:40]!r} notes={o['notes']}")
