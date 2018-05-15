from binance.client import Client
import util.time_converter as tc
import pandas as pd
import numpy as np
pd.options.display.float_format = '{%.2f}'.format


class MarketMaker(object):
    def __init__(self, api_key, api_secret, ticker, num_levels):
        self.client = Client(api_key, api_secret)
        self.ticker = ticker
        self.num_levels = num_levels

        self.position = 0
        self.avg_price = np.nan
        self.fees = 0
        self.revenue = 0

        self.open_orders = pd.DataFrame()
        self.all_orders = pd.DataFrame()

    def fetch_all_orders(self):
        """Get all open orders and save to df"""

        orders = self.client.get_open_orders(symbol=self.ticker)
        columns = ['symbol', 'orderId', 'price', 'origQty', 'executedQty', 'status', 'timeInForce',
                   'type', 'side', 'isWorking']
        o = pd.DataFrame([[x[col] for col in columns] for x in orders], columns=columns)
        self.open_orders = o

    def set_mid_price(self):
        order_book = self.client.get_order_book(symbol=self.ticker)
        best_bid = float(order_book['bids'][0][0])
        best_ask = float(order_book['asks'][0][0])
        mid = round(np.average([best_bid, best_ask]), 6)
        return mid

    def cancel_one_side(self, side):
        ids = self.open_orders[self.open_orders.side == side.upper()].orderId.values
        for orderId in ids:
            result = self.client.cancel_order(symbol=self.ticker, orderId=orderId)
        self.fetch_all_orders()

    def place_one_side(self, side):
        mid = self.set_mid_price()
        if side.upper() == 'BUY':
            best = mid - 0.000005
            for i in range(self.num_levels):
                order = self.client.order_limit_buy(
                    symbol=self.ticker,
                    quantity=0.16,
                    price=round(best-0.000003*i, 6))

        if side.upper() == 'SELL':
            best = mid + 0.000005
            for i in range(self.num_levels):
                order = self.client.order_limit_sell(
                    symbol=self.ticker,
                    quantity=0.16,
                    price=round(best+0.000003*i, 6))


m = MarketMaker(api_key, api_secret, "NEOBTC", 3)

if __name__ == "__main__":


    m = MarketMaker(api_key, api_secret, "NEOBTC", 3)
    print(m.set_mid_price())
