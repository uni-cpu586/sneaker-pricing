"""C&C 球鞋比價 Web 後端"""
from __future__ import annotations
import asyncio, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="C&C 球鞋比價")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_OFFICIAL_PLATFORMS = {"ABC-MART JP", "Nike TW", "Adidas TW"}
_COLLAB_KEYWORDS = [
    "supreme", "bape", "off-white", "travis scott", "fragment",
    "sacai", "union", "palace", "clot", "stussy", "stüssy",
    "comme des garçons", "cdg", "patta", "atmos", "concepts",
    "undercover", "acronym", "a-cold-wall", "fear of god",
]

_cache: dict = {}
_CACHE_TTL = 600


def _cached(key: str):
    e = _cache.get(key)
    return e["v"] if e and time.time() - e["t"] < _CACHE_TTL else None


def _store(key: str, val):
    _cache[key] = {"t": time.time(), "v": val}


def _is_collab(name: str) -> bool:
    return any(k in name.lower() for k in _COLLAB_KEYWORDS)


def _do_search(q: str) -> dict:
    from src.search import search_product
    from src.scraper import (
        scrape_abc_mart, scrape_nike, scrape_yahoo_auctions,
        scrape_pchome, scrape_shopee, scrape_momo,
        scrape_adidas_tw, scrape_stockx,
    )

    entry = search_product(q)
    if not entry:
        return {"error": f"找不到「{q}」"}

    sku       = entry.get("sku")
    name      = entry.get("name", "")
    abc_kw    = entry.get("abc_keyword")
    yahoo_kw  = entry.get("yahoo_keyword")
    pchome_kw = entry.get("pchome_keyword")
    shopee_kw = entry.get("shopee_keyword")

    tasks: list[tuple] = []
    if abc_kw:    tasks.append((scrape_abc_mart, abc_kw))
    if sku:       tasks.append((scrape_nike, sku))
    if yahoo_kw:  tasks.append((scrape_yahoo_auctions, yahoo_kw))
    if pchome_kw:
        tasks.append((scrape_pchome, pchome_kw))
        tasks.append((scrape_momo, pchome_kw))
    if shopee_kw: tasks.append((scrape_shopee, shopee_kw))
    if name.lower().startswith("adidas") and abc_kw:
        tasks.append((scrape_adidas_tw, abc_kw))
    if name:      tasks.append((scrape_stockx, name))

    platform_results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn, kw): (fn, kw) for fn, kw in tasks}
        for fut in as_completed(futures):
            try:
                platform_results.append(fut.result())
            except Exception:
                pass

    platforms, official_prices, market_prices = [], [], []
    for r in platform_results:
        price   = r.get("price")
        pname   = r.get("platform", "")
        is_off  = pname in _OFFICIAL_PLATFORMS
        platforms.append({
            "platform":     pname,
            "price":        price,
            "currency":     r.get("currency", "TWD"),
            "status":       r.get("status", "ok"),
            "url":          r.get("url", ""),
            "price_min":    r.get("price_min"),
            "price_max":    r.get("price_max"),
            "sample_count": r.get("sample_count"),
            "is_official":  is_off,
        })
        if price:
            (official_prices if is_off else market_prices).append(price)

    platforms.sort(key=lambda x: (x["price"] is None, x["price"] or 0))

    arbitrage = None
    if official_prices and market_prices:
        buy    = min(official_prices)
        sell   = max(market_prices)
        profit = sell - buy
        if profit > 0:
            arbitrage = {
                "buy_at":     buy,
                "sell_at":    sell,
                "profit":     profit,
                "margin_pct": round(profit / buy * 100, 1),
            }

    return {
        "name":      name,
        "sku":       sku,
        "is_collab": _is_collab(name),
        "platforms": platforms,
        "arbitrage": arbitrage,
    }


@app.get("/api/search")
async def api_search(q: str = ""):
    q = q.strip()
    if not q:
        return JSONResponse({"error": "請輸入鞋款名稱"})
    if cached := _cached(f"s:{q}"):
        return JSONResponse({**cached, "cached": True})
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _do_search, q)
    if "error" not in result:
        _store(f"s:{q}", result)
    return JSONResponse(result)


@app.get("/api/profit")
async def api_profit(
    cost: float,
    currency: str = "TWD",
    shipping: float = 100,
    commission: float = 0.05,
    margin: float = 0.15,
):
    from src.pricing import calculate_price
    return JSONResponse(calculate_price(
        cost=cost, currency=currency, shipping=shipping,
        commission_rate=commission, margin_rate=margin,
    ))


@app.get("/api/trending")
async def api_trending():
    if cached := _cached("trending"):
        return JSONResponse(cached)

    items = []
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        try:
            from supabase import create_client
            sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
            res = (sb.table("pending_review")
                     .select("*")
                     .order("created_at", desc=True)
                     .limit(40)
                     .execute())
            items = res.data or []
        except Exception:
            pass

    result = {"items": items}
    if items:
        _store("trending", result)
    return JSONResponse(result)


_COOKIE_FILE = Path(__file__).parent.parent / "shopee_cookie.txt"


class CookiePayload(BaseModel):
    cookie: str


@app.post("/admin/update-shopee-cookie")
async def update_shopee_cookie(
    payload: CookiePayload,
    x_admin_token: str = Header(default=""),
):
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cookie = payload.cookie.strip()
    if not cookie:
        raise HTTPException(status_code=400, detail="Cookie 不能是空的")
    _COOKIE_FILE.write_text(cookie, encoding="utf-8")
    # 清掉 Shopee 相關 cache，讓下次查詢用新 cookie
    for k in list(_cache.keys()):
        del _cache[k]
    return JSONResponse({"ok": True, "length": len(cookie)})


@app.get("/admin/cookie-status")
async def cookie_status(x_admin_token: str = Header(default="")):
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if _COOKIE_FILE.exists():
        c = _COOKIE_FILE.read_text(encoding="utf-8").strip()
        return JSONResponse({"source": "file", "length": len(c), "preview": c[:40] + "…"})
    return JSONResponse({"source": "env", "length": len(os.getenv("SHOPEE_COOKIE", ""))})


_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.get("/admin")
async def admin_page():
    return FileResponse(str(_static / "admin.html"))


@app.get("/")
async def root():
    return FileResponse(str(_static / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
