# trade_logger.py

import os
import csv
from datetime import datetime

CSV_FILE = "trades.csv"

# Ensure the CSV file exists with a header
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "action", "price", "rsi", "amount", "notes"])

# Record a new trade
def record_trade(action, price, rsi_value, amount, notes="Signal match"):
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            action,
            round(price, 2),
            round(rsi_value, 2),
            amount,
            notes
        ])

# Analyze trade history and print profit/loss
def analyze_trades():
    trades = []

    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append({
                "timestamp": row["timestamp"],
                "action": row["action"],
                "price": float(row["price"]),
                "amount": float(row["amount"]),
            })

    profits = []
    holding = None

    for trade in trades:
        if trade["action"] == "BUY":
            holding = trade
        elif trade["action"] == "SELL" and holding:
            profit = (trade["price"] - holding["price"]) * trade["amount"]
            profits.append({
                "buy_time": holding["timestamp"],
                "sell_time": trade["timestamp"],
                "buy_price": holding["price"],
                "sell_price": trade["price"],
                "amount": trade["amount"],
                "profit": profit
            })
            holding = None  # Reset

    total_profit = sum(p["profit"] for p in profits)

    for p in profits:
        print(f"Bought at {p['buy_price']} → Sold at {p['sell_price']} | Profit: ${p['profit']:.2f}")

    print(f"\nTOTAL PROFIT: ${total_profit:.2f}")
