import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from decouple import config
from telegram import Bot

from ravindex_graphql_query import query

# Configuration
LEAST_DESIRED_DELTA = config("LEAST_DESIRED_DELTA", 0.8, cast=float)
LEAST_COVERED_CALL_PROFIT = config("LEAST_COVERED_CALL_PROFIT", 60, cast=int)
POLLING_INTERVAL_MINUTES = config("POLLING_INTERVAL_MINUTES", 5, cast=int)
RAVINDEX_API_URL = "https://api.ravindex.ir/graphql"
RAVINDEX_OUTPUT_DATE_FORMAT = "%Y-%m-%d"
RAVINDEX_ACCESS_TOKEN = config("RAVINDEX_ACCESS_TOKEN")
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = config("TELEGRAM_CHANNEL_ID")


@dataclass
class RavindexOptionItem:
    id: str
    symbol: str
    highest_bid_price: float
    lowest_ask_price: float
    strick_price: float
    cover_call_final_price: float
    loss_in_break_even_percentages: float
    base_symbol: str
    base_symbol_lowest_ask_price: float
    days_to_maturity: int
    cover_call_in_end_date_profit: float
    annual_profit_percentage: float
    monthly_profit_percentage: float
    delta: float


# Ravindex Client
class RavindexClient:
    def __init__(self):
        self.headers = {
            "authorization": f"Bearer {RAVINDEX_ACCESS_TOKEN}",
            "content-type": "application/json",
        }
        self.body = {
            "operationName": "CoverdCallStrategy",
            "variables": {
                "first": 20,
                "data_Delta_Gte": LEAST_DESIRED_DELTA,
                "endDate_Gte": datetime.today().strftime("%Y-%m-%d"),
                "endDate_Lte": (datetime.today() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "orderBy": "-coverCall,id",
                "coverCallGte": LEAST_COVERED_CALL_PROFIT,
            },
            "query": query,
        }

    def fetch_options(self):
        response = requests.post(RAVINDEX_API_URL, headers=self.headers, json=self.body)
        response.raise_for_status()
        data = response.json()
        edges = data.get("data", {}).get("options", {}).get("edges", [])
        return [self._parse_option_item(edge['node']) for edge in edges]

    def _parse_option_item(self, node):
        today = datetime.today()
        end_date = datetime.strptime(node.get("endDate"), RAVINDEX_OUTPUT_DATE_FORMAT)
        return RavindexOptionItem(
            id=node.get('id'),
            symbol=node.get('security', {}).get('symbol'),
            highest_bid_price=node.get('security', {}).get('orderBook', {}).get('highestBidPrice'),
            lowest_ask_price=int(node.get('security', {}).get('orderBook', {}).get('lowestAskPrice')) - 10,
            strick_price=node.get('strickPrice'),
            cover_call_final_price=node.get('coverCallFinalPrice'),
            loss_in_break_even_percentages=float(f"{node.get('coverCallFinalPriceDiffPercentByBasePrice'):.2f}"),
            base_symbol=node.get('baseSecurity', {}).get('symbol'),
            base_symbol_lowest_ask_price=node.get('baseSecurity', {}).get('orderBook', {}).get('lowestAskPrice'),
            days_to_maturity=(end_date - today).days,
            cover_call_in_end_date_profit=node.get('coverCallInEndDate'),
            annual_profit_percentage=node.get('coverCall'),
            monthly_profit_percentage=node.get('coverCallInEndDate') / (end_date - today).days * 30,
            delta=node.get('data', {}).get('delta')
        )


# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def fetch_and_send():
    client = RavindexClient()
    try:
        options = client.fetch_options()
        if not options:
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text="No data available.")
            return

        for option in options:
            message = (
                f"نماد: {option.symbol}\n"
                f"قیمت لحظه: {option.highest_bid_price}\n"
                f"قیمت مناسب برای سفارش گذاری: {option.lowest_ask_price}\n"
                f"قیمت اعمال: {option.strick_price}\n"
                f"سربه‌سر: {option.cover_call_final_price}({option.loss_in_break_even_percentages})\n"
                "\n--------------------------------------------------\n\n"
                f"نماد سهام پایه: {option.base_symbol}\n"
                f"قیمت عرضه سهام پایه: {option.base_symbol_lowest_ask_price}\n"
                f"مانده تا سررسید: {option.days_to_maturity} روز\n"
                "\n--------------------------------------------------\n\n"
                f"درصد سود در سررسید: {option.cover_call_in_end_date_profit:.2f}\n"
                f"درصد سود سالانه: {option.annual_profit_percentage:.2f}\n"
                f"درصد سود ماهیانه: {option.monthly_profit_percentage:.2f}\n"
                f"احتمال تحقق: {option.delta}\n"
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
