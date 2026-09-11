# PriceWatch test stores

Five mock storefronts, ranging from straightforward to difficult. Each one reproduces a kind of
friction real e-commerce sites put in front of automated clients. None of it is a real anti-bot
product, and nothing requires solving a CAPTCHA — everything a normal browser needs to show you
a price is in what the server sends. Your job is to notice what a browser does that your code
doesn't.

## Running the stores

**Locally** (recommended for full scans, and for testing against a seed of your own):

```bash
docker run --rm -p 4000:4000 -e STORE_SEED=mytest ghcr.io/i95dev/pricewatch-stores:latest
# http://localhost:4000
```

**Hosted** (public seed): https://pricewatch-stores.vercel.app — suitable for light development;
please stay under a few requests per second. The hosted instance runs on serverless
infrastructure, so some behaviour can differ from the container. Do your final testing against
the container.

`STORE_SEED` changes the whole catalogue *and* some of the store behaviour. The grader runs with
a seed you have never seen, so anything hard-coded from the public seed will not transfer.

## Checking your results

```bash
curl "http://localhost:4000/grader-truth?key=dev-truth-key"
```

returns the expected product data for **levels 1 and 2** under whatever seed the container is
running, so you can check the basics of your extractor against any seed. There is no equivalent
for levels 3–5: verify those the way you would on a real website — open the page in a browser
and compare.

## The five stores — symptoms, not mechanisms

| Level | Store | Path | What you'll notice |
|---|---|---|---|
| 1 | Corner Store | `/stores/corner/` | Nothing. Plain, well-structured HTML. Your sanity check. |
| 2 | Maple & Co | `/stores/maple/` | Looks like a Shopify store and has some of the things Shopify stores have. Prices are printed the European way. Sale items show two prices, but not always. Products have variants, and the one the page shows you first is not always the first one in any list. |
| 3 | Zon | `/stores/zon/` | A marketplace. Prices are in pieces. Nothing in the markup is stable between deployments. Several prices appear on a page and only one is the price. Some items make you pick a variant first; some have no price at all. Zon is suspicious of clients that don't behave like a browser — in what they send *and in what they do* — and it doesn't tell you when it has decided you're a bot; it just stops showing you prices. Its `robots.txt` means what it says. |
| 4 | Shield Outfitters | `/stores/shield/` | You can't get in at first. A browser can, after a moment. Once you're in, you're not in forever, and you're not in from everywhere. The store objects if you're fast. The price is on the page, but you won't find it with a text search. |
| 5 | Flux | `/stores/flux/` | A single-page app. The HTML has no prices. The browser gets them from an API that only talks to the app's own JavaScript — and what it means by "amount" isn't the same for every product. The layout isn't the same on every load, the API isn't up on every call, and prices genuinely change over the day. Some items are out of stock but still quote a number. |

All stores publish `/robots.txt`. The grader checks that you respect it and any `Retry-After`
you are given.

## Ground rules

- Treat the stores as a black box. Work only from what they serve over HTTP, as you would with
  a real website. Extracting, decompiling, or otherwise inspecting the container image is out
  of scope.
- The stores exist only for this assignment. Do not point PriceWatch at any real website.

## Tips

- Open every store in a real browser with DevTools' Network tab open before writing any code.
- If a page "works in the browser but not in my script", the answer is in the difference between the two.
- When a mechanism is in JavaScript, running that JavaScript is a legitimate strategy.
