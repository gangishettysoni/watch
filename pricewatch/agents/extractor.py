"""Extractor agent: one adapter per storefront turns a fetched page into an Observation.

Adapters receive the raw HTML (already fetched by the Client) and the URL. They must not do
their own networking except through the Client they are given, so throttling and cookies
stay in one place.

Adapters are registered by name; `stores.yaml` maps each store to an adapter.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..http import Client
from ..models import Observation
from .normalizer import parse_money, unit_price

ADAPTERS: dict[str, Callable[[Client, str, str, str], Observation]] = {}


def adapter(name: str):
    def deco(fn):
        ADAPTERS[name] = fn
        return fn
    return deco


def _pid_from_url(url: str) -> str:
    return urlparse(url).path.rstrip("/").split("/")[-1]


# --------------------------------------------------------------------------- level 1
@adapter("corner")
def extract_corner(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    ld = soup.find("script", type="application/ld+json")
    data = json.loads(ld.string) if ld and ld.string else {}
    offer = data.get("offers", {})
    price_cents, currency = parse_money(str(offer.get("price", "")), offer.get("priceCurrency"))
    was = soup.find("s")
    compare, _ = parse_money(was.get_text(), currency) if was else (None, None)
    return Observation(
        store=store, product_id=data.get("sku") or _pid_from_url(url), url=url,
        name=data.get("name") or soup.h1.get_text(strip=True),
        price_cents=price_cents, currency=currency or "USD", compare_at_cents=compare,
        availability="in_stock" if "InStock" in str(offer.get("availability", "")) else "out_of_stock",
    )


# --------------------------------------------------------------------------- level 2
@adapter("maple")
def extract_maple(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    name = soup.select_one(".product__title").get_text(strip=True)
    price_candidates = soup.select(".price .price")
    price_el = next((el for el in reversed(price_candidates) if "price--compare" not in el.get("class", [])), None)
    if price_el is None:
        price_el = soup.select_one(".price--sale") or soup.select_one(".price .price")
    price_cents, currency = parse_money(price_el.get_text(" ", strip=True), "EUR") if price_el else (None, "EUR")
    compare_el = soup.select_one(".price--compare")
    compare, _ = parse_money(compare_el.get_text(" ", strip=True), currency) if compare_el else (None, None)
    avail = "out_of_stock" if "Sold out" in soup.get_text() else "in_stock"
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=name,
        price_cents=price_cents, currency=currency or "EUR", compare_at_cents=compare, availability=avail,
    )


# --------------------------------------------------------------------------- level 3
# Class names used by Zon's product page template.
ZON_CLASSES = {"price": "a-1c3f89", "whole": "a-2b2181", "frac": "a-4e2865", "title": "a-affa10", "avail": "a-78b7d1", "unit": "a-702121"}


@adapter("zon")
def extract_zon(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    if "Are you a human" in html:
        return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
                           currency="USD", notes=["robot check page"])
    title = soup.find(class_=ZON_CLASSES["title"])
    name = title.get_text(strip=True) if title else ""
    m = re.search(r"Pack of (\d+)", name)
    pack = int(m.group(1)) if m else 1
    box = soup.find(class_=ZON_CLASSES["price"])
    price_cents: Optional[int] = None
    if box:
        whole = box.find(class_=ZON_CLASSES["whole"])
        frac = box.find(class_=ZON_CLASSES["frac"])
        if whole and frac:
            price_cents, _ = parse_money(f"${whole.get_text()}.{frac.get_text()}", "USD")
    avail_el = soup.find(class_=ZON_CLASSES["avail"])
    avail = "out_of_stock" if avail_el and "out of stock" in avail_el.get_text().lower() else "in_stock"
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=re.sub(r"\s*\(Pack of \d+\)", "", name),
        price_cents=price_cents, currency="USD", availability=avail, pack_size=pack,
        unit_price_cents=unit_price(price_cents, pack),
        notes=[] if price_cents is not None else ["no price found"],
    )


# --------------------------------------------------------------------------- levels 4-5
@adapter("shield")
def extract_shield(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    if "Are you a human" in html or "Checking your browser" in html or "Just a moment" in html:
        return Observation(store=store, product_id=_pid_from_url(url), url=url, name="", price_cents=None,
                           currency="GBP", availability="unknown", notes=["shield challenge page"])

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(" ", strip=True)
    if not name:
        title = soup.find("title")
        if title:
            name = title.get_text(" ", strip=True).replace("— Shield Outfitters", "").strip()

    price_candidates = []
    for sel in ("strong", ".price", "[data-price]", "span", "p", "li", ".money"):
        for el in soup.select(sel):
            txt = el.get_text(" ", strip=True)
            if txt and any(ch.isdigit() for ch in txt):
                price_candidates.append(txt)
    price_cents = None
    currency = "GBP"
    for text in price_candidates:
        amount, picked = parse_money(text, currency)
        if amount is not None:
            price_cents, currency = amount, picked or currency
            break
    if price_cents is None:
        text = soup.get_text(" ", strip=True)
        amount, picked = parse_money(text, currency)
        if amount is not None:
            price_cents, currency = amount, picked or currency
    availability = "in_stock" if "in stock" in soup.get_text(" ", strip=True).lower() else "out_of_stock" if "out of stock" in soup.get_text(" ", strip=True).lower() else "unknown"
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=name,
        price_cents=price_cents, currency=currency, availability=availability,
    )


@adapter("flux")
def extract_flux(client: Client, store: str, url: str, html: str) -> Observation:
    soup = BeautifulSoup(html, "html.parser")
    sku = (soup.select_one("[data-sku]") or {}).get("data-sku") or _pid_from_url(url)
    product = None
    build = (soup.select_one('meta[name="flux-build"]') or {}).get("content")
    api_url = urljoin(url, "/stores/flux/api/graphql")
    query = "query($sku:String!){product(sku:$sku){sku title offer{amount unit currency stock stale}}}"
    payload = {"query": query, "variables": {"sku": sku}}
    headers = {"content-type": "application/json"}
    if build:
        headers["x-flux-build"] = build
    try:
        if sku:
            sig_seed = "fx_1b11e1e8cfb25a950a27|" + sku
            headers["x-flux-sig"] = hashlib.sha256(sig_seed.encode("utf-8")).hexdigest()[:24]
            r = client.post(api_url, json=payload, headers=headers)
            if r.status_code == 200:
                data = r.json()
                product = data.get("data", {}).get("product")
    except Exception:
        product = None

    if product is None:
        title = soup.find("h1")
        text = soup.get_text(" ", strip=True)
        currency = "USD"
        price_cents = None
        for candidate in re.findall(r"\$\s?\d[\d,]*(?:\.\d+)?|USD\s?\d[\d,]*(?:\.\d+)?", text):
            val, cur = parse_money(candidate, currency)
            if val is not None:
                price_cents, currency = val, cur or currency
                break
        fallback = title.get_text(" ", strip=True) if title else ""
        return Observation(store=store, product_id=_pid_from_url(url), url=url, name=fallback, price_cents=price_cents,
                           currency=currency, availability="in_stock" if "in stock" in text.lower() else "out_of_stock" if "out of stock" in text.lower() else "unknown")

    offer = product.get("offer") or {}
    amount = offer.get("amount")
    unit = offer.get("unit")
    if amount is None:
        price_cents = None
    else:
        try:
            amount_f = float(amount)
            if unit == "major":
                price_cents = int(round(amount_f * 100))
            else:
                price_cents = int(round(amount_f))
        except (TypeError, ValueError):
            price_cents = None

    currency = offer.get("currency") or "USD"
    stock = offer.get("stock")
    avail = "in_stock" if stock == "IN_STOCK" else "out_of_stock" if stock == "OUT_OF_STOCK" else "unknown"
    title = product.get("title") or (soup.find("h1") or {}).get_text(" ", strip=True) or ""
    return Observation(
        store=store, product_id=_pid_from_url(url), url=url, name=title,
        price_cents=price_cents, currency=currency, availability=avail,
        notes=["last known price"] if offer.get("stale") else [],
    )


def extract(client: Client, store: str, adapter_name: str, url: str, html: str) -> Observation:
    fn = ADAPTERS.get(adapter_name)
    if fn is None:
        raise KeyError(f"no adapter named {adapter_name!r}")
    return fn(client, store, url, html)
