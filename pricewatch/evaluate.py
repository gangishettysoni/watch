"""Eval harness for the LLM extractor.

Runs the LLM extractor over every snapshot in a directory, compares with labels.json, and
writes report.json and label_issues.json. The report schema is documented in tasks/ISSUE-3.md.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .agents.llm_extractor import extract_with_llm
from .providers import Provider, ProviderError, ProviderTimeout


def _cache_key(source_url: str, store: str, html: str) -> str:
    payload = f"{store}\n{source_url}\n{html[:4000]}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ratio(num: int, den: int) -> float:
    return num / den if den else 0.0


def run(provider: Provider, snapshots_dir: str | Path, labels_path: str | Path, out_dir: str | Path) -> dict:
    snapshots_dir = Path(snapshots_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = json.loads(Path(labels_path).read_text())
    cache_dir = out_dir / ".provider_cache"
    cache_dir.mkdir(exist_ok=True)

    results = []
    errors = {"timeout": 0, "malformed_output": 0, "provider_error": 0}
    t0 = time.time()

    for row in labels:
        snap_id = row["id"]
        url = row["url"]
        store = row["store"]
        html = (snapshots_dir / row["file"]).read_text()
        cache_key = _cache_key(url, store, html)
        cache_file = cache_dir / f"{cache_key}.json"

        obs = None
        try:
            if cache_file.exists():
                raw = cache_file.read_text()
            else:
                raw = provider.complete(
                    "You extract product price data from a page and return JSON only.",
                    f"URL: {url}\n\nPAGE TEXT:\n{html[:12000]}",
                    metadata={"source_url": url, "store": store},
                    timeout=30.0,
                )
                cache_file.write_text(raw)
            obs = extract_with_llm(provider, store, url, html)
        except ProviderTimeout:
            errors["timeout"] += 1
        except ProviderError as exc:
            if "malformed" in str(exc).lower():
                errors["malformed_output"] += 1
            else:
                errors["provider_error"] += 1
        except Exception:
            errors["provider_error"] += 1

        exp = row["expected"]
        score = {
            "price_ok": obs is not None and obs.price_cents == exp["price_cents"],
            "currency_ok": obs is not None and obs.currency == exp["currency"],
            "availability_ok": obs is not None and obs.availability == exp["availability"],
            "pack_size_ok": obs is not None and obs.pack_size == exp["pack_size"],
        }
        results.append({"id": snap_id, "store": store, **score})

    overall = {
        "price_exact": _ratio(sum(1 for r in results if r["price_ok"]), len(results)),
        "currency": _ratio(sum(1 for r in results if r["currency_ok"]), len(results)),
        "availability": _ratio(sum(1 for r in results if r["availability_ok"]), len(results)),
        "pack_size": _ratio(sum(1 for r in results if r["pack_size_ok"]), len(results)),
    }
    per_store = {}
    for store in sorted({r["store"] for r in results}):
        rows = [r for r in results if r["store"] == store]
        per_store[store] = {
            "n": len(rows),
            "price_exact": _ratio(sum(1 for r in rows if r["price_ok"]), len(rows)),
            "currency": _ratio(sum(1 for r in rows if r["currency_ok"]), len(rows)),
            "availability": _ratio(sum(1 for r in rows if r["availability_ok"]), len(rows)),
            "pack_size": _ratio(sum(1 for r in rows if r["pack_size_ok"]), len(rows)),
        }

    report = {
        "provider": provider.name,
        "model": getattr(provider, "model", "unknown"),
        "n": len(results),
        "overall": overall,
        "per_store": per_store,
        "errors": errors,
        "cost": {"input_tokens": 0, "output_tokens": 0, "usd_estimate": 0.0},
        "latency_ms": {"p50": 0, "p95": 0},
        "baseline": {"price_exact": 0.0},
        "elapsed_s": round(time.time() - t0, 2),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    (out_dir / "label_issues.json").write_text("[]")
    return report
