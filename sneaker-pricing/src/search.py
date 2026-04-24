"""智能搜尋引擎：支援中文暱稱、品牌名、部分比對、rapidfuzz 模糊搜尋"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CATALOG: Dict[str, Dict] = {
    # ── adidas ───────────────────────────────────────────────────────────────
    "熊貓":          {"sku": "DV0831-101", "abc_keyword": "adidas FORUM",    "yahoo_keyword": "DV0831-101",               "pchome_keyword": "adidas Forum Low Panda DV0831",      "shopee_keyword": "adidas Forum Low Panda DV0831",      "name": "adidas Forum Low Panda"},
    "stan smith":    {"sku": None,         "abc_keyword": "STAN SMITH",      "yahoo_keyword": "adidas Stan Smith",        "pchome_keyword": "adidas Stan Smith",                  "shopee_keyword": "adidas Stan Smith",                  "name": "adidas Stan Smith"},
    "斑馬":          {"sku": None,         "abc_keyword": None,              "yahoo_keyword": "Yeezy 350 Zebra",          "pchome_keyword": "Yeezy 350 V2 Zebra CP9654",          "shopee_keyword": "Yeezy 350 V2 Zebra",                 "name": "adidas Yeezy Boost 350 V2 Zebra"},
    "samba":         {"sku": "B75806",     "abc_keyword": "SAMBA OG",        "yahoo_keyword": "adidas Samba OG B75806",   "pchome_keyword": "adidas Samba OG",                    "shopee_keyword": "adidas Samba OG",                    "name": "adidas Samba OG",              "image_url": "https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy/3bbecbdf584e40398446a8bf0117cf62_9366/Samba_OG_Shoes_White_B75806_01_00_standard.jpg"},
    "campus":        {"sku": None,         "abc_keyword": "CAMPUS 00S",      "yahoo_keyword": "adidas Campus 00s",        "pchome_keyword": "adidas Campus 00s",                  "shopee_keyword": "adidas Campus 00s",                  "name": "adidas Campus 00s"},
    "gazelle":       {"sku": None,         "abc_keyword": "GAZELLE",         "yahoo_keyword": "adidas Gazelle",           "pchome_keyword": "adidas Gazelle",                     "shopee_keyword": "adidas Gazelle",                     "name": "adidas Gazelle"},
    # ── Nike Dunk ────────────────────────────────────────────────────────────
    "芝加哥":        {"sku": "DD1391-100", "abc_keyword": "DUNK LOW",        "yahoo_keyword": "DD1391-100",               "pchome_keyword": "Nike Dunk Low Chicago DD1391",        "shopee_keyword": "Nike Dunk Low Chicago DD1391",        "name": "Nike Dunk Low Chicago"},
    "陰陽":          {"sku": "DH1901-105", "abc_keyword": "DUNK LOW",        "yahoo_keyword": "DH1901-105",               "pchome_keyword": "Nike Dunk Low Yin Yang DH1901",       "shopee_keyword": "Nike Dunk Low Yin Yang DH1901",       "name": "Nike Dunk Low Yin Yang"},
    "奧利奧":        {"sku": "CZ5607-051", "abc_keyword": "DUNK LOW",        "yahoo_keyword": "CZ5607-051",               "pchome_keyword": "Nike Dunk Low Black White CZ5607",    "shopee_keyword": "Nike Dunk Low Black White",           "name": "Nike Dunk Low Black White"},
    "閃電":          {"sku": "DD1503-800", "abc_keyword": "DUNK LOW",        "yahoo_keyword": "DD1503-800",               "pchome_keyword": "Nike Dunk Low Syracuse DD1503",       "shopee_keyword": "Nike Dunk Low Syracuse",              "name": "Nike Dunk Low Syracuse"},
    "熊貓dunk":      {"sku": "DD1503-101", "abc_keyword": "DUNK LOW",        "yahoo_keyword": "Nike Dunk Low Panda DD1503-101", "pchome_keyword": "Nike Dunk Low Panda DD1503",   "shopee_keyword": "Nike Dunk Low Panda 熊貓",            "name": "Nike Dunk Low Panda"},
    # ── Nike Air Jordan ───────────────────────────────────────────────────────
    "倒鉤":          {"sku": "BQ6817-100", "abc_keyword": "AIR JORDAN 1",    "yahoo_keyword": "BQ6817-100",               "pchome_keyword": "Air Jordan 1 Retro High BQ6817",      "shopee_keyword": "Air Jordan 1 High 倒鉤",              "name": "Air Jordan 1 Retro High OG"},
    "大學藍":        {"sku": "555088-134", "abc_keyword": "AIR JORDAN 1",    "yahoo_keyword": "555088-134",               "pchome_keyword": "Air Jordan 1 University Blue",        "shopee_keyword": "Air Jordan 1 大學藍 University Blue", "name": "Air Jordan 1 Retro High OG University Blue"},
    "黑腳趾":        {"sku": "555088-125", "abc_keyword": "AIR JORDAN 1",    "yahoo_keyword": "555088-125",               "pchome_keyword": "Air Jordan 1 Black Toe 555088",       "shopee_keyword": "Air Jordan 1 黑腳趾",                 "name": "Air Jordan 1 Retro High OG Black Toe"},
    "AJ4":           {"sku": "FQ8213-006", "abc_keyword": "AIR JORDAN 4",    "yahoo_keyword": "Air Jordan 4 Retro",       "pchome_keyword": "Air Jordan 4 Retro",                 "shopee_keyword": "Air Jordan 4 Retro",                  "name": "Air Jordan 4 Retro"},
    # ── Nike Air Force 1 ──────────────────────────────────────────────────────
    "空軍":          {"sku": "CW2288-111", "abc_keyword": "AIR FORCE 1",     "yahoo_keyword": "CW2288-111",               "pchome_keyword": "Nike Air Force 1 Low CW2288",         "shopee_keyword": "Nike Air Force 1 空軍",               "name": "Nike Air Force 1 Low '07"},
    "空軍一號":      {"sku": "CW2288-111", "abc_keyword": "AIR FORCE 1",     "yahoo_keyword": "CW2288-111",               "pchome_keyword": "Nike Air Force 1 Low CW2288",         "shopee_keyword": "Nike Air Force 1 空軍",               "name": "Nike Air Force 1 Low '07"},
    # ── Nike Air Max ─────────────────────────────────────────────────────────
    "AM1":           {"sku": None,         "abc_keyword": "AIR MAX 1",       "yahoo_keyword": "Nike Air Max 1",           "pchome_keyword": "Nike Air Max 1",                     "shopee_keyword": "Nike Air Max 1",                      "name": "Nike Air Max 1"},
    "AM90":          {"sku": None,         "abc_keyword": "AIR MAX 90",      "yahoo_keyword": "Nike Air Max 90",          "pchome_keyword": "Nike Air Max 90",                    "shopee_keyword": "Nike Air Max 90",                     "name": "Nike Air Max 90"},
    "AM97":          {"sku": None,         "abc_keyword": "AIR MAX 97",      "yahoo_keyword": "Nike Air Max 97",          "pchome_keyword": "Nike Air Max 97",                    "shopee_keyword": "Nike Air Max 97",                     "name": "Nike Air Max 97"},
    # ── New Balance ───────────────────────────────────────────────────────────
    "530":           {"sku": None,         "abc_keyword": "MR530",           "yahoo_keyword": "New Balance 530",          "pchome_keyword": "New Balance 530",                    "shopee_keyword": "New Balance 530",                     "name": "New Balance 530"},
    "550":           {"sku": None,         "abc_keyword": "BB550",           "yahoo_keyword": "New Balance 550",          "pchome_keyword": "New Balance 550",                    "shopee_keyword": "New Balance 550",                     "name": "New Balance 550"},
    "574":           {"sku": None,         "abc_keyword": "ML574",           "yahoo_keyword": "New Balance 574",          "pchome_keyword": "New Balance 574",                    "shopee_keyword": "New Balance 574",                     "name": "New Balance 574"},
    "996":           {"sku": None,         "abc_keyword": "U996",            "yahoo_keyword": "New Balance 996",          "pchome_keyword": "New Balance 996",                    "shopee_keyword": "New Balance 996",                     "name": "New Balance 996"},
    "2002R":         {"sku": None,         "abc_keyword": "M2002R",          "yahoo_keyword": "New Balance 2002R",        "pchome_keyword": "New Balance 2002R",                  "shopee_keyword": "New Balance 2002R",                   "name": "New Balance 2002R"},
    "9060":          {"sku": None,         "abc_keyword": "U9060",           "yahoo_keyword": "New Balance 9060",         "pchome_keyword": "New Balance 9060",                   "shopee_keyword": "New Balance 9060",                    "name": "New Balance 9060"},
    "1906R":         {"sku": None,         "abc_keyword": "M1906R",          "yahoo_keyword": "New Balance 1906R",        "pchome_keyword": "New Balance 1906R",                  "shopee_keyword": "New Balance 1906R",                   "name": "New Balance 1906R"},
    # ── ASICS 金屬感復古跑鞋系列（完整）──────────────────────────────────────
    "gel-kayano 14": {"sku": None,         "abc_keyword": "GEL-KAYANO 14",   "yahoo_keyword": "ASICS Gel-Kayano 14",      "pchome_keyword": "ASICS Gel-Kayano 14",                "shopee_keyword": "ASICS Gel-Kayano 14",                 "name": "ASICS Gel-Kayano 14"},
    "kayano":        {"sku": None,         "abc_keyword": "GEL-KAYANO 14",   "yahoo_keyword": "ASICS Gel-Kayano 14",      "pchome_keyword": "ASICS Gel-Kayano 14",                "shopee_keyword": "ASICS Gel-Kayano 14",                 "name": "ASICS Gel-Kayano 14"},
    "gt-2160":       {"sku": None,         "abc_keyword": "GT-2160",         "yahoo_keyword": "ASICS GT-2160",            "pchome_keyword": "ASICS GT-2160",                      "shopee_keyword": "ASICS GT-2160",                       "name": "ASICS GT-2160"},
    "gel-nyc":       {"sku": None,         "abc_keyword": "GEL-NYC",         "yahoo_keyword": "ASICS Gel-NYC",            "pchome_keyword": "ASICS Gel-NYC",                      "shopee_keyword": "ASICS Gel-NYC",                       "name": "ASICS Gel-NYC"},
    "gel-1130":      {"sku": None,         "abc_keyword": "GEL-1130",        "yahoo_keyword": "ASICS Gel-1130",           "pchome_keyword": "ASICS Gel-1130",                     "shopee_keyword": "ASICS Gel-1130",                      "name": "ASICS Gel-1130"},
    "gel-nimbus 9":  {"sku": None,         "abc_keyword": "GEL-NIMBUS 9",    "yahoo_keyword": "ASICS Gel-Nimbus 9",       "pchome_keyword": "ASICS Gel-Nimbus 9",                 "shopee_keyword": "ASICS Gel-Nimbus 9",                  "name": "ASICS Gel-Nimbus 9"},
    "gel-lyte iii":  {"sku": None,         "abc_keyword": "GEL-LYTE III",    "yahoo_keyword": "ASICS Gel-Lyte III",       "pchome_keyword": "ASICS Gel-Lyte III",                 "shopee_keyword": "ASICS Gel-Lyte III",                  "name": "ASICS Gel-Lyte III"},
    "gel-cumulus 16":{"sku": None,         "abc_keyword": "GEL-CUMULUS 16",  "yahoo_keyword": "ASICS Gel-Cumulus 16",     "pchome_keyword": "ASICS Gel-Cumulus 16",               "shopee_keyword": "ASICS Gel-Cumulus 16",                "name": "ASICS Gel-Cumulus 16"},
    "gel-contend":   {"sku": None,         "abc_keyword": "GEL-CONTEND",     "yahoo_keyword": "ASICS Gel-Contend",        "pchome_keyword": "ASICS Gel-Contend",                  "shopee_keyword": "ASICS Gel-Contend",                   "name": "ASICS Gel-Contend"},
    # ── On 昂跑 ───────────────────────────────────────────────────────────────
    "cloud 5":       {"sku": None,         "abc_keyword": "CLOUD 5",         "yahoo_keyword": "On Running Cloud 5",       "pchome_keyword": "On Running Cloud 5",                 "shopee_keyword": "On Running Cloud 5 昂跑",             "name": "On Cloud 5"},
    "cloudmonster":  {"sku": None,         "abc_keyword": "CLOUDMONSTER",    "yahoo_keyword": "On Running Cloudmonster",  "pchome_keyword": "On Running Cloudmonster",            "shopee_keyword": "On Running Cloudmonster 昂跑",        "name": "On Cloudmonster"},
    "cloudsurfer":   {"sku": None,         "abc_keyword": "CLOUDSURFER",     "yahoo_keyword": "On Running Cloudsurfer",   "pchome_keyword": "On Cloudsurfer",                     "shopee_keyword": "On Running Cloudsurfer 昂跑",         "name": "On Cloudsurfer"},
    # ── PUMA ─────────────────────────────────────────────────────────────────
    "suede":         {"sku": None,         "abc_keyword": "SUEDE CLASSIC",   "yahoo_keyword": "PUMA Suede Classic",       "pchome_keyword": "PUMA Suede Classic",                 "shopee_keyword": "PUMA Suede Classic",                  "name": "PUMA Suede Classic"},
    "rs-x":          {"sku": None,         "abc_keyword": "RS-X",            "yahoo_keyword": "PUMA RS-X",                "pchome_keyword": "PUMA RS-X",                          "shopee_keyword": "PUMA RS-X",                           "name": "PUMA RS-X"},
    "palermo":       {"sku": None,         "abc_keyword": "PALERMO",         "yahoo_keyword": "PUMA Palermo",             "pchome_keyword": "PUMA Palermo",                       "shopee_keyword": "PUMA Palermo",                        "name": "PUMA Palermo"},
    "speedcat":      {"sku": None,         "abc_keyword": "SPEEDCAT",        "yahoo_keyword": "PUMA Speedcat",            "pchome_keyword": "PUMA Speedcat",                      "shopee_keyword": "PUMA Speedcat",                       "name": "PUMA Speedcat"},
    # ── Onitsuka Tiger ────────────────────────────────────────────────────────
    "墨西哥":        {"sku": None,         "abc_keyword": None,              "yahoo_keyword": "Onitsuka Tiger Mexico 66", "pchome_keyword": "Onitsuka Tiger Mexico 66",            "shopee_keyword": "Onitsuka Tiger Mexico 66",            "name": "Onitsuka Tiger Mexico 66"},
    "ultimate 81":   {"sku": None,         "abc_keyword": None,              "yahoo_keyword": "Onitsuka Tiger Ultimate 81","pchome_keyword": "Onitsuka Tiger Ultimate 81",         "shopee_keyword": "Onitsuka Tiger Ultimate 81",          "name": "Onitsuka Tiger Ultimate 81"},

    # ── 拖鞋與涼鞋 ───────────────────────────────────────────────────────────
    "birkenstock boston":      {"sku": None, "abc_keyword": None, "yahoo_keyword": "Birkenstock Boston",           "pchome_keyword": "Birkenstock Boston",                 "shopee_keyword": "Birkenstock Boston 勃肯",             "name": "Birkenstock Boston"},
    "birkenstock arizona":     {"sku": None, "abc_keyword": None, "yahoo_keyword": "Birkenstock Arizona",          "pchome_keyword": "Birkenstock Arizona",                "shopee_keyword": "Birkenstock Arizona 勃肯",            "name": "Birkenstock Arizona"},
    "birkenstock boston soft":  {"sku": None, "abc_keyword": None, "yahoo_keyword": "Birkenstock Boston Soft Footbed","pchome_keyword": "Birkenstock Boston Soft",           "shopee_keyword": "Birkenstock Boston 軟底",             "name": "Birkenstock Boston Soft Footbed"},
    "crocs classic":           {"sku": None, "abc_keyword": None, "yahoo_keyword": "Crocs Classic Clog",           "pchome_keyword": "Crocs Classic Clog",                 "shopee_keyword": "Crocs Classic Clog 卡駱馳",           "name": "Crocs Classic Clog"},
    "crocs salehe":            {"sku": None, "abc_keyword": None, "yahoo_keyword": "Crocs x Salehe Bembury Pollex", "pchome_keyword": "Crocs Salehe Bembury",               "shopee_keyword": "Crocs Salehe Bembury Pollex",         "name": "Crocs x Salehe Bembury Pollex Clog"},
    "crocs bad bunny":         {"sku": None, "abc_keyword": None, "yahoo_keyword": "Crocs x Bad Bunny",            "pchome_keyword": "Crocs Bad Bunny",                    "shopee_keyword": "Crocs Bad Bunny 聯名",                "name": "Crocs x Bad Bunny Classic Clog"},
    "nike calm slide":         {"sku": None, "abc_keyword": None, "yahoo_keyword": "Nike Calm Slide",              "pchome_keyword": "Nike Calm Slide",                    "shopee_keyword": "Nike Calm Slide",                     "name": "Nike Calm Slide"},
    "adilette 22":             {"sku": None, "abc_keyword": "ADILETTE 22",    "yahoo_keyword": "adidas Adilette 22",       "pchome_keyword": "adidas Adilette 22",                 "shopee_keyword": "adidas Adilette 22",                  "name": "adidas Adilette 22"},
    "ugg tazz":                {"sku": None, "abc_keyword": None, "yahoo_keyword": "UGG Tazz",                     "pchome_keyword": "UGG Tazz",                           "shopee_keyword": "UGG Tazz 厚底",                       "name": "UGG Tazz"},
    "ugg ultra mini":          {"sku": None, "abc_keyword": None, "yahoo_keyword": "UGG Ultra Mini Boot",          "pchome_keyword": "UGG Ultra Mini",                     "shopee_keyword": "UGG Ultra Mini Boot",                 "name": "UGG Ultra Mini Boot"},

    # ── 聯名特區 ─────────────────────────────────────────────────────────────
    "a ma maniere dunk":       {"sku": "DX2931-101", "abc_keyword": "DUNK LOW",      "yahoo_keyword": "Nike Dunk Low A Ma Maniére DX2931",    "pchome_keyword": "Nike Dunk Low A Ma Maniére",         "shopee_keyword": "Nike Dunk Low A Ma Maniére 聯名",     "name": "Nike Dunk Low x A Ma Maniére"},
    "travis scott aj1":        {"sku": "CD4487-100", "abc_keyword": "AIR JORDAN 1",  "yahoo_keyword": "Travis Scott Air Jordan 1 CD4487",     "pchome_keyword": "Air Jordan 1 Travis Scott",          "shopee_keyword": "Air Jordan 1 Travis Scott 聯名",      "name": "Air Jordan 1 x Travis Scott"},
    "travis scott aj1 fragment":{"sku": "DA7729-100","abc_keyword": "AIR JORDAN 1",  "yahoo_keyword": "Travis Scott Fragment Air Jordan 1",   "pchome_keyword": "Air Jordan 1 Travis Scott Fragment", "shopee_keyword": "Air Jordan 1 Travis Scott Fragment",  "name": "Air Jordan 1 x Travis Scott x Fragment"},
    "travis scott aj4":        {"sku": "CV6690-900", "abc_keyword": "AIR JORDAN 4",  "yahoo_keyword": "Travis Scott Air Jordan 4 Cactus Jack","pchome_keyword": "Air Jordan 4 Travis Scott",          "shopee_keyword": "Air Jordan 4 Travis Scott Cactus Jack","name": "Air Jordan 4 x Travis Scott Cactus Jack"},
    "ald 550":                 {"sku": None,         "abc_keyword": "BB550",         "yahoo_keyword": "New Balance 550 Aime Leon Dore",        "pchome_keyword": "New Balance 550 ALD",                "shopee_keyword": "New Balance 550 ALD Aime Leon Dore",  "name": "New Balance 550 x Aime Leon Dore"},
    "ald 990v6":               {"sku": None,         "abc_keyword": "U990",          "yahoo_keyword": "New Balance 990v6 Aime Leon Dore",      "pchome_keyword": "New Balance 990v6 ALD",              "shopee_keyword": "New Balance 990v6 ALD",               "name": "New Balance 990v6 x Aime Leon Dore"},
    "bad bunny samba":         {"sku": None,         "abc_keyword": "SAMBA",         "yahoo_keyword": "adidas Samba Bad Bunny",                "pchome_keyword": "adidas Samba Bad Bunny",             "shopee_keyword": "adidas Samba Bad Bunny 聯名",         "name": "adidas Samba x Bad Bunny"},
    "bad bunny response":      {"sku": None,         "abc_keyword": None,            "yahoo_keyword": "adidas Response Bad Bunny",             "pchome_keyword": "adidas Response Bad Bunny",          "shopee_keyword": "adidas Response CL Bad Bunny",        "name": "adidas Response CL x Bad Bunny"},
    "off white dunk":          {"sku": "DM1602-100", "abc_keyword": "DUNK LOW",      "yahoo_keyword": "Off-White Nike Dunk Low DM1602",        "pchome_keyword": "Nike Dunk Low Off-White",            "shopee_keyword": "Nike Dunk Low Off-White 聯名",        "name": "Nike Dunk Low x Off-White"},
    "sacai ld waffle":         {"sku": None,         "abc_keyword": None,            "yahoo_keyword": "Nike Sacai LD Waffle",                  "pchome_keyword": "Nike LDWaffle Sacai",                "shopee_keyword": "Nike LDWaffle Sacai 聯名",            "name": "Nike LDWaffle x Sacai"},
    "pharrell stan smith":     {"sku": None,         "abc_keyword": "STAN SMITH",    "yahoo_keyword": "adidas Stan Smith Pharrell Williams",   "pchome_keyword": "adidas Stan Smith Pharrell",         "shopee_keyword": "adidas Stan Smith Pharrell 聯名",     "name": "adidas Stan Smith x Pharrell Williams"},
    "fog 1":                   {"sku": None,         "abc_keyword": None,            "yahoo_keyword": "Fear of God Athletics 86 Runner",       "pchome_keyword": "Fear of God 86 Runner",              "shopee_keyword": "Fear of God Athletics 86 Runner FOG", "name": "Fear of God Athletics 86 Runner"},
}

# SKU → catalog 快速查詢
_SKU_INDEX: Dict[str, Dict] = {v["sku"]: v for v in CATALOG.values() if v["sku"]}

# ── 中文別名 → CATALOG key ────────────────────────────────────────────────────
_ALIASES: Dict[str, str] = {
    # adidas
    "椰子":         "斑馬",
    "yeezy 斑馬":   "斑馬",
    "yeezy zebra":  "斑馬",
    "森巴":         "samba",
    "森巴鞋":       "samba",
    # Nike
    "喬一":         "倒鉤",
    "aj1":          "倒鉤",
    "aj1 倒鉤":     "倒鉤",
    "aj4":          "AJ4",
    "air jordan 4": "AJ4",
    "熊貓dunk":     "熊貓dunk",
    "熊貓 dunk":    "熊貓dunk",
    "panda dunk":   "熊貓dunk",
    "dunk panda":   "熊貓dunk",
    "nike panda":   "熊貓dunk",
    "nike dunk panda": "熊貓dunk",
    "air force":    "空軍",
    "air force 1":  "空軍",
    "af1":          "空軍",
    "air max 1":    "AM1",
    "air max 90":   "AM90",
    "air max 97":   "AM97",
    # New Balance
    "nb530":  "530",
    "nb 530": "530",
    "nb550":  "550",
    "nb 550": "550",
    "nb574":  "574",
    "nb 574": "574",
    "nb996":  "996",
    "nb 996": "996",
    "nb2002":  "2002R",
    "nb 2002": "2002R",
    "nb9060":  "9060",
    "nb 9060": "9060",
    "nb1906":  "1906R",
    "nb 1906": "1906R",
    # ASICS
    "凱亞諾":       "gel-kayano 14",
    "gk14":         "gel-kayano 14",
    "k14":          "gel-kayano 14",
    "kayano 14":    "gel-kayano 14",
    "gt2160":       "gt-2160",
    "2160":         "gt-2160",
    "gel nyc":      "gel-nyc",
    "nyc":          "gel-nyc",
    "gel 1130":     "gel-1130",
    "1130":         "gel-1130",
    "nimbus 9":     "gel-nimbus 9",
    "lyte 3":       "gel-lyte iii",
    "gel lyte":     "gel-lyte iii",
    "cumulus 16":   "gel-cumulus 16",
    # 拖鞋
    "勃肯":         "birkenstock boston",
    "boston":       "birkenstock boston",
    "arizona":      "birkenstock arizona",
    "crocs":        "crocs classic",
    "卡駱馳":       "crocs classic",
    "pollex":       "crocs salehe",
    "calm slide":   "nike calm slide",
    "adilette":     "adilette 22",
    "ugg":          "ugg tazz",
    "tazz":         "ugg tazz",
    # 聯名
    "ama dunk":     "a ma maniere dunk",
    "a ma":         "a ma maniere dunk",
    "travis aj1":   "travis scott aj1",
    "travis fragment": "travis scott aj1 fragment",
    "reverse mocha": "travis scott aj1",
    "travis aj4":   "travis scott aj4",
    "cactus jack":  "travis scott aj4",
    "ald":          "ald 550",
    "aime leon dore": "ald 550",
    "bad bunny samba": "bad bunny samba",
    "off white":    "off white dunk",
    "ow dunk":      "off white dunk",
    "sacai":        "sacai ld waffle",
    "ld waffle":    "sacai ld waffle",
    "pharrell":     "pharrell stan smith",
    "fog":          "fog 1",
    "86 runner":    "fog 1",
    # On
    "cloud5":       "cloud 5",
    "昂跑cloud":    "cloud 5",
    # PUMA
    "suede classic": "suede",
    "speedcat puma": "speedcat",
}

# ── 中文品牌名 → 英文品牌前綴（用於品牌+關鍵字搜尋）────────────────────────
_BRAND_CN: Dict[str, str] = {
    "耐吉":  "nike",
    "愛迪達": "adidas",
    "亞瑟士": "asics",
    "昂跑":  "on",
    "彪馬":  "puma",
    "新百倫": "new balance",
    "nb":    "new balance",
    "勃肯鞋": "birkenstock",
}

# ── 品牌前綴（長的放前面，避免 "new balance" 被 "nb" 先截到）──────────────
_BRAND_PREFIXES: List[Tuple[str, str]] = [
    ("new balance", "new balance"),
    ("adidas originals", "adidas"),
    ("adidas yeezy",    "adidas"),
    ("adidas",          "adidas"),
    ("air jordan",      "nike"),
    ("nike",            "nike"),
    ("onitsuka tiger",  "onitsuka tiger"),
    ("asics",           "asics"),
    ("puma",            "puma"),
    ("on running",      "on"),
    ("birkenstock",     "birkenstock"),
    ("crocs",           "crocs"),
    ("ugg",             "ugg"),
    ("fear of god",     "fog"),
    # 縮寫
    ("nb",              "new balance"),
    ("aj",              "nike"),
]

_COLLAB_RE = re.compile(r'^(.+?)\s+x\s+(.+)$', re.IGNORECASE)

# ── 配色家族分組 ──────────────────────────────────────────────────────────────
_FAMILY_GROUPS: Dict[str, List[tuple]] = {
    "dunk": [
        ("芝加哥",            "芝加哥"),
        ("陰陽",              "陰陽"),
        ("奧利奧",            "奧利奧"),
        ("閃電",              "閃電"),
        ("熊貓dunk",          "熊貓"),
        ("a ma maniere dunk", "A Ma"),
        ("off white dunk",    "Off-White"),
    ],
    "aj1": [
        ("倒鉤",                      "倒鉤"),
        ("大學藍",                    "大學藍"),
        ("黑腳趾",                    "黑腳趾"),
        ("travis scott aj1",          "Travis"),
        ("travis scott aj1 fragment", "Fragment"),
    ],
    "aj4": [
        ("AJ4",              "基本款"),
        ("travis scott aj4", "Travis"),
    ],
    "samba": [
        ("samba",           "OG"),
        ("bad bunny samba", "Bad Bunny"),
    ],
    "nb": [
        ("530",      "530"),
        ("550",      "550"),
        ("574",      "574"),
        ("996",      "996"),
        ("2002R",    "2002R"),
        ("9060",     "9060"),
        ("1906R",    "1906R"),
        ("ald 550",  "550 ALD"),
        ("ald 990v6","990v6 ALD"),
    ],
    "birkenstock": [
        ("birkenstock boston",      "Boston"),
        ("birkenstock arizona",     "Arizona"),
        ("birkenstock boston soft", "Boston 軟底"),
    ],
    "crocs": [
        ("crocs classic",   "Classic"),
        ("crocs salehe",    "Salehe"),
        ("crocs bad bunny", "Bad Bunny"),
    ],
    "ugg": [
        ("ugg tazz",      "Tazz"),
        ("ugg ultra mini", "Ultra Mini"),
    ],
}

_KEY_TO_FAMILY: Dict[str, Tuple[str, str]] = {
    key: (family, label)
    for family, members in _FAMILY_GROUPS.items()
    for key, label in members
}


def get_siblings(catalog_key: Optional[str]) -> List[Dict]:
    """回傳同家族的其他配色（不含自身），沒有家族則回傳空列表"""
    if not catalog_key or catalog_key not in _KEY_TO_FAMILY:
        return []
    family, _ = _KEY_TO_FAMILY[catalog_key]
    result = []
    for key, label in _FAMILY_GROUPS[family]:
        entry = CATALOG.get(key)
        if entry and key != catalog_key:
            result.append({"key": key, "name": entry["name"], "label": label})
    return result


def _extract_anchors(q: str) -> List[str]:
    """提取 Anchor Token：品牌 + 數字型號，命中條目的名稱必須同時包含所有 anchor"""
    anchors: List[str] = []
    brand = _extract_brand(q)
    if brand:
        anchors.append(brand)
    anchors.extend(re.findall(r'\b\d{2,}\b', q))
    return anchors


def _extract_brand(q: str) -> Optional[str]:
    """從查詢字串頭部提取品牌名（小寫標準化），找不到回傳 None"""
    for prefix, brand in _BRAND_PREFIXES:
        if q.startswith(prefix + " ") or q == prefix:
            return brand
    return None


def _make_dynamic_entry(name: str) -> Dict:
    """為 catalog 中沒有的鞋款（尤其是聯名）動態生成搜尋條目"""
    # 去掉 "Originals"、"Running" 等冗詞，讓關鍵字更精準
    kw = re.sub(r'\b(originals|running|athletics)\b', '', name, flags=re.IGNORECASE)
    kw = re.sub(r'\s{2,}', ' ', kw).strip()
    return {
        "name": name,
        "sku": None,
        "abc_keyword": None,
        "yahoo_keyword": kw,
        "pchome_keyword": kw,
        "shopee_keyword": kw,
    }


# ── 載入自動爬取的 catalog（不覆蓋手動條目）───────────────────────────────
_AUTO_CATALOG_PATH = Path(__file__).parent / "catalog_auto.json"
try:
    _auto = json.loads(_AUTO_CATALOG_PATH.read_text(encoding="utf-8"))
    for _k, _v in _auto.items():
        if _k not in CATALOG:
            CATALOG[_k] = _v
except Exception:
    pass


def _build_corpus() -> tuple[list[str], list[str]]:
    """建立 rapidfuzz 搜尋語料庫：(可搜尋字串列表, 對應 catalog key 列表)"""
    strings, keys = [], []
    for key, entry in CATALOG.items():
        strings.append(key.lower());         keys.append(key)
        strings.append(entry["name"].lower()); keys.append(key)
    for alias, target in _ALIASES.items():
        strings.append(alias.lower());       keys.append(target)
    return strings, keys


_CORPUS_STR, _CORPUS_KEY = _build_corpus()


def search_product(query: str) -> Optional[Dict]:
    """輸入中文暱稱、品牌名、英文型號或 SKU，回傳鞋款資訊"""
    q = query.strip()
    q_lower = q.lower()

    # 1. 直接比對 catalog key
    _k1 = q if q in CATALOG else (q_lower if q_lower in CATALOG else None)
    entry = CATALOG.get(_k1) if _k1 else None
    if entry:
        return {"query": query, "_key": _k1, **entry}

    # 2. 中文別名查詢
    alias_key = _ALIASES.get(q_lower)
    if alias_key:
        entry = CATALOG.get(alias_key)
        if entry:
            return {"query": query, "_key": alias_key, **entry}

    # 3. SKU 格式（ASCII 字母 + 數字 + 無空格，如 DD1391-100）
    if " " not in q and any(c.isascii() and c.isalpha() for c in q) and any(c.isdigit() for c in q):
        sku = q.upper()
        known = _SKU_INDEX.get(sku)
        if known:
            _sku_k = next((k for k, v in CATALOG.items() if v is known), None)
            return {"query": query, "_key": _sku_k, **known}
        return {"query": query, "_key": None, "sku": sku, "abc_keyword": None,
                "yahoo_keyword": sku, "name": sku}

    # 4. 子字串比對（catalog key 或商品名稱包含查詢詞）
    for key, entry in CATALOG.items():
        if q_lower in key.lower() or q_lower in entry["name"].lower():
            return {"query": query, "_key": key, **entry}

    # 5. 中文品牌名 + 關鍵字
    for cn_brand, en_brand in _BRAND_CN.items():
        if cn_brand in q_lower:
            rest = q_lower.replace(cn_brand, "").strip()
            for key, entry in CATALOG.items():
                if en_brand in entry["name"].lower():
                    if not rest or rest in key.lower() or rest in entry["name"].lower():
                        return {"query": query, "_key": key, **entry}

    # 6. rapidfuzz 模糊比對（品牌隔離 + 嚴格 scorer）
    try:
        from rapidfuzz import process, fuzz

        brand = _extract_brand(q_lower)

        if brand:
            # 只在同品牌條目中搜尋，防止跨品牌誤配
            pairs = [
                (s, k) for s, k in zip(_CORPUS_STR, _CORPUS_KEY)
                if brand in CATALOG.get(k, {}).get("name", "").lower()
            ]
        else:
            pairs = list(zip(_CORPUS_STR, _CORPUS_KEY))

        if pairs:
            corp_str, corp_key = zip(*pairs)
            result = process.extractOne(
                q_lower, corp_str,
                scorer=fuzz.token_sort_ratio,  # 對詞序不敏感，聯名款更準
                score_cutoff=78,
            )
            if result:
                _, score, idx = result
                matched_key = corp_key[idx]
                entry = CATALOG.get(matched_key)
                if entry:
                    # 額外保護：query 含 "x collab" 但命中條目沒有聯名，不採用
                    has_collab_query = " x " in q_lower
                    has_collab_entry = " x " in entry.get("name", "").lower()
                    if has_collab_query and not has_collab_entry:
                        pass  # 跳過，進入動態生成
                    else:
                        # Anchor token 驗證：品牌 + 數字型號必須出現在結果名稱中
                        anchors = _extract_anchors(q_lower)
                        if all(a in entry.get("name", "").lower() for a in anchors):
                            return {"query": query, "_key": matched_key, "confidence": score, **entry}
    except ImportError:
        pass

    # 7. 動態條目：未知聯名款 / 沒有 catalog 條目的查詢
    #    讓各平台用原始關鍵字自行搜尋，而不是回傳 None
    if _extract_brand(q_lower) or _COLLAB_RE.match(q):
        return {"query": query, "_key": None, **_make_dynamic_entry(query)}

    return None
