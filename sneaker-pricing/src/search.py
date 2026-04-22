"""智能搜尋引擎：中文暱稱或 SKU 都能找到正確鞋款"""
from __future__ import annotations
from typing import Dict, Optional

# 格式：中文暱稱 → (Nike SKU, ABC-MART 關鍵字, 顯示名稱)
CATALOG: Dict[str, Dict] = {
    "熊貓":  {"sku": "DV0831-101", "abc_keyword": "adidas FORUM",   "name": "adidas Forum Low Panda"},
    "芝加哥": {"sku": "DD1391-100", "abc_keyword": "DUNK LOW",       "name": "Nike Dunk Low Chicago"},
    "陰陽":  {"sku": "DH1901-105", "abc_keyword": "DUNK LOW",       "name": "Nike Dunk Low Yin Yang"},
    "倒鉤":  {"sku": "BQ6817-100", "abc_keyword": "AIR JORDAN 1",   "name": "Air Jordan 1 Retro High OG"},
    "奧利奧": {"sku": "CZ5607-051", "abc_keyword": "DUNK LOW",       "name": "Nike Dunk Low Black White"},
    "996":   {"sku": None,         "abc_keyword": "U996",           "name": "New Balance 996"},
    "stan smith": {"sku": None,    "abc_keyword": "STAN SMITH",     "name": "adidas Stan Smith"},
}

# SKU → catalog 快速查詢
_SKU_INDEX: Dict[str, Dict] = {v["sku"]: v for v in CATALOG.values() if v["sku"]}


def search_product(query: str) -> Optional[Dict]:
    """輸入中文暱稱、SKU 或英文型號，回傳鞋款資訊"""
    q = query.strip()

    # 1. 先查中文別名
    entry = CATALOG.get(q) or CATALOG.get(q.lower())
    if entry:
        return {"query": query, **entry}

    # 2. 直接是 SKU 格式（含字母+數字，如 DD1391-100）
    if any(c.isalpha() for c in q) and any(c.isdigit() for c in q):
        sku = q.upper()
        known = _SKU_INDEX.get(sku)
        if known:
            return {"query": query, **known}
        # 未知 SKU，只查 Nike，不查 ABC-MART
        return {"query": query, "sku": sku, "abc_keyword": None, "name": sku}

    return None
