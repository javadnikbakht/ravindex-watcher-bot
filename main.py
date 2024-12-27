import asyncio
from datetime import datetime

import requests
from telegram import Bot
from decouple import config

LEAST_DESIRED_DELTA = config("LEAST_DESIRED_DELTA", 0.9, cast=float)
LEAST_COVERED_CALL_PROFIT = config("LEAST_COVERED_CALL_PROFIT", 80, cast=int)

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
            message = (
                # f"ID: {node.get('id')}\n"
                f"نماد: {node.get('security', {}).get('symbol')}\n"
                f"قیمت تقاضا: {node.get('security', {}).get('orderBook', {}).get('highestBidPrice')}\n"
                f"قیمت عرضه: {node.get('security', {}).get('orderBook', {}).get('lowestAskPrice')}\n"
                f"قیمت اعمال: {node.get('strickPrice')}\n"
                f"سربه‌سر: {node.get('coverCallFinalPrice')}({loss_in_break_even_percentages})\n"
                "\n--------------------------------------------------\n\n"
                f"نماد سهام پایه: {node.get('baseSecurity', {}).get('symbol')}\n"
                f"قیمت عرضه سهام پایه: {node.get('baseSecurity', {}).get('orderBook', {}).get('lowestAskPrice')}\n"
                f"مانده تا سررسید: {(end_date - today).days} روز\n"
                "\n--------------------------------------------------\n\n"
                f"سود در صورت اعمال: {node.get('coverCallProfit')}\n"
                f"درصد سود در سررسید: {node.get('coverCallInEndDate'):.2f}\n"
                f"درصد سود سالانه: {node.get('coverCall'):.2f}\n"
                f"مبلغ قابل‌ خرید: {node.get('coverCallVolume')}\n"
                f"دلتا: {node.get('data', {}).get('delta')}\n"
                # f"Guarantee: {node.get('guarantee')}\n"
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
