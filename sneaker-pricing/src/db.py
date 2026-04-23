"""Supabase 寫入器：把 scraper 結果存進資料庫"""
from __future__ import annotations
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client


def get_or_create_sneaker(name: str, sku: Optional[str]) -> int:
    sb = _get_client()
    if sku:
        res = sb.table("sneakers").select("id").eq("sku", sku).execute()
        if res.data:
            return res.data[0]["id"]
    res = sb.table("sneakers").select("id").eq("name", name).execute()
    if res.data:
        return res.data[0]["id"]
    res = sb.table("sneakers").insert({"name": name, "sku": sku}).execute()
    return res.data[0]["id"]


def save_prices(sneaker_id: int, platform_results: List[Dict]) -> None:
    sb = _get_client()
    rows = []
    for r in platform_results:
        rows.append({
            "sneaker_id": sneaker_id,
            "platform": r["platform"],
            "price": r.get("price"),
            "currency": r.get("currency", "TWD"),
            "price_min": r.get("price_min"),
            "price_max": r.get("price_max"),
            "sample_count": r.get("sample_count"),
            "status": r.get("status", "ok"),
            "url": r.get("url"),
        })
    if rows:
        sb.table("prices").insert(rows).execute()
