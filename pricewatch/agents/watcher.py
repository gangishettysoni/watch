"""Watcher agent: compares new observations against history and raises alerts.

History is a list of observations ordered by `observed_at`. Rules come from alerts.yaml.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Iterable

from ..models import Alert, Observation


def _key(o: Observation) -> tuple[str, str]:
    return (o.store, o.product_id)


def _by_product(history: Iterable[Observation]) -> dict[tuple[str, str], list[Observation]]:
    out: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    for o in history:
        out[_key(o)].append(o)
    for v in out.values():
        v.sort(key=lambda o: o.observed_at)
    return out


def _seen_at(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def rule_drop_pct(prev: Observation, cur: Observation, pct: float) -> Alert | None:
    if prev.price_cents is None or cur.price_cents is None:
        return None
    if cur.price_cents >= prev.price_cents:
        return None
    drop = (prev.price_cents - cur.price_cents) / prev.price_cents * 100
    if drop >= pct:
        return Alert(store=cur.store, product_id=cur.product_id, rule="drop_pct",
                     message=f"{cur.name or cur.product_id}: {prev.price_cents} -> {cur.price_cents} ({drop:.1f}% drop)",
                     previous_cents=prev.price_cents, current_cents=cur.price_cents, observed_at=cur.observed_at)
    return None


def rule_below_median(history: list[Observation], cur: Observation, pct: float, window_days: float) -> Alert | None:
    if cur.price_cents is None:
        return None

    cutoff = _seen_at(cur.observed_at) - timedelta(days=window_days)
    window: list[Observation] = []
    for o in history:
        if o.price_cents is None:
            continue
        if o.observed_at >= cur.observed_at:
            continue
        if _seen_at(o.observed_at) < cutoff:
            continue
        if o.currency != cur.currency:
            cur.notes.append("currency changed in below_median window")
            return None
        window.append(o)

    if len(window) < 3:
        return None

    med = median(o.price_cents for o in window)
    floor = med * (1 - pct / 100)
    if cur.price_cents > floor:
        return None

    med_cents = int(round(med))
    return Alert(
        store=cur.store,
        product_id=cur.product_id,
        rule="below_median",
        message=f"{cur.name or cur.product_id}: median {med_cents} -> {cur.price_cents} ({((med_cents - cur.price_cents) / med_cents * 100 if med_cents else 0):.1f}% below median)",
        previous_cents=med_cents,
        current_cents=cur.price_cents,
        observed_at=cur.observed_at,
    )


def evaluate(history: list[Observation], new: list[Observation], rules: list[dict]) -> list[Alert]:
    """Evaluate `rules` for each observation in `new` against `history` (which must not include `new`)."""
    alerts: list[Alert] = []
    hist = _by_product(history)
    for cur in sorted(new, key=lambda o: o.observed_at):
        prior = hist.get(_key(cur), [])
        prev = prior[-1] if prior else None
        chosen: Alert | None = None

        for rule in rules:
            rule_type = rule.get("type")
            if rule_type == "below_median":
                a = rule_below_median(prior, cur, float(rule.get("pct", 15)), float(rule.get("window_days", 30)))
                if a is not None:
                    chosen = a
                    break
            elif rule_type == "drop_pct" and prev is not None:
                a = rule_drop_pct(prev, cur, float(rule.get("pct", 10)))
                if a is not None and chosen is None:
                    chosen = a

        if chosen:
            alerts.append(chosen)
        hist[_key(cur)] = prior + [cur]
    return alerts
