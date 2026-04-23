"""智能搜尋引擎：中文暱稱或 SKU 都能找到正確鞋款"""
from __future__ import annotations
from typing import Dict, Optional

# 格式：中文暱稱 → {sku, abc_keyword, yahoo_keyword, name}
CATALOG: Dict[str, Dict] = {
    # adidas
    # adidas
    "熊貓":      {"sku": "DV0831-101", "abc_keyword": "adidas FORUM",   "yahoo_keyword": "DV0831-101",          "pchome_keyword": "adidas Forum Low Panda DV0831",    "shopee_keyword": "adidas Forum Low Panda DV0831",   "name": "adidas Forum Low Panda"},
    "stan smith":{"sku": None,         "abc_keyword": "STAN SMITH",     "yahoo_keyword": "adidas Stan Smith",   "pchome_keyword": "adidas Stan Smith",                "shopee_keyword": "adidas Stan Smith",               "name": "adidas Stan Smith"},
    "斑馬":      {"sku": None,         "abc_keyword": None,             "yahoo_keyword": "Yeezy 350 Zebra",     "pchome_keyword": "Yeezy 350 V2 Zebra CP9654",        "shopee_keyword": "Yeezy 350 V2 Zebra",              "name": "adidas Yeezy Boost 350 V2 Zebra"},
    # Nike Dunk
    "芝加哥":    {"sku": "DD1391-100", "abc_keyword": "DUNK LOW",       "yahoo_keyword": "DD1391-100",          "pchome_keyword": "Nike Dunk Low Chicago DD1391",     "shopee_keyword": "Nike Dunk Low Chicago DD1391",    "name": "Nike Dunk Low Chicago"},
    "陰陽":      {"sku": "DH1901-105", "abc_keyword": "DUNK LOW",       "yahoo_keyword": "DH1901-105",          "pchome_keyword": "Nike Dunk Low Yin Yang DH1901",    "shopee_keyword": "Nike Dunk Low Yin Yang DH1901",   "name": "Nike Dunk Low Yin Yang"},
    "奧利奧":    {"sku": "CZ5607-051", "abc_keyword": "DUNK LOW",       "yahoo_keyword": "CZ5607-051",          "pchome_keyword": "Nike Dunk Low Black White CZ5607", "shopee_keyword": "Nike Dunk Low Black White",       "name": "Nike Dunk Low Black White"},
    "閃電":      {"sku": "DD1503-800", "abc_keyword": "DUNK LOW",       "yahoo_keyword": "DD1503-800",          "pchome_keyword": "Nike Dunk Low Syracuse DD1503",    "shopee_keyword": "Nike Dunk Low Syracuse",          "name": "Nike Dunk Low Syracuse"},
    # Air Jordan
    "倒鉤":      {"sku": "BQ6817-100", "abc_keyword": "AIR JORDAN 1",   "yahoo_keyword": "BQ6817-100",          "pchome_keyword": "Air Jordan 1 Retro High BQ6817",  "shopee_keyword": "Air Jordan 1 High 倒鉤",          "name": "Air Jordan 1 Retro High OG"},
    "大學藍":    {"sku": "555088-134", "abc_keyword": "AIR JORDAN 1",   "yahoo_keyword": "555088-134",          "pchome_keyword": "Air Jordan 1 University Blue",     "shopee_keyword": "Air Jordan 1 大學藍 University Blue", "name": "Air Jordan 1 Retro High OG University Blue"},
    "黑腳趾":    {"sku": "555088-125", "abc_keyword": "AIR JORDAN 1",   "yahoo_keyword": "555088-125",          "pchome_keyword": "Air Jordan 1 Black Toe 555088",    "shopee_keyword": "Air Jordan 1 黑腳趾",             "name": "Air Jordan 1 Retro High OG Black Toe"},
    # Air Force 1
    "空軍":      {"sku": "CW2288-111", "abc_keyword": "AIR FORCE 1",    "yahoo_keyword": "CW2288-111",          "pchome_keyword": "Nike Air Force 1 Low CW2288",      "shopee_keyword": "Nike Air Force 1 空軍",           "name": "Nike Air Force 1 Low '07"},
    "空軍一號":  {"sku": "CW2288-111", "abc_keyword": "AIR FORCE 1",    "yahoo_keyword": "CW2288-111",          "pchome_keyword": "Nike Air Force 1 Low CW2288",      "shopee_keyword": "Nike Air Force 1 空軍",           "name": "Nike Air Force 1 Low '07"},
    # New Balance
    "996":       {"sku": None,         "abc_keyword": "U996",           "yahoo_keyword": "New Balance 996",     "pchome_keyword": "New Balance 996",                  "shopee_keyword": "New Balance 996",                 "name": "New Balance 996"},
    "574":       {"sku": None,         "abc_keyword": "ML574",          "yahoo_keyword": "New Balance 574",     "pchome_keyword": "New Balance 574",                  "shopee_keyword": "New Balance 574",                 "name": "New Balance 574"},
    # Onitsuka Tiger
    "墨西哥":    {"sku": None,         "abc_keyword": None,             "yahoo_keyword": "Onitsuka Tiger Mexico 66", "pchome_keyword": "Onitsuka Tiger Mexico 66",    "shopee_keyword": "Onitsuka Tiger Mexico 66",        "name": "Onitsuka Tiger Mexico 66"},
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
        # 未知 SKU，只查 Nike 和 Yahoo，不查 ABC-MART
        return {"query": query, "sku": sku, "abc_keyword": None, "yahoo_keyword": sku, "name": sku}

    return None
