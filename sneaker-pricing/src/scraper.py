"""數據採集器：從各平台抓取球鞋價格，全部回傳 TWD"""
import json
import random
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from src.pricing import get_rate


def _jpy_to_twd(jpy: int) -> int:
    return round(jpy * get_rate("JPY"))


def _usd_to_twd(usd: float) -> int:
    return round(usd * get_rate("USD"))


_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]


def _rua() -> str:
    return random.choice(_UA_POOL)


def _h(base: dict) -> dict:
    """回傳加上隨機 UA 的 header 副本"""
    return {**base, "User-Agent": _rua()}


_NIKE_BASE = {
    "Nike-Api-Caller-Id": "com.nike.commerce.nikedotcom.web",
}

_ABC_BASE = {
    "Accept-Language": "ja,en;q=0.9",
}

_BROWSER_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}


def scrape_abc_mart(keyword: str) -> dict:
    """搜尋 ABC-MART JP，回傳最低售價（JPY）"""
    search_url = f"https://www.abc-mart.net/shop/goods/search.aspx?keyword={keyword}"
    try:
        res = requests.get(search_url, headers=_h(_ABC_BASE), timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        prices = []
        items = soup.select(".StyleT_Item_")
        for item in items:
            price_tag = item.select_one(".price_ dd")
            link = item.select_one("a.StyleT_Item_Link_")
            if not price_tag:
                continue
            price_text = price_tag.get_text(strip=True).split("(")[0]
            digits = re.sub(r"[^\d]", "", price_text)
            if digits:
                prices.append({
                    "price": int(digits),
                    "url": link["href"] if link else search_url,
                    "name": (item.select_one(".name2_") or item).get_text(strip=True),
                })

        if not prices:
            return {"platform": "ABC-MART JP", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found", "url": search_url}

        cheapest = min(prices, key=lambda x: x["price"])
        return {
            "platform": "ABC-MART JP",
            "keyword": keyword,
            "name": cheapest["name"],
            "price": _jpy_to_twd(cheapest["price"]),
            "currency": "TWD",
            "status": "ok",
            "url": cheapest["url"],
        }
    except Exception as e:
        return {"platform": "ABC-MART JP", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}", "url": search_url}


def scrape_nike(sku: str) -> dict:
    """抓取 Nike TW 官網售價（TWD），透過官方 product feed API"""
    url = "https://api.nike.com/product_feed/threads/v2/"
    params = [
        ("filter", "marketplace(TW)"),
        ("filter", "language(zh-Hant)"),
        ("filter", "channelId(d9a5bc42-4b9c-4976-858a-f159cf99c647)"),
        ("filter", "exclusiveAccess(true,false)"),
        ("filter", f"productInfo.merchProduct.styleColor({sku})"),
        ("count", "1"),
    ]
    try:
        res = requests.get(url, params=params, headers=_h(_NIKE_BASE), timeout=10)
        res.raise_for_status()
        objects = res.json().get("objects", [])
        if not objects:
            return {"platform": "Nike TW", "sku": sku, "price": None, "currency": "TWD",
                    "status": "not_found", "url": f"https://www.nike.com/tw/"}

        obj = objects[0]
        pi = obj.get("productInfo", [{}])[0]
        merch_price = pi.get("merchPrice", {})
        content = pi.get("productContent", {})
        name = content.get("title", sku)
        price = merch_price.get("currentPrice")
        card = (obj.get("publishedContent") or {}).get("properties", {}).get("productCard", {}).get("properties", {})
        image_url = card.get("squarishURL") or card.get("portraitURL") or None
        return {
            "platform": "Nike TW",
            "sku": sku,
            "name": name,
            "price": price,
            "currency": "TWD",
            "discounted": merch_price.get("discounted", False),
            "status": "ok",
            "url": f"https://www.nike.com/tw/t/-/{sku}",
            "image_url": image_url,
        }
    except Exception as e:
        return {"platform": "Nike TW", "sku": sku, "price": None, "currency": "TWD",
                "status": f"error: {e}", "url": ""}


def _load_shopee_cookie() -> str:
    """優先讀 shopee_cookie.txt，再 fallback .env SHOPEE_COOKIE"""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv()
    cookie_file = Path(__file__).parent.parent / "shopee_cookie.txt"
    if cookie_file.exists():
        c = cookie_file.read_text(encoding="utf-8").strip()
        if c:
            return c
    return os.getenv("SHOPEE_COOKIE", "").strip()


def _parse_shopee_items(items: list) -> list:
    prices = []
    for item in items:
        info = item.get("item_basic") or item
        price_raw = info.get("price") or info.get("price_min")
        if price_raw:
            val = int(price_raw)
            # Shopee 台灣以 1/100000 TWD 儲存價格
            twd = val // 100000
            if twd > 0:
                prices.append(twd)
    return prices


def scrape_shopee(keyword: str) -> dict:
    """搜尋蝦皮 TW；優先用 cookie，失效則 fallback 訪客模式"""
    cookie_str = _load_shopee_cookie()
    search_url = f"https://shopee.tw/search?keyword={quote(keyword)}"
    api_url = (
        f"https://shopee.tw/api/v4/search/search_items"
        f"?by=relevancy&keyword={quote(keyword)}&limit=20&newest=0&order=desc"
        f"&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2"
    )
    base_headers = _h({
        "Referer": search_url,
        "x-api-source": "pc",
        "Accept": "application/json",
    })

    def _fetch(with_cookie: bool):
        h = {**base_headers}
        if with_cookie and cookie_str:
            h["Cookie"] = cookie_str
        return requests.get(api_url, headers=h, timeout=10).json()

    try:
        d = _fetch(with_cookie=True)
        # cookie 過期時 fallback 訪客模式
        if d.get("error") == 90309999 and cookie_str:
            d = _fetch(with_cookie=False)
        if d.get("error"):
            return {"platform": "Shopee TW", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "error", "url": search_url}
        items = d.get("items", []) or []
        prices = _parse_shopee_items(items)
        if not prices:
            return {"platform": "Shopee TW", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found", "url": search_url}
        return {
            "platform": "Shopee TW", "keyword": keyword,
            "price": sum(prices) // len(prices),
            "price_min": min(prices), "price_max": max(prices),
            "sample_count": len(prices),
            "currency": "TWD", "status": "ok", "url": search_url,
        }
    except Exception as e:
        return {"platform": "Shopee TW", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}", "url": search_url}


def scrape_pchome(keyword: str) -> dict:
    """搜尋 PChome 24h，回傳平均售價（TWD）"""
    search_url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={keyword}&page=1&sort=rnk/dc"
    try:
        res = requests.get(search_url, headers=_h(_ABC_BASE), timeout=10)
        res.raise_for_status()
        prods = res.json().get("prods", []) or []

        prices = [int(p["price"]) for p in prods if p.get("price")]
        if not prices:
            return {"platform": "PChome 24h", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found",
                    "url": f"https://24h.pchome.com.tw/search/?q={keyword}"}

        avg_price = sum(prices) // len(prices)
        return {
            "platform": "PChome 24h",
            "keyword": keyword,
            "price": avg_price,
            "price_min": min(prices),
            "price_max": max(prices),
            "sample_count": len(prices),
            "currency": "TWD",
            "status": "ok",
            "url": f"https://24h.pchome.com.tw/search/?q={keyword}",
        }
    except Exception as e:
        return {"platform": "PChome 24h", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}",
                "url": f"https://24h.pchome.com.tw/search/?q={keyword}"}


def scrape_yahoo_auctions(keyword: str) -> dict:
    """搜尋 Yahoo Auctions JP 在售商品，計算平均市場價（JPY）"""
    search_url = f"https://auctions.yahoo.co.jp/search/search?p={keyword}&va={keyword}&exflg=1&b=1&n=20&s1=cbids&o1=d&st=1"
    try:
        res = requests.get(search_url, headers=_h(_ABC_BASE), timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        prices = []
        for item in soup.select(".Product"):
            price_el = item.select_one(".Product__priceValue")
            if not price_el:
                continue
            digits = re.sub(r"[^\d]", "", price_el.text)
            if digits:
                prices.append(int(digits))

        if not prices:
            return {"platform": "Yahoo Auctions JP", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found", "url": search_url}

        avg_jpy = sum(prices) // len(prices)
        return {
            "platform": "Yahoo Auctions JP",
            "keyword": keyword,
            "price": _jpy_to_twd(avg_jpy),
            "price_min": _jpy_to_twd(min(prices)),
            "price_max": _jpy_to_twd(max(prices)),
            "sample_count": len(prices),
            "currency": "TWD",
            "status": "ok",
            "url": search_url,
        }
    except Exception as e:
        return {"platform": "Yahoo Auctions JP", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}", "url": search_url}


_MOMO_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def scrape_momo(keyword: str) -> dict:
    """搜尋 Momo 購物網，從 JSON-LD 結構化資料取價格與圖片（TWD），失敗自動 retry"""
    import time
    search_url = f"https://www.momoshop.com.tw/search/searchShop.jsp?keyword={quote(keyword)}&cateCode=&ent=k&disp=L&comdtyTyp=B&page=1"
    last_err = None

    for attempt in range(3):
        if attempt > 0:
            time.sleep(attempt * 2)
        try:
            sess = requests.Session()
            sess.headers.update(_h(_MOMO_BASE))
            res = sess.get(search_url, timeout=15)
            res.raise_for_status()

            # 確認是真正的搜尋結果頁（被 bot 擋住時 body 很短）
            if len(res.text) < 5000:
                last_err = "response too short, possible bot block"
                continue

            raw_prices = re.findall(r'"price":\s*"(\d+)"', res.text)
            prices = [int(p) for p in raw_prices if 500 <= int(p) <= 80000]
            imgs = re.findall(r'"image":\s*"(https://img\d+\.momoshop\.com\.tw[^"]+)"', res.text)
            image_url = imgs[0] if imgs else None

            if prices:
                avg_price = sum(prices) // len(prices)
                return {
                    "platform": "Momo 購物",
                    "keyword": keyword,
                    "price": avg_price,
                    "price_min": min(prices),
                    "price_max": max(prices),
                    "sample_count": len(prices),
                    "currency": "TWD",
                    "status": "ok",
                    "url": search_url,
                    "image_url": image_url,
                }

            # 頁面正常載入但無商品
            if "momoshop" in res.text:
                return {"platform": "Momo 購物", "keyword": keyword, "price": None,
                        "currency": "TWD", "status": "not_found", "url": search_url}

            last_err = "no prices found, unexpected page"
        except Exception as e:
            last_err = e

    return {"platform": "Momo 購物", "keyword": keyword, "price": None,
            "currency": "TWD", "status": f"error: {last_err}", "url": search_url}


def scrape_adidas_tw(keyword: str) -> dict:
    """搜尋 Adidas 台灣官網（91APP，JS 渲染），用 Playwright 取價格與圖片"""
    from playwright.sync_api import sync_playwright
    search_url = f"https://www.adidas.com.tw/search?q={quote(keyword)}"
    captured_images: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_rua())

            def _on_response(response):
                url = response.url
                ct = response.headers.get("content-type", "")
                if "image" in ct and "91app.com" in url and "SalePage" in url:
                    captured_images.append(url)

            page.on("response", _on_response)
            page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            try:
                page.wait_for_function(
                    "document.body.innerText.includes('NT$')", timeout=12000
                )
            except Exception:
                pass
            html = page.content()
            browser.close()

        prices = []
        for m in re.finditer(r"NT\$\s*([\d,]+)", html):
            val = int(m.group(1).replace(",", ""))
            if 500 < val < 50000:
                prices.append(val)
        prices = list(dict.fromkeys(prices))

        image_url = captured_images[0] if captured_images else None

        if not prices:
            return {"platform": "Adidas TW", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found", "url": search_url,
                    "image_url": image_url}

        avg_price = sum(prices) // len(prices)
        return {
            "platform": "Adidas TW",
            "keyword": keyword,
            "price": avg_price,
            "price_min": min(prices),
            "price_max": max(prices),
            "sample_count": len(prices),
            "currency": "TWD",
            "status": "ok",
            "url": search_url,
            "image_url": image_url,
        }
    except Exception as e:
        return {"platform": "Adidas TW", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}", "url": search_url}


def scrape_stockx(keyword: str) -> dict:
    """搜尋 StockX，回傳最低賣出價（TWD，原幣 USD）"""
    search_url = f"https://stockx.com/search?s={quote(keyword)}"
    try:
        res = requests.post(
            "https://xw7sbct9v6-dsn.algolia.net/1/indexes/products/query",
            headers={
                "X-Algolia-Application-Id": "XW7SBCT9V6",
                "X-Algolia-API-Key": "6b5e76b49705eb9f51a06d3c82f7acee",
                "Content-Type": "application/json",
            },
            json={"params": f"query={keyword}&hitsPerPage=10"},
            timeout=10,
        )
        if res.status_code == 200:
            hits = res.json().get("hits", [])
            image_url = (hits[0].get("media") or {}).get("imageUrl") if hits else None
            prices_usd = [
                h["market"]["lowestAsk"]
                for h in hits
                if (h.get("market") or {}).get("lowestAsk", 0) > 0
            ]
            if prices_usd:
                avg_usd = sum(prices_usd) / len(prices_usd)
                rate = get_rate("USD")
                return {
                    "platform": "StockX",
                    "keyword": keyword,
                    "price": _usd_to_twd(avg_usd),
                    "price_min": _usd_to_twd(min(prices_usd)),
                    "price_max": _usd_to_twd(max(prices_usd)),
                    "sample_count": len(prices_usd),
                    "currency": "TWD",
                    "status": "ok",
                    "url": search_url,
                    "image_url": image_url,
                }
    except Exception:
        pass

    return {"platform": "StockX", "keyword": keyword, "price": None,
            "currency": "TWD", "status": "not_found", "url": search_url}
