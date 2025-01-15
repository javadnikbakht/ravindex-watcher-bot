import asyncio
from datetime import datetime, timedelta

import requests
from decouple import config
from telegram import Bot

LEAST_DESIRED_DELTA = config("LEAST_DESIRED_DELTA", 0.8, cast=float)
LEAST_COVERED_CALL_PROFIT = config("LEAST_COVERED_CALL_PROFIT", 60, cast=int)

POLLING_INTERVAL_MINUTES = config("POLLING_INTERVAL_MINUTES", 5, cast=int)

RAVINDEX_API_URL = "https://api.ravindex.ir/graphql"

RAVINDEX_OUTPUT_DATE_FORMAT = "%Y-%m-%d"
RAVINDEX_ACCESS_TOKEN = config("RAVINDEX_ACCESS_TOKEN")

API_HEADERS = {
    "authorization": f"Bearer {RAVINDEX_ACCESS_TOKEN}",
    "content-type": "application/json",
}
API_BODY = {
    "operationName": "CoverdCallStrategy",
    "variables": {
        "first": 20,
        "data_Delta_Gte": LEAST_DESIRED_DELTA,
        "endDate_Gte": datetime.today().strftime("%Y-%m-%d"),
        "endDate_Lte": (datetime.today() + timedelta(days=15)).strftime("%Y-%m-%d"),
        # todo: 15 must be configurable in above line
        "orderBy": "-coverCall,id",
        "coverCallGte": LEAST_COVERED_CALL_PROFIT,
    },
    "query": """
    query CoverdCallStrategy($after: String, $first: Int, $orderBy: String, $baseSecurity_Ticker_In: [String], $data_Delta_Gte: Float, $endDate_Gte: Date, $endDate_Lte: Date, $strickPriceDiffWithBasePriceRange: RangeInput, $coverCallGte: Int, $coverCallFinalPriceDiffPercentByBasePriceRange: RangeInput, $coverCallVolumeGte: BigInt) {
      options(
        after: $after
        first: $first
        orderBy: $orderBy
        baseSecurity_Ticker_In: $baseSecurity_Ticker_In
        data_Delta_Gte: $data_Delta_Gte
        endDate_Gte: $endDate_Gte
        endDate_Lte: $endDate_Lte
        hasCoverCall: true
        strickPriceDiffWithBasePriceRange: $strickPriceDiffWithBasePriceRange
        coverCallGte: $coverCallGte
        optionType: BUY
        coverCallFinalPriceDiffPercentByBasePriceRange: $coverCallFinalPriceDiffPercentByBasePriceRange
        coverCallVolumeGte: $coverCallVolumeGte
      ) {
        edges {
          node {
            id
            finalPriceDiffPercentByFinalPrice
            coverCallFinalPriceDiffPercentByBasePrice
            security {
              symbol
              id
              orderBook {
                highestBidPrice
                lowestAskPrice
                highestBidValue
              }
            }
            strickPrice
            coverCallFinalPrice
            coverCallVolume
            coverCall
            coverCallProfit
            coverCallInEndDate
            baseSecurity {
              symbol
              orderBook {
                lowestAskPrice
              }
            }
            endDate
            data {
              delta
            }
            guarantee
          }
        }
      }
    }
    """,
}

TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = config("TELEGRAM_CHANNEL_ID")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def fetch_and_send():
    try:
        # Send request to the API
        response = requests.post(RAVINDEX_API_URL, headers=API_HEADERS, json=API_BODY)
        response.raise_for_status()
        data = response.json()

        # Extract edges from response
        edges = data.get("data", {}).get("options", {}).get("edges", [])
        if not edges:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text="No data available.")
            return

        # Send each node as a message
        today = datetime.today()
        for edge in edges:
            node = edge.get("node", {})
            end_date = datetime.strptime(node.get("endDate"), RAVINDEX_OUTPUT_DATE_FORMAT)
            loss_in_break_even_percentages = f"{node.get('coverCallFinalPriceDiffPercentByBasePrice'):.2f}"
            symbol = node.get('security', {}).get('symbol')
            highest_bid_price = node.get('security', {}).get('orderBook', {}).get('highestBidPrice')
            lowest_ask_price = int(
                node.get('security', {}).get('orderBook', {}).get('lowestAskPrice')
            ) - 10  # 10 rials less than the lowest in the market
            strick_price = node.get('strickPrice')
            cover_call_final_price = node.get('coverCallFinalPrice')
            base_symbol = node.get('baseSecurity', {}).get('symbol')
            base_symbol_lowest_ask_price = node.get('baseSecurity', {}).get('orderBook', {}).get('lowestAskPrice')
            days_to_maturity = (end_date - today).days
            cover_call_in_end_date_profit = node.get('coverCallInEndDate')
            annual_profit_percentage = node.get('coverCall')
            monthly_profit_percentage = cover_call_in_end_date_profit / days_to_maturity * 30
            delta = node.get('data', {}).get('delta')

            message = (
                # f"ID: {node.get('id')}\n"
                f"نماد: {symbol}\n"
                f"قیمت لحظه: {highest_bid_price}\n"
                f"قیمت مناسب برای سفارش گذاری: {lowest_ask_price}\n"
                f"قیمت اعمال: {strick_price}\n"
                f"سربه‌سر: {cover_call_final_price}({loss_in_break_even_percentages})\n"
                "\n--------------------------------------------------\n\n"
                f"نماد سهام پایه: {base_symbol}\n"
                f"قیمت عرضه سهام پایه: {base_symbol_lowest_ask_price}\n"
                f"مانده تا سررسید: {days_to_maturity} روز\n"
                "\n--------------------------------------------------\n\n"
                f"درصد سود در سررسید: {cover_call_in_end_date_profit:.2f}\n"
                f"درصد سود سالانه: {annual_profit_percentage:.2f}\n"
                f"درصد سود ماهیانه: {monthly_profit_percentage:.2f}\n"
                f"احتمال تحقق: {delta}\n"
            )
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)

    except Exception as e:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=f"Error: {e}")


async def main():
    while True:
        await fetch_and_send()
        await asyncio.sleep(POLLING_INTERVAL_MINUTES * 60)  # seconds


if __name__ == "__main__":
    asyncio.run(main())
