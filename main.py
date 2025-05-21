from datetime import timezone
import logging
from logging.handlers import TimedRotatingFileHandler
import time
from trade_logger import init_csv, record_trade
import os
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import *
import telegram


load_dotenv()

# Setup logging
logger = logging.getLogger("crypto_bot")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler("logs/trade.log", when="midnight", interval=1)
handler.suffix = "%Y-%m-%d"
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Setup Telegram bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Setup Binance client
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_SECRET_KEY")
client = Client(API_KEY, API_SECRET)

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_15MINUTE
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
SMA_SHORT = 5
SMA_LONG = 15
TRADE_AMOUNT = 100  # In BTC for example

def get_klines():
    klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=100)
    closes = [float(k[4]) for k in klines]
    return closes

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i - 1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logger.warning(f"Failed to send Telegram message: {e}")

def main():
    init_csv()
    holding = False
    logger.info("Bot started...")

    while True:
        try:
            prices = get_klines()
            rsi = calculate_rsi(prices, RSI_PERIOD)
            sma_short = calculate_sma(prices, SMA_SHORT)
            sma_long = calculate_sma(prices, SMA_LONG)

            if not rsi or not sma_short or not sma_long:
                logger.info("Not enough data to compute indicators.")
                time.sleep(60)
                continue

            price = prices[-1]
            logger.info(f"Price: {price:.2f}, RSI: {rsi:.2f}, SMA Short: {sma_short:.2f}, SMA Long: {sma_long:.2f}")

            if rsi < RSI_OVERSOLD and sma_short > sma_long and not holding:
                logger.info(f"BUY signal! Price: {price}, RSI: {rsi:.2f}")
                send_telegram_message(f"BUY signal! Price: {price}, RSI: {rsi:.2f}")
                record_trade("BUY", price, rsi, TRADE_AMOUNT)
                # Uncomment to execute:
                # order = client.order_market_buy(symbol=SYMBOL, quantity=TRADE_AMOUNT)
                holding = True

            elif rsi > RSI_OVERBOUGHT and sma_short < sma_long and holding:
                logger.info(f"SELL signal! Price: {price}, RSI: {rsi:.2f}")
                send_telegram_message(f"SELL signal! Price: {price}, RSI: {rsi:.2f}")
                record_trade("SELL", price, rsi, TRADE_AMOUNT)
                # Uncomment to execute:
                # order = client.order_market_sell(symbol=SYMBOL, quantity=TRADE_AMOUNT)
                holding = False

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        time.sleep(905)

if __name__ == "__main__":
    main()
