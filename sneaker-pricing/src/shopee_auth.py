"""蝦皮 Cookie 管理：Playwright 登入 + Supabase 持久化"""
from __future__ import annotations
import os
import time
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Supabase ────────────────────────────────────────────────────────────────

def _sb():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def load_cookie_from_supabase() -> Optional[str]:
    try:
        res = _sb().table("platform_cookies").select("cookie").eq("platform", "shopee_tw").execute()
        if res.data:
            return res.data[0]["cookie"]
    except Exception as e:
        logger.warning("Supabase cookie 讀取失敗: %s", e)
    return None


def save_cookie_to_supabase(cookie: str) -> bool:
    try:
        _sb().table("platform_cookies").upsert({
            "platform":   "shopee_tw",
            "cookie":     cookie,
            "updated_at": "now()",
        }).execute()
        return True
    except Exception as e:
        logger.error("Supabase cookie 寫入失敗: %s", e)
        return False


# ── Playwright 登入 ──────────────────────────────────────────────────────────

def playwright_login() -> Optional[str]:
    """用 Playwright 登入蝦皮，回傳 cookie 字串；未安裝 playwright 或失敗回傳 None"""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("playwright 未安裝，略過自動登入（請在本機執行 scripts/shopee_login.py）")
        return None

    email    = os.getenv("SHOPEE_EMAIL", "")
    password = os.getenv("SHOPEE_PASSWORD", "")
    if not email or not password:
        logger.error("未設定 SHOPEE_EMAIL / SHOPEE_PASSWORD")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="zh-TW",
        )
        page = ctx.new_page()
        try:
            page.goto("https://shopee.tw/buyer/login", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_selector("input[name='loginKey']", timeout=10000)
            page.fill("input[name='loginKey']", email)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")

            # 等待登入成功（導向首頁或出現 user avatar）
            try:
                page.wait_for_url("https://shopee.tw/", timeout=15000)
            except PWTimeout:
                page.wait_for_selector(".shopee-avatar", timeout=10000)

            cookies = ctx.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            browser.close()
            return cookie_str if cookie_str else None

        except Exception as e:
            logger.error("Playwright 登入失敗: %s", e)
            browser.close()
            return None


# ── 公開 API ─────────────────────────────────────────────────────────────────

def get_cookie() -> str:
    """依序嘗試：Supabase → 本地檔案 → env var；全部空則回傳空字串"""
    # 1. Supabase
    if os.getenv("SUPABASE_URL"):
        c = load_cookie_from_supabase()
        if c:
            return c

    # 2. 本地檔案（開發環境 fallback）
    from pathlib import Path
    cookie_file = Path(__file__).parent.parent / "shopee_cookie.txt"
    if cookie_file.exists():
        c = cookie_file.read_text(encoding="utf-8").strip()
        if c:
            return c

    # 3. env var
    return os.getenv("SHOPEE_COOKIE", "").strip()


def refresh_cookie() -> Optional[str]:
    """Playwright 重新登入，成功後存入 Supabase，回傳 cookie；失敗回傳 None"""
    cookie = playwright_login()
    if cookie:
        save_cookie_to_supabase(cookie)
    return cookie
