#!/usr/bin/env python3
"""每日熱銷榜 sync：SNKRDUNK + Area02 → Supabase 待審核清單

Supabase 需先建立 pending_review 資料表：
  CREATE TABLE pending_review (
    id         SERIAL PRIMARY KEY,
    sku        TEXT,
    name       TEXT NOT NULL,
    source     TEXT NOT NULL,
    rank       INTEGER,
    price      INTEGER,
    status     TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
"""
import os
from dotenv import load_dotenv
from src.trending import fetch_snkrdunk_ranking, fetch_area02_ranking

load_dotenv()


def main() -> None:
    print("=== 每日熱銷榜 Sync ===")

    snkr = fetch_snkrdunk_ranking(20)
    print(f"[SNKRDUNK] 抓到 {len(snkr)} 筆")
    for i in snkr:
        print(f"  #{i['rank']:>2} {i['sku']:<15} {i['name'][:40]}")

    area = fetch_area02_ranking(20)
    print(f"[Area02]   抓到 {len(area)} 筆")
    for i in area:
        print(f"  #{i['rank']:>2} {str(i['sku']):<15} {i['name'][:40]}")

    all_items = snkr + area

    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")):
        print("\n[DB] 未設定 Supabase 環境變數，略過寫入")
        return

    from src.db import get_existing_skus, save_pending_review

    existing = get_existing_skus()
    print(f"\n[DB] 現有 {len(existing)} 個已知 SKU")

    new_items = [
        item for item in all_items
        if item.get("sku") and item["sku"].upper() not in existing
    ]

    if new_items:
        count = save_pending_review(new_items)
        print(f"[DB] 新增 {count} 筆至待審核清單：")
        for item in new_items:
            print(f"  [{item['source']}] #{item['rank']} {item['sku']} — {item['name'][:40]}")
    else:
        print("[DB] 無新 SKU，待審核清單未更新")


if __name__ == "__main__":
    main()
