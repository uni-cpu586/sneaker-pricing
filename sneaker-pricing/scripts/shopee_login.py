"""
本機執行：用 Playwright 登入蝦皮，把 cookie 存進 Supabase

用法：
  pip install playwright
  playwright install chromium
  python scripts/shopee_login.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from playwright.sync_api import sync_playwright

SHOPEE_EMAIL    = os.getenv("SHOPEE_EMAIL", "")
SHOPEE_PASSWORD = os.getenv("SHOPEE_PASSWORD", "")


def login_and_save():
    if not SHOPEE_EMAIL or not SHOPEE_PASSWORD:
        print("請先在 .env 設定 SHOPEE_EMAIL 和 SHOPEE_PASSWORD")
        sys.exit(1)

    print("啟動瀏覽器…")
    with sync_playwright() as p:
        # headless=False 方便手動處理 CAPTCHA / 簡訊驗證
        browser = p.chromium.launch(headless=False)
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
        page.goto("https://shopee.tw/buyer/login", wait_until="domcontentloaded")
        page.wait_for_selector("input[name='loginKey']")
        page.fill("input[name='loginKey']", SHOPEE_EMAIL)
        page.fill("input[name='password']", SHOPEE_PASSWORD)
        page.click("button[type='submit']")

        print("等待登入完成（如果有 CAPTCHA 請手動處理）…")
        # 等待導向首頁，最多 60 秒讓使用者處理驗證
        try:
            page.wait_for_url("https://shopee.tw/", timeout=60000)
        except Exception:
            input("瀏覽器未自動跳轉，手動確認登入後按 Enter 繼續…")

        cookies = ctx.cookies()
        browser.close()

    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    if not cookie_str:
        print("取得 cookie 失敗")
        sys.exit(1)

    print(f"取得 cookie（{len(cookie_str)} 字元），儲存到 Supabase…")
    from src.shopee_auth import save_cookie_to_supabase
    ok = save_cookie_to_supabase(cookie_str)
    if ok:
        print("完成！Railway 下次請求蝦皮時會自動使用新 cookie。")
    else:
        print("Supabase 寫入失敗，請確認 SUPABASE_URL / SUPABASE_SERVICE_KEY")


if __name__ == "__main__":
    login_and_save()
