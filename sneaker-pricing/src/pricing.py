"""定價計算機：輸入成本，自動加權匯率、運費、抽成，算出建議售價"""
from __future__ import annotations
from typing import Dict
import time
import requests

# 匯率快取（避免每次都打 API）
_rate_cache: Dict[str, float] = {}
_cache_time: float = 0
_CACHE_TTL = 3600  # 1 小時更新一次

# 備用固定匯率（API 無法連線時使用）
_FALLBACK_RATES: Dict[str, float] = {
    "JPY": 0.215,
    "USD": 32.5,
    "TWD": 1.0,
}

DEFAULT_SHIPPING = 300      # 運費（TWD）
DEFAULT_COMMISSION = 0.05   # 平台抽成 5%


def _fetch_rates() -> Dict[str, float]:
    """從 open.er-api.com 取得以 TWD 為基準的即時匯率"""
    global _rate_cache, _cache_time
    now = time.time()
    if _rate_cache and now - _cache_time < _CACHE_TTL:
        return _rate_cache

    try:
        res = requests.get("https://open.er-api.com/v6/latest/TWD", timeout=5)
        data = res.json()
        if data.get("result") == "success":
            rates_from_twd = data["rates"]
            # open.er-api 給的是 1 TWD → X 外幣，要反轉為 1 外幣 → TWD
            _rate_cache = {k: 1 / v for k, v in rates_from_twd.items() if v != 0}
            _rate_cache["TWD"] = 1.0
            _cache_time = now
            return _rate_cache
    except Exception:
        pass

    return _FALLBACK_RATES


def calculate_price(
    cost: float,
    currency: str = "TWD",
    shipping: float = DEFAULT_SHIPPING,
    commission_rate: float = DEFAULT_COMMISSION,
    margin_rate: float = 0.15,
) -> Dict:
    rates = _fetch_rates()
    rate = rates.get(currency.upper(), _FALLBACK_RATES.get(currency.upper(), 1.0))
    cost_twd = cost * rate
    total_cost = cost_twd + shipping
    suggested_price = total_cost / (1 - commission_rate - margin_rate)

    return {
        "cost_original": cost,
        "currency": currency.upper(),
        "cost_twd": round(cost_twd, 0),
        "shipping": shipping,
        "total_cost": round(total_cost, 0),
        "commission": round(suggested_price * commission_rate, 0),
        "margin": round(suggested_price * margin_rate, 0),
        "suggested_price": round(suggested_price, 0),
    }
