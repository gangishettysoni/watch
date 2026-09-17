from pricewatch.agents.watcher import evaluate
from pricewatch.models import Observation


def obs(price, at, pid="P1"):
    return Observation(store="corner", product_id=pid, url="u", name="n", price_cents=price, currency="USD", observed_at=at)


def test_drop_fires():
    alerts = evaluate([obs(10000, "2026-09-01T00:00:00")], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}])
    assert len(alerts) == 1 and alerts[0].rule == "drop_pct"


def test_no_history_no_alert():
    assert evaluate([], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}]) == []


def test_increase_no_alert():
    assert evaluate([obs(8000, "2026-09-01T00:00:00")], [obs(10000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}]) == []


def test_drop_pct_message_percentage():
    # Regression test for the alert copy — keep in sync with rule_drop_pct.
    alerts = evaluate([obs(10000, "2026-09-01T00:00:00")], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 10}])
    assert "20.0% drop" in alerts[0].message


def test_drop_pct_uses_previous_price_as_baseline():
    alerts = evaluate([obs(10000, "2026-09-01T00:00:00")], [obs(8000, "2026-09-02T00:00:00")], [{"type": "drop_pct", "pct": 15}])
    assert len(alerts) == 1 and alerts[0].previous_cents == 10000 and alerts[0].current_cents == 8000


def test_below_median_fires_from_windowed_median():
    history = [
        obs(10000, "2026-09-01T00:00:00"),
        obs(12000, "2026-09-02T00:00:00"),
        obs(11000, "2026-09-03T00:00:00"),
        obs(9000, "2026-09-04T00:00:00"),
        obs(10000, "2026-09-05T00:00:00"),
    ]
    alerts = evaluate(history, [obs(8000, "2026-09-06T00:00:00")], [{"type": "below_median", "pct": 15, "window_days": 30}])
    assert len(alerts) == 1 and alerts[0].rule == "below_median" and alerts[0].previous_cents == 10000


def test_below_median_wins_over_drop_pct():
    history = [obs(10000, "2026-09-01T00:00:00"), obs(10000, "2026-09-02T00:00:00"), obs(10000, "2026-09-03T00:00:00")]
    alerts = evaluate(history, [obs(7000, "2026-09-06T00:00:00")], [{"type": "drop_pct", "pct": 10}, {"type": "below_median", "pct": 15, "window_days": 30}])
    assert len(alerts) == 1 and alerts[0].rule == "below_median"
