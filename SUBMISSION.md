# Submitting your work

## Checklist before your first submission

- [ ] `pytest` passes locally.
- [ ] `pricewatch scan --stores-url http://localhost:4000 --out obs.jsonl` runs to completion
      without a traceback, against a stores instance started with a seed you chose yourself:
      `docker run --rm -p 4000:4000 -e STORE_SEED=mytest ghcr.io/i95dev/pricewatch-stores:latest`.
      Compare `obs.jsonl` against `curl "http://localhost:4000/grader-truth?key=dev-truth-key"` for
      levels 1–2, and against what a browser shows you for levels 3–5 (see `STORES.md`).
- [ ] `pricewatch watch --history <file> --new <file>` runs with your `alerts.yaml`.
- [ ] `pricewatch eval --provider echo --out eval/out` runs without a key and writes both files.
- [ ] `eval/out/` from your real-key run is committed.
- [ ] The `DECISION_LOG.md` frontmatter is filled in.
- [ ] `pip install -e .` works from a clean clone. If you added dependencies, they're in `pyproject.toml`.
      (TypeScript port: `npm ci && npm run build` must work, and `npx pricewatch …` must expose the same CLI.)
- [ ] No API keys in the repository. The grader does not have your key and does not need it.

## How to submit

1. Push your work to a **private** GitHub repository with any name. Keep the history — we like
   seeing how you got there.
2. Install the **PriceWatch Grader** GitHub App on that repository:
   **https://github.com/apps/pricewatch-grader/installations/new** → *Only select
   repositories* → choose your submission repository. It requests read-only access to
   repository contents and nothing else, and you can uninstall it once you hear back from us.
3. Open the submission form: **https://pricewatch-submit.vercel.app**. Enter your email (the one
   we contacted you on), the repository URL, and optionally a commit SHA (default: HEAD of the
   default branch).
4. Confirm the link we email you. Within about 15 minutes of confirming you'll receive your score
   card: points per section, per-store extraction results, and a note on any step that failed or
   timed out. The score card does not reveal hidden test data.

You may submit **three times**. The **last** submission is the one that counts, and the one
we review by hand. Attempts are logged with timestamps.

## How grading works

1. Clones your repository at the given commit into a clean Linux environment (Python 3.11,
   Node 20) and runs `pip install -e .` (or `npm ci && npm run build`).
2. Starts the test stores locally with a **secret seed**.
3. **Stage 1 / Levels:** runs `pricewatch scan --stores-url … --out obs.jsonl` twice, a few
   seconds apart, then `pricewatch watch --history run1 --new run2`. Scores each store's
   prices against ground truth, and scores "no false alerts". Checks the store logs for
   `robots.txt` violations and ignored `Retry-After`s (penalty).
4. **Stage 2:** runs `pricewatch watch` with our history fixtures and a rules file containing
   `below_median`, and compares the result with the expected alerts for the `median_basis`
   declared in `DECISION_LOG.md`.
5. **Stage 3:** runs `pricewatch eval` with `PRICEWATCH_PROVIDER_PATH` set to our stub
   provider. The stub answers deterministically from `metadata["source_url"]`, and it will
   time out on some snapshots and return non-JSON on others. Checks that the harness survives,
   that `report.json` has the required keys with sane values, and scores
   `label_issues.json` against our answer key. Then runs `pricewatch extract --llm --provider anthropic`
   with our Anthropic key on 40 product pages from two stores you have never seen, and scores
   what it prints against ground truth (ISSUE-3 Part C). The key is spend-capped and rotated.
   Read it only from the `ANTHROPIC_API_KEY` environment variable, and never log, print, or
   store it.
6. Emails you the score card and records the score.

Each step has a time limit: scan 4 minutes; watch 30 seconds; eval 3 minutes; `extract` on a
Part C page 60 seconds. A step that runs over its limit scores zero, so respect the rate limits
rather than fighting them.

## Common ways to lose points

- Renaming a CLI flag. The grader can't find it, and the whole step scores zero.
- Hard-coding anything you observed under the public seed — markup, class names, or store
  behaviour. It changes with the seed.
- Hammering a store until it rate-limits you, then giving up. Slow down; the response tells you how long.
- An eval harness that stops at the first provider error. Most of Stage 3's automatic points
  depend on the harness running to completion.
- An LLM extractor tuned only to the two eval stores. Part C uses stores that do not appear
  anywhere in this repository.
- Leaving the `DECISION_LOG.md` frontmatter blank. The grader reads it.
- Listing every snapshot in `label_issues.json`. That scores zero by design.
