#!/usr/bin/env python3
"""每日熱榜同步：SNKRDUNK + Area02 前 20 名 → 自動補齊 catalog_auto.json"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rapidfuzz import process, fuzz

# ── 路徑 ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
AUTO_CATALOG = ROOT / "src" / "catalog_auto.json"


# ── 爬取函式 ──────────────────────────────────────────────────────────────────

def _launch_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ))
    return pw, browser, ctx


def scrape_snkrdunk() -> list[str]:
    """SNKRDUNK 熱門排行前 20 名（英文商品名）"""
    pw, browser, ctx = _launch_browser()
    names: list[str] = []
    try:
        page = ctx.new_page()
        page.goto("https://snkrdunk.com/en/sneakers/?sort=popular", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # 嘗試從 __NEXT_DATA__ 取結構化資料（Next.js 站點）
        next_data = page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent : null;
            }
        """)
        if next_data:
            try:
                data = json.loads(next_data)
                items = (data.get("props", {})
                              .get("pageProps", {})
                              .get("sneakers", [])
                         or data.get("props", {})
                              .get("pageProps", {})
                              .get("items", []))
                for item in items[:20]:
                    name = item.get("name") or item.get("title") or item.get("model_name")
                    if name:
                        names.append(str(name).strip())
                if names:
                    return names[:20]
            except Exception:
                pass

        # Fallback：直接抓頁面文字節點
        els = page.query_selector_all(
            "h2, h3, .product-name, [class*='item-name'], "
            "[class*='product_name'], [class*='sneaker-name'], "
            "[class*='title'][class*='product']"
        )
        seen: set[str] = set()
        for el in els:
            txt = el.inner_text().strip()
            if len(txt) > 5 and txt not in seen:
                seen.add(txt)
                names.append(txt)
                if len(names) >= 20:
                    break
    finally:
        browser.close()
        pw.stop()
    return names[:20]


def scrape_area02() -> list[str]:
    """Area02 熱銷商品前 20 名"""
    pw, browser, ctx = _launch_browser()
    names: list[str] = []
    try:
        page = ctx.new_page()
        # 嘗試 bestsellers collection（Shopify 常見路徑）
        for url in [
            "https://www.area02.com.tw/collections/best-sellers",
            "https://www.area02.com.tw/collections/bestsellers",
            "https://www.area02.com.tw/collections/popular",
            "https://www.area02.com.tw/",
        ]:
            try:
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                els = page.query_selector_all(
                    ".product-item__title, .product-card__title, "
                    ".product__title, [class*='product-title'], "
                    "h2.h3, h3.h4, .card__heading"
                )
                seen: set[str] = set()
                for el in els:
                    txt = el.inner_text().strip()
                    if len(txt) > 5 and txt not in seen:
                        seen.add(txt)
                        names.append(txt)
                if len(names) >= 5:
                    break
            except Exception:
                continue
    finally:
        browser.close()
        pw.stop()
    return names[:20]


# ── 名稱正規化 ────────────────────────────────────────────────────────────────

def _normalize(raw: str) -> str:
    """把爬來的商品名統一成 'Brand Model' 格式"""
    s = re.sub(r"\s+", " ", raw).strip()
    # 移除顏色後綴（常見括號格式）
    s = re.sub(r"\s*[\(\[（【].*?[\)\]）】]", "", s)
    return s


def _make_entry(name: str) -> dict:
    """依商品名生成 catalog entry"""
    kw = name.strip()
    brand_abc = None
    for brand in ("Nike", "adidas", "ASICS", "New Balance", "PUMA", "On Running"):
        if brand.lower() in kw.lower():
            brand_abc = brand.upper()
            break
    return {
        "sku": None,
        "abc_keyword": brand_abc,
        "yahoo_keyword": kw,
        "pchome_keyword": kw,
        "shopee_keyword": kw,
        "name": kw,
    }


# ── 比對邏輯 ──────────────────────────────────────────────────────────────────

def _already_covered(name: str, existing_names: list[str]) -> bool:
    result = process.extractOne(
        name.lower(),
        [n.lower() for n in existing_names],
        scorer=fuzz.partial_ratio,
        score_cutoff=80,
    )
    return result is not None


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    from src.search import CATALOG

    existing_names = [v["name"] for v in CATALOG.values()]
    corpus_keys    = [k for k in CATALOG]

    auto_catalog: dict = {}
    if AUTO_CATALOG.exists():
        try:
            auto_catalog = json.loads(AUTO_CATALOG.read_text(encoding="utf-8"))
        except Exception:
            pass

    added, skipped = [], []

    print("▶ 爬取 SNKRDUNK...")
    try:
        snkr_names = scrape_snkrdunk()
        print(f"  取得 {len(snkr_names)} 筆：{snkr_names[:5]}…")
    except Exception as e:
        print(f"  ⚠ SNKRDUNK 爬取失敗：{e}")
        snkr_names = []

    print("▶ 爬取 Area02...")
    try:
        area_names = scrape_area02()
        print(f"  取得 {len(area_names)} 筆：{area_names[:5]}…")
    except Exception as e:
        print(f"  ⚠ Area02 爬取失敗：{e}")
        area_names = []

    all_names = snkr_names + area_names
    for raw in all_names:
        name = _normalize(raw)
        if not name or len(name) < 5:
            continue

        # 已在手動 catalog 或 auto catalog 裡
        if _already_covered(name, existing_names + [v["name"] for v in auto_catalog.values()]):
            skipped.append(name)
            continue

        # 以小寫名稱作為 key
        key = name.lower()
        auto_catalog[key] = _make_entry(name)
        existing_names.append(name)
        added.append(name)

    # 寫回 JSON
    AUTO_CATALOG.write_text(
        json.dumps(auto_catalog, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n✅ 新增 {len(added)} 筆：")
    for n in added:
        print(f"   + {n}")
    print(f"⏭  略過（已收錄）{len(skipped)} 筆")
    print(f"📄 catalog_auto.json 共 {len(auto_catalog)} 筆")


if __name__ == "__main__":
    main()
