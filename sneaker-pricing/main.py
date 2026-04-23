"""球鞋定價助手 CLI"""

import argparse
from src.search import search_product
from src.scraper import scrape_abc_mart, scrape_nike, scrape_yahoo_auctions, scrape_pchome, scrape_shopee
from src.pricing import calculate_price


def cmd_search(args):
    result = search_product(args.query)
    if result is None:
        print(f"找不到鞋款：{args.query}")
        return

    sku = result.get("sku")
    abc_keyword = result.get("abc_keyword")
    yahoo_keyword = result.get("yahoo_keyword")
    print(f"\n鞋款：{result['name']}" + (f"  SKU: {sku}" if sku else ""))
    print("-" * 52)

    pchome_keyword = result.get("pchome_keyword")
    shopee_keyword = result.get("shopee_keyword")

    platforms = []
    if abc_keyword:
        platforms.append(scrape_abc_mart(abc_keyword))
    if sku:
        platforms.append(scrape_nike(sku))
    if yahoo_keyword:
        platforms.append(scrape_yahoo_auctions(yahoo_keyword))
    if pchome_keyword:
        platforms.append(scrape_pchome(pchome_keyword))
    if shopee_keyword:
        platforms.append(scrape_shopee(shopee_keyword))

    for data in platforms:
        price = data.get("price")
        status = data.get("status", "")
        currency = data.get("currency", "")
        if price is not None:
            extra = ""
            if "sample_count" in data:
                extra = f"  (n={data['sample_count']}, 最低 {data['price_min']:,} / 最高 {data['price_max']:,})"
            print(f"{data['platform']:16}  {price:>8,} {currency}{extra}")
        else:
            print(f"{data['platform']:16}  {'—':>8}  ({status})")
    print()


def cmd_price(args):
    result = calculate_price(
        cost=args.cost,
        currency=args.currency,
        shipping=args.shipping,
        commission_rate=args.commission,
        margin_rate=args.margin,
    )
    print(f"\n進貨成本：{result['cost_original']:,} {result['currency']}  "
          f"→  TWD {result['cost_twd']:,.0f}")
    print(f"運費：    TWD {result['shipping']:,.0f}")
    print(f"總成本：  TWD {result['total_cost']:,.0f}")
    print("-" * 30)
    print(f"建議售價：TWD {result['suggested_price']:,.0f}")
    print(f"  平台抽成 {result['commission']:,.0f}  /  毛利 {result['margin']:,.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="球鞋定價助手")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="搜尋鞋款價格")
    p_search.add_argument("query", help='鞋款名稱或 SKU，例如：熊貓、DD1391-100')

    p_price = sub.add_parser("price", help="計算建議售價")
    p_price.add_argument("--cost", type=float, required=True, help="進貨成本")
    p_price.add_argument("--currency", default="TWD", help="貨幣（JPY/USD/TWD）")
    p_price.add_argument("--shipping", type=float, default=300, help="運費（TWD）")
    p_price.add_argument("--commission", type=float, default=0.05, help="平台抽成（預設 0.05）")
    p_price.add_argument("--margin", type=float, default=0.15, help="目標毛利率（預設 0.15）")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "price":
        cmd_price(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
