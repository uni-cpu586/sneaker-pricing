"""數據採集器：從各平台抓取球鞋價格"""
import re
import requests
from bs4 import BeautifulSoup

_NIKE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Nike-Api-Caller-Id": "com.nike.commerce.nikedotcom.web",
}

_ABC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ja,en;q=0.9",
}


def scrape_abc_mart(keyword: str) -> dict:
    """搜尋 ABC-MART JP，回傳最低售價（JPY）"""
    search_url = f"https://www.abc-mart.net/shop/goods/search.aspx?keyword={keyword}"
    try:
        res = requests.get(search_url, headers=_ABC_HEADERS, timeout=10)
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
                    "currency": "JPY", "status": "not_found", "url": search_url}

        cheapest = min(prices, key=lambda x: x["price"])
        return {
            "platform": "ABC-MART JP",
            "keyword": keyword,
            "name": cheapest["name"],
            "price": cheapest["price"],
            "currency": "JPY",
            "status": "ok",
            "url": cheapest["url"],
        }
    except Exception as e:
        return {"platform": "ABC-MART JP", "keyword": keyword, "price": None,
                "currency": "JPY", "status": f"error: {e}", "url": search_url}


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
        res = requests.get(url, params=params, headers=_NIKE_HEADERS, timeout=10)
        res.raise_for_status()
        objects = res.json().get("objects", [])
        if not objects:
            return {"platform": "Nike TW", "sku": sku, "price": None, "currency": "TWD",
                    "status": "not_found", "url": f"https://www.nike.com/tw/"}

        pi = objects[0].get("productInfo", [{}])[0]
        merch_price = pi.get("merchPrice", {})
        name = pi.get("productContent", {}).get("title", sku)
        price = merch_price.get("currentPrice")
        return {
            "platform": "Nike TW",
            "sku": sku,
            "name": name,
            "price": price,
            "currency": "TWD",
            "discounted": merch_price.get("discounted", False),
            "status": "ok",
            "url": f"https://www.nike.com/tw/t/-/{sku}",
        }
    except Exception as e:
        return {"platform": "Nike TW", "sku": sku, "price": None, "currency": "TWD",
                "status": f"error: {e}", "url": ""}


def scrape_shopee(keyword: str) -> dict:
    """搜尋蝦皮 TW，回傳平均售價（TWD）"""
    url = "https://shopee.tw/api/v4/search/search_items/"
    params = {
        "by": "relevance",
        "keyword": keyword,
        "limit": 20,
        "newest": 0,
        "order": "desc",
        "page_type": "search",
        "version": 2,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"https://shopee.tw/search?keyword={keyword}",
        "X-Shopee-Language": "zh-Hant",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        items = res.json().get("items", []) or []

        prices = []
        for item in items:
            info = item.get("item_basic") or item
            price_raw = info.get("price") or info.get("price_min")
            if price_raw:
                prices.append(int(price_raw) // 100000)  # Shopee 價格單位為 1/100000 TWD

        if not prices:
            return {"platform": "Shopee TW", "keyword": keyword, "price": None,
                    "currency": "TWD", "status": "not_found",
                    "url": f"https://shopee.tw/search?keyword={keyword}"}

        avg_price = sum(prices) // len(prices)
        return {
            "platform": "Shopee TW",
            "keyword": keyword,
            "price": avg_price,
            "price_min": min(prices),
            "price_max": max(prices),
            "sample_count": len(prices),
            "currency": "TWD",
            "status": "ok",
            "url": f"https://shopee.tw/search?keyword={keyword}",
        }
    except Exception as e:
        return {"platform": "Shopee TW", "keyword": keyword, "price": None,
                "currency": "TWD", "status": f"error: {e}",
                "url": f"https://shopee.tw/search?keyword={keyword}"}


def scrape_yahoo_auctions(keyword: str) -> dict:
    """搜尋 Yahoo Auctions JP 在售商品，計算平均市場價（JPY）"""
    search_url = f"https://auctions.yahoo.co.jp/search/search?p={keyword}&va={keyword}&exflg=1&b=1&n=20&s1=cbids&o1=d&st=1"
    try:
        res = requests.get(search_url, headers=_ABC_HEADERS, timeout=10)
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
                    "currency": "JPY", "status": "not_found", "url": search_url}

        avg_price = sum(prices) // len(prices)
        return {
            "platform": "Yahoo Auctions JP",
            "keyword": keyword,
            "price": avg_price,
            "price_min": min(prices),
            "price_max": max(prices),
            "sample_count": len(prices),
            "currency": "JPY",
            "status": "ok",
            "url": search_url,
        }
    except Exception as e:
        return {"platform": "Yahoo Auctions JP", "keyword": keyword, "price": None,
                "currency": "JPY", "status": f"error: {e}", "url": search_url}
