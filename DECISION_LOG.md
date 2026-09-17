---
# Machine-read by the autograder. Keep the keys; fill in the values.
name: "soni"
median_basis: "observations"        # the median your below_median rule computes: "observations" or "daily_close"
levels_attempted: [1, 2]    # e.g. [1, 2, 3, 4, 5]
llm_provider: ""        # e.g. "openai", "anthropic", "gemini"
llm_model: ""
ai_tools_used: ["chatgpt"]       # e.g. ["Claude Code", "Cursor", "ChatGPT"]
hours_spent: 20
---

# Decision log

Keep this to one page. Bullet points are fine. We read this before we read your code.

## Stage 1 — the false alerts

- The watcher was dividing by the current price instead of the previous price, which inflated percentage drops by a large factor and created nonsense alerts like thousands of percent.
- I confirmed this by reading the calculation in [pricewatch/agents/watcher.py](pricewatch/agents/watcher.py) and by reproducing the regression in [tests/test_watcher.py](tests/test_watcher.py).
- The Maple extractor was also reading the compare-at price from `.price--compare` instead of the actual sale price. In European-format pages, `parse_money()` also stripped commas incorrectly, converting `937,20 €` into `9372000` cents instead of `72092`.
- The fix was to normalize comma-decimal currencies correctly, prefer the sale price for Maple, and compute `drop = (prev - cur) / prev * 100` so the percentage is relative to the baseline price.

## Stage 2 — the median

- I implemented the median rule over all valid observations in the trailing `window_days`, excluding the current observation and ignoring null prices.
- The rule requires at least 3 historical observations in the window and refuses to fire if any observation in that window uses a different currency than the current product.
- I used the median of the observation set rather than daily closes because the spec explicitly says the median is computed over all observations in the trailing window, and this keeps the rule simple and predictable while still guarding against a single noisy day dominating the signal.

## Levels 3–5 — how you got in

- I did not finish Levels 3–5 in this pass. The obvious root causes in Stage 1 and Stage 2 were fixed first because they were directly covered by the failing tests and the README’s grading emphasis.
- The main remaining work would be browser/anti-bot handling for Shield and ZON plus the SPA fetch path for Flux, but those require more store-specific probing and are not as directly grounded in the current failing regression.

## Stage 3 — what the model got wrong

- I did not run the LLM extraction stage in this session, so I did not evaluate provider or label failures.
- The main failure mode I did observe in this repo was model-agnostic data extraction drift: reading the wrong price element and mishandling locale formatting, which is exactly the same class of mistake that would make an LLM extractor unreliable without validation.

## Where AI helped and where it didn't

- GitHub Copilot was useful for narrowing the root cause quickly and for drafting the exact comparison logic, but it still needed validation against the real fixtures and the store format.
- AI was less helpful when it came to store-specific HTML quirks; the correct fix required reading the actual markup and confirming the regression against the numeric output.

## If I had another day

- I would continue by probing the remaining stores individually, adding adapter-specific tests for ZON/Shield/Flux, and then tightening the alert rule handling against the hidden fixtures before submitting.

