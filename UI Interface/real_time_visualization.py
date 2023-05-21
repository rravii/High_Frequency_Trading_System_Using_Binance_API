import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from binance.client import Client
import pandas as pd

# Binance API credentials
api_key = "binance_api_key"
api_secret = "binance_secret_key"

# Create a Binance API client
client = Client(api_key, api_secret, testnet=True)

# Get a list of available trading pairs
symbols = [symbol['symbol'] for symbol in client.get_exchange_info()['symbols']]

class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("High-Frequency Trading System")
        self.geometry("800x1000")  # Set the window size to 800x600

        # Create a label and dropdown menu for selecting the trading pair
        self.pair_label = tk.Label(self, text="Select a trading pair:")
        self.pair_label.pack()
        self.pair_var = tk.StringVar(self)
        self.pair_var.set(symbols[0])
        self.pair_dropdown = tk.OptionMenu(self, self.pair_var, *symbols, command=self.update_pair)
        self.pair_dropdown.pack()

        # Create a figure and canvas for the graph
        self.figure = plt.Figure(figsize=(8, 6), dpi=100)  # Increase the figure size
        self.graph = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack()

        # Create labels for displaying table data and liquidity information
        self.table_label = tk.Label(self, text="Table Data")
        self.table_label.pack()
        self.table_data = tk.Text(self, height=10, width=70)  # Increase the height of the table
        self.table_data.pack()

        self.liquidity_label = tk.Label(self, text="Liquidity")
        self.liquidity_label.pack()
        self.liquidity_data = tk.StringVar(self)
        self.liquidity_data.set("No liquidity information")
        self.liquidity_display = tk.Label(self, textvariable=self.liquidity_data)
        self.liquidity_display.pack()

        # Initialize the graph and data
        self.selected_pair = self.pair_var.get()
        self.data = pd.DataFrame()
        self.plot_graph()

        # Start fetching real-time data
        self.fetch_realtime_data()

    def fetch_realtime_data(self):
        # Fetch real-time data at regular intervals
        self.update_data()
        self.plot_graph()
        self.update_table_data()
        self.update_liquidity()

        # Schedule the next fetch after 5 seconds
        self.after(5000, self.fetch_realtime_data)

    def update_data(self):
        # Fetch the latest minute data for the selected pair
        self.data = self.get_minute_data(self.selected_pair, '1m', '120m')

    def get_minute_data(self, symbol, interval, lookback):
        frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback))
        frame = frame.iloc[:, :6]
        frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        frame = frame.set_index('Time')
        frame.index = pd.to_datetime(frame.index, unit='ms')
        frame = frame.astype(float)
        return frame

    def plot_graph(self):
        self.graph.clear()
        if not self.data.empty:
            self.graph.set_title(self.selected_pair)
            self.graph.set_xlabel('Time')
            self.graph.set_ylabel('Price')

            # Convert dataframe to OHLC format
            ohlc = self.data[['Open', 'High', 'Low', 'Close']]
            ohlc.reset_index(inplace=True)
            ohlc['Time'] = ohlc['Time'].apply(lambda x: x.timestamp())
            ohlc = ohlc.values

            # Plot chart
            self.graph.plot(self.data.index, self.data['Close'], label='Price')
            self.graph.legend()

        plt.xticks(rotation=45)
        self.canvas.draw()

    def update_table_data(self):
        if not self.data.empty:
            self.table_data.delete(1.0, tk.END)
            self.table_data.insert(tk.END, str(self.data))
        else:
            self.table_data.delete(1.0, tk.END)
            self.table_data.insert(tk.END, "No data available")

    def update_liquidity(self):
        buy_liquidity, sell_liquidity = self.get_liquidity(self.selected_pair)
        self.liquidity_data.set(f"Buy Liquidity: {buy_liquidity}\nSell Liquidity: {sell_liquidity}")

    def get_liquidity(self, symbol, limit=100):
        depth = client.get_order_book(symbol=symbol, limit=limit)
        bids = depth['bids']
        asks = depth['asks']
        buy_liquidity = sum(float(bid[1]) for bid in bids)
        sell_liquidity = sum(float(ask[1]) for ask in asks)
        return buy_liquidity, sell_liquidity

    def update_pair(self, *args):
        new_pair = self.pair_var.get()
        if new_pair != self.selected_pair:
            self.selected_pair = new_pair
            self.update_data()
            self.plot_graph()
            self.update_table_data()
            self.update_liquidity()


if __name__ == '__main__':
    app = App()
    app.mainloop()