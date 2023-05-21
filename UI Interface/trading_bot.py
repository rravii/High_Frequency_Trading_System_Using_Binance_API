import tkinter as tk
from tkinter import messagebox
from binance.client import Client
import pandas as pd
import ta
from datetime import timedelta
import time
import threading

# Binance API credentials
api_key = "binance_api_key"
api_secret = "binance_secret_key"

# Binance client initialization
client = Client(api_key, api_secret, testnet=True)

# Symbol and investment amount
symbol = 'BTCUSDT'
investment = 0
pos_dict = {'in_position': False}
df = None

# Indicator function
def indicators(df):
    df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
    df['stochrsi_k'] = ta.momentum.stochrsi_k(df['Close'], window=10)
    df.dropna(inplace=True)
    df['Buy'] = (df['Close'] > df['SMA_200']) & (df['stochrsi_k'] < 0.05)
    return df


# Get historical data
def getdata(symbol):
    frame = pd.DataFrame(client.get_historical_klines(symbol, '15m', '3000 minutes UTC'))
    frame = frame.iloc[:, 0:5]
    frame.columns = ['Time', 'Open', 'High', 'Low', 'Close']
    frame = frame.set_index('Time')
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame


# Price calculation function
def pricecalc(symbol, limit=0.97):
    raw_price = float(client.get_symbol_ticker(symbol=symbol)['price'])
    dec_len = len(str(raw_price).split('.')[1])
    price = raw_price * limit
    return round(price, dec_len)


# Quantity calculation function
def quantitycalc(symbol, investment):
    info = client.get_symbol_info(symbol=symbol)
    Lotsize = float([i for i in info['filters'] if i['filterType'] == 'LOT_SIZE'][0]['minQty'])
    price = pricecalc(symbol)
    qty = round(investment / price, right_rounding(Lotsize))
    return qty


# Decimal places calculation function
def right_rounding(Lotsize):
    decimal_places = 0
    while Lotsize < 1:
        Lotsize *= 10
        decimal_places += 1
    return decimal_places


# Buy order function
def buy(investment):
    order = client.order_limit_buy(
        symbol=symbol,
        price=pricecalc(symbol),
        quantity=quantitycalc(symbol, investment)
    )
    logs.insert(tk.END, f"Buy order executed: {order}\n")
    pos_dict['in_position'] = True


# Sell order function
def sell(qty):
    order = client.create_order(
        symbol=symbol,
        side='SELL',
        type='MARKET',
        quantity=qty
    )
    logs.insert(tk.END, f"Sell order executed: {order}\n")
    pos_dict['in_position'] = False


# Check for buy condition
def checkbuy():
    if not pos_dict['in_position']:
        if df.Buy.values:
            return True
    else:
        logs.insert(tk.END, "Already in a position\n")


# Check for sell condition
def checksell(order):
    order_status = client.get_order(symbol=symbol, orderId=order['orderId'])
    if pos_dict['in_position']:
        if order_status['status'] == 'NEW':
            logs.insert(tk.END, "Buy limit order pending\n")
        elif order_status['status'] == 'FILLED':
            cond1 = df.Close.values > float(order_status['price'])
            cond2 = pd.to_datetime('now') >= pd.to_datetime(order_status['updateTime'], unit='ms') + timedelta(minutes=150)
            if cond1 or cond2:
                sell(order_status['origQty'])
                logs.insert(tk.END, "Sell order executed\n")
    else:
        logs.insert(tk.END, "Currently not in position, no checks for selling\n")


# Main trading loop
def trading_loop():
    global df
    while True:
        df = indicators(getdata(symbol))

        if df is not None:
            if checkbuy():
                curr_order = buy(investment)
        try:
            checksell(curr_order)
        except:
            logs.insert(tk.END, "Not an order yet\n")

        time.sleep(60)


# GUI Functions
def start_trading():
    global investment
    investment = float(investment_entry.get())
    threading.Thread(target=trading_loop).start()


# Create the main window
root = tk.Tk()
root.title("Trading Bot")

# Investment amount input field
investment_label = tk.Label(root, text="Investment Amount:")
investment_label.pack()

investment_entry = tk.Entry(root)
investment_entry.pack()

# Start trading button
start_button = tk.Button(root, text="Start Trading", command=start_trading)
start_button.pack()

# Logs field
logs_label = tk.Label(root, text="Logs:")
logs_label.pack()

logs = tk.Text(root, width=50, height=10)
logs.pack()

root.mainloop()