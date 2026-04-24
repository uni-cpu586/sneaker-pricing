"""SNKRDUNK / Area02 熱銷榜爬取"""
from __future__ import annotations
import re
import json
import requests
from typing import Optional

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,ja;q=0.8,en;q=0.7",
}


def _area02_sku(product_url: str) -> Optional[str]:
    """從 Area02 商品頁 JSON-LD 取 SKU（requests，不需要 Playwright）"""
    try:
        res = requests.get(product_url, headers=_HEADERS, timeout=10)
        if res.status_code != 200:
            return None
        m = re.search(r'"sku"\s*:\s*"([A-Z0-9][A-Z0-9\-]{3,14})"', res.text)
        return m.group(1) if m else None
    except Exception:
        return None


def fetch_snkrdunk_ranking(limit: int = 20) -> list[dict]:
    """抓取 SNKRDUNK 首頁熱門スニーカー前 N 名（Playwright SSR）"""
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=_HEADERS["User-Agent"],
                locale="ja-JP",
            )
            page.goto("https://snkrdunk.com/", wait_until="networkidle", timeout=30000)

            data = page.evaluate("""() => {
                // 找 class 含 sneaker 的 section
                const sections = [...document.querySelectorAll('[class*="sneaker"]')];
                let links = [];
                for (const sec of sections) {
                    const found = [...sec.querySelectorAll('a[href*="/products/"]')];
                    if (found.length >= 5) { links = found; break; }
                }
                const seen = new Set();
                const items = [];
                for (const a of links) {
                    const sku = (a.href.match(/\\/products\\/([^/?#\\s]{3,20})/) || [])[1];
                    if (!sku || seen.has(sku)) continue;
                    seen.add(sku);
                    const img = a.querySelector('img');
                    const priceM = a.textContent.match(/¥([\\d,]+)/);
                    items.push({
                        sku,
                        name: img ? img.alt : '',
                        price_jpy: priceM ? parseInt(priceM[1].replace(/,/g,'')) : null
                    });
                    if (items.length >= 30) break;
                }
                return items;
            }""")

            browser.close()

        from src.pricing import get_rate
        jpy_rate = get_rate("JPY")

        for i, item in enumerate(data[:limit]):
            results.append({
                "rank":   i + 1,
                "sku":    item["sku"],
                "name":   item["name"] or item["sku"],
                "price":  round(item["price_jpy"] * jpy_rate) if item.get("price_jpy") else None,
                "source": "SNKRDUNK",
            })

    except Exception as e:
        print(f"[SNKRDUNK] 抓取失敗：{e}")

    return results


def fetch_area02_ranking(limit: int = 20) -> list[dict]:
    """抓取 Area02 /hot TRENDING 前 N 名，並抓每個商品頁的 SKU"""
    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=_HEADERS["User-Agent"],
                locale="zh-TW",
            )
            page.goto("https://www.area02.com/en-US/hot", wait_until="networkidle", timeout=30000)

            raw = page.evaluate("""(limit) => {
                const links = [...document.querySelectorAll('a[href*="/i-p"]')];
                return links.slice(0, limit).map((a, i) => {
                    const img = a.querySelector('img');
                    const priceM = a.textContent.match(/NT\\$\\s?([\\d,]+)/);
                    return {
                        rank:      i + 1,
                        url:       a.href,
                        name:      img ? img.alt : a.textContent.trim().slice(0, 60),
                        price_twd: priceM ? parseInt(priceM[1].replace(/,/g,'')) : null
                    };
                });
            }""", limit)

            browser.close()

        for item in raw:
            sku = _area02_sku(item["url"])
            results.append({
                "rank":   item["rank"],
                "sku":    sku,
                "name":   item["name"],
                "price":  item["price_twd"],
                "source": "Area02",
                "url":    item["url"],
            })

    except Exception as e:
        print(f"[Area02] 抓取失敗：{e}")

    return results
