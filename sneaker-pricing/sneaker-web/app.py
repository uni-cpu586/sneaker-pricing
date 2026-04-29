"""C&C 球鞋比價 Web 後端"""
from __future__ import annotations
import asyncio, json, os, sys, time
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

_HOT_QUERIES = [
    # 10 原始熱門
    "熊貓 Dunk", "Samba", "AJ1 倒鉤", "Air Force 1",
    "Yeezy 斑馬", "NB 550", "Speedcat", "Kayano 14", "NB 9060", "Campus 00s",
    # Dunk 配色
    "芝加哥", "陰陽",
    # Samba 配色
    "samba black", "samba wales bonner", "bad bunny samba",
    # AJ1 配色
    "大學藍", "黑腳趾", "lost and found",
    # AF1 配色
    "af1 triple black",
    # Yeezy 配色
    "yeezy cream", "yeezy beluga",
    # NB 聯名
    "ald 550",
    # AJ4 + Dunk High
    "AJ4", "dunk high panda",
]


async def _warm_hot_cache() -> None:
    loop = asyncio.get_event_loop()
    for q in _HOT_QUERIES:
        if not _cached(f"s:{q}"):
            try:
                result = await loop.run_in_executor(None, _do_search, q)
                if "error" not in result:
                    _store(f"s:{q}", result)
            except Exception:
                pass
            await asyncio.sleep(3)


async def _cache_warmer() -> None:
    await asyncio.sleep(15)
    while True:
        await _warm_hot_cache()
        await asyncio.sleep(3600)


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

_CACHE_TTL = 600
_cache: dict = {}
_redis = None
_START_TIME = time.time()


def _init_redis() -> None:
    global _redis
    url = os.getenv("REDIS_URL")
    if not url:
        return
    try:
        import redis as _redis_lib
        r = _redis_lib.from_url(url, decode_responses=True)
        r.ping()
        _redis = r
    except Exception:
        pass


_init_redis()


def _cached(key: str):
    if _redis:
        try:
            v = _redis.get(key)
            return json.loads(v) if v else None
        except Exception:
            pass
    e = _cache.get(key)
    return e["v"] if e and time.time() - e["t"] < _CACHE_TTL else None


def _store(key: str, val) -> None:
    if _redis:
        try:
            _redis.setex(key, _CACHE_TTL, json.dumps(val, ensure_ascii=False))
            return
        except Exception:
            pass
    _cache[key] = {"t": time.time(), "v": val}


def _is_collab(name: str) -> bool:
    return any(k in name.lower() for k in _COLLAB_KEYWORDS)


def _do_search(q: str) -> dict:
    from src.search import search_product, get_siblings
    from src.scraper import (
        scrape_abc_mart, scrape_nike, scrape_yahoo_auctions,
        scrape_pchome, scrape_shopee, scrape_momo,
        scrape_adidas_tw, scrape_stockx,
    )

    entry = search_product(q)
    if not entry:
        return {"error": f"找不到「{q}」"}

    confidence = entry.get("confidence")
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
    name_lc = name.lower()
    # 動態條目（abc_kw 為 None）時，用 pchome_kw 當 Adidas TW 的關鍵字
    adidas_kw = abc_kw or (pchome_kw if name_lc.startswith("adidas") else None)
    if name_lc.startswith("adidas") and adidas_kw:
        tasks.append((scrape_adidas_tw, adidas_kw))
    if name:      tasks.append((scrape_stockx, name))

    platform_results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn, kw): (fn, kw) for fn, kw in tasks}
        for fut in as_completed(futures):
            try:
                platform_results.append(fut.result())
            except Exception:
                pass

    _IMG_PRIO = {"Nike TW": 0, "Adidas TW": 1, "StockX": 2, "Momo 購物": 3}
    platforms, official_prices, market_prices = [], [], []
    image_url = entry.get("image_url")  # catalog 指定的圖優先
    _image_prio = -1 if image_url else 999
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
        if r.get("image_url"):
            prio = _IMG_PRIO.get(pname, 4)
            if prio < _image_prio:
                image_url = r["image_url"]
                _image_prio = prio

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

    catalog_key = entry.get("_key")
    siblings    = get_siblings(catalog_key)

    return {
        "name":       name,
        "sku":        sku,
        "confidence": confidence,
        "is_collab":  _is_collab(name),
        "image_url":  image_url,
        "platforms":  platforms,
        "arbitrage":  arbitrage,
        "siblings":   siblings,
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


@app.get("/api/suggest")
async def api_suggest(q: str = ""):
    from src.search import CATALOG, _ALIASES
    qs = q.strip().lower()
    if len(qs) < 2:
        return JSONResponse([])
    seen, out = set(), []
    for key, entry in CATALOG.items():
        nm = entry.get("name", "")
        if qs in nm.lower() and key not in seen:
            out.append({"name": nm, "hint": ""})
            seen.add(key)
    for key, entry in CATALOG.items():
        if qs in key.lower() and key not in seen:
            out.append({"name": entry.get("name", ""), "hint": key})
            seen.add(key)
    for alias, target in _ALIASES.items():
        if qs in alias.lower() and target not in seen:
            e = CATALOG.get(target, {})
            if e:
                out.append({"name": e.get("name", target), "hint": alias})
                seen.add(target)
    return JSONResponse(out[:7])


@app.get("/api/health")
async def api_health():
    from src.scraper import get_stats
    cache_size = len(_cache)
    if _redis:
        try:
            cache_size = _redis.dbsize()
        except Exception:
            pass
    return JSONResponse({
        "uptime_s":      round(time.time() - _START_TIME),
        "redis":         _redis is not None,
        "cache_size":    cache_size,
        "platform_stats": get_stats(),
    })


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
    from src.shopee_auth import save_cookie_to_supabase
    save_cookie_to_supabase(cookie)
    _COOKIE_FILE.write_text(cookie, encoding="utf-8")
    _cache.clear()
    if _redis:
        try:
            _redis.flushdb()
        except Exception:
            pass
    return JSONResponse({"ok": True, "length": len(cookie)})


@app.post("/admin/refresh-shopee-cookie")
async def refresh_shopee_cookie(x_admin_token: str = Header(default="")):
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    loop = asyncio.get_event_loop()

    def _do_refresh():
        from src.shopee_auth import refresh_cookie
        return refresh_cookie()

    cookie = await loop.run_in_executor(None, _do_refresh)
    if not cookie:
        raise HTTPException(status_code=500, detail="Playwright 登入失敗，請確認 SHOPEE_EMAIL / SHOPEE_PASSWORD")
    _cache.clear()
    if _redis:
        try:
            _redis.flushdb()
        except Exception:
            pass
    return JSONResponse({"ok": True, "length": len(cookie)})


@app.get("/admin/cookie-status")
async def cookie_status(x_admin_token: str = Header(default="")):
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from src.shopee_auth import load_cookie_from_supabase
    sb_cookie = load_cookie_from_supabase()
    if sb_cookie:
        return JSONResponse({"source": "supabase", "length": len(sb_cookie), "preview": sb_cookie[:40] + "…"})
    if _COOKIE_FILE.exists():
        c = _COOKIE_FILE.read_text(encoding="utf-8").strip()
        return JSONResponse({"source": "file", "length": len(c), "preview": c[:40] + "…"})
    return JSONResponse({"source": "env", "length": len(os.getenv("SHOPEE_COOKIE", ""))})


@app.on_event("startup")
async def startup():
    asyncio.create_task(_cache_warmer())


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
