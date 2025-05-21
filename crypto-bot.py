import requests
import ccxt
import pandas as pd
import time
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime, timezone
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")

# Set up log directory
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "trading_bot.log")

# Configure rotating file handler
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize Binance client
binance = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'},
})

symbol = 'BTC/USDT'
timeframe = '15m'
limit = 100
amount = 0.001  # Placeholder amount

def fetch_ohlcv():
    """
    Fetch historical OHLCV data from Binance.
    """
    data = binance.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def add_indicators(df):
    """
    Calculate EMA and RSI indicators and add them to the DataFrame.
    """
    df['ema9'] = EMAIndicator(df['close'], window=9).ema_indicator()
    df['ema21'] = EMAIndicator(df['close'], window=21).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    return df

def check_signals(df):
    """
    Generate trading signal based on EMA crossover and RSI conditions.
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]

    bullish_cross = prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21']
    bearish_cross = prev['ema9'] > prev['ema21'] and last['ema9'] < last['ema21']

    rsi_ok_buy = last['rsi'] < 70
    rsi_ok_sell = last['rsi'] > 30

    if bullish_cross and rsi_ok_buy:
        return 'BUY'
    elif bearish_cross and rsi_ok_sell:
        return 'SELL'
    else:
        return 'HOLD'

def execute_trade(signal, price, rsi_value):
    message = f"SIGNAL: {signal} | Price: ${price:.2f} | RSI: {rsi_value:.2f}"
    if signal in ['BUY', 'SELL']:
        logging.info(message)
        send_telegram_message(message)
        # Uncomment to place real orders:
        # if signal == 'BUY':
        #     binance.create_market_buy_order(symbol, amount)
        # elif signal == 'SELL':
        #     binance.create_market_sell_order(symbol, amount)
    else:
        logging.info(message)


def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.warning(f"Telegram error: {response.text}")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

# Main loop
while True:
    try:
        df = fetch_ohlcv()
        df = add_indicators(df)
        signal = check_signals(df)

        close_price = df['close'].iloc[-1]
        rsi_value = df['rsi'].iloc[-1]

        execute_trade(signal, close_price, rsi_value)

    except Exception as e:
        logging.error(f"[{datetime.now(timezone.utc)}] ERROR: {e}")

    time.sleep(60 * 15)
