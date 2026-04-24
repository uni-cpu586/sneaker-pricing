# C&C 球鞋比價助手

## 專案概述
多平台球鞋比價工具，抓取蝦皮、PChome、Yahoo JP 等平台即時價格，部署在 Railway。

## 架構

```
sneaker-pricing/
├── sneaker-web/app.py      # FastAPI 主程式（PORT 8080，Railway 部署）
├── src/
│   ├── catalog_auto.json   # 商品目錄
│   ├── search.py           # 模糊搜尋邏輯
│   ├── scraper.py          # 各平台爬蟲
│   ├── pricing.py          # 價格整理與比較
│   ├── db.py               # Supabase 資料庫操作
│   └── trending.py         # 熱門排行邏輯
├── chrome-extension/       # Chrome MV3 Extension（蝦皮 Cookie 同步）
├── daily_trending.py       # 每日熱門排行爬蟲
└── Dockerfile              # python:3.11-slim，Railway 用
```

## 部署
- Railway，Dockerfile builder，容器內 PORT=8080
- URL: https://sneaker-pricing-production.up.railway.app
- domain targetPort 需設為 8080（已透過 Railway GraphQL API 設定，勿更動）

## 重要環境變數
- `ADMIN_TOKEN` — 保護 /admin/* 端點
- `SUPABASE_URL`, `SUPABASE_KEY` — 資料庫連線

## API 端點
- `GET /search?q=<keyword>` — 搜尋球鞋比價
- `POST /admin/update-shopee-cookie` — 更新蝦皮 cookie（Header: X-Admin-Token）
- `GET /admin/cookie-status` — 查看目前 cookie 狀態

## 程式碼規範
- Python 3.11，FastAPI + uvicorn
- 爬蟲用 ThreadPoolExecutor 並行執行
- Cache TTL 600 秒，key 為查詢字串
- 回傳統一格式：`{ name, platforms: [{platform, price, url}], collab, official }`

## 禁止事項
- 不要刪除 Railway domain 或更動 targetPort（已手動設定過）
- 不要修改 PORT 變數（Railway 自動注入）
