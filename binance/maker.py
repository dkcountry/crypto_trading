from binance.client import Client
import util.time_converter as tc
import pandas as pd
import numpy as np
import time
import datetime
pd.options.display.float_format = '{%.2f}'.format


class MarketMaker(object):
    def __init__(self, api_key, api_secret, ticker, num_levels):
        self.client = Client(api_key, api_secret)
        self.ticker = ticker
        self.num_levels = num_levels

        self.position = 0.0
        self.avg_price = 0.0
        self.fees = 0.0
        self.revenue = 0.0
        self.open_orders = pd.DataFrame()

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
        if len(self.open_orders) > 0:
            ids = self.open_orders[self.open_orders.side == side.upper()].orderId.values
            for orderId in ids:
                result = self.client.cancel_order(symbol=self.ticker, orderId=orderId)
        self.fetch_all_orders()

    def place_one_side(self, side, mid):
        if side.upper() == 'BUY':
            best = mid - 0.000005
            for i in range(self.num_levels):
                o = self.client.order_limit_buy(symbol=self.ticker, quantity=0.16, price=round(best-0.000005*i, 6))

        if side.upper() == 'SELL':
            best = mid + 0.000005
            for i in range(self.num_levels):
                o = self.client.order_limit_sell(symbol=self.ticker, quantity=0.16, price=round(best+0.000005*i, 6))

    def cancel_all(self):
        self.cancel_one_side("BUY")
        self.cancel_one_side("SELL")

    def update_position(self):
        position_changed = False
        for ind, row in self.open_orders.iterrows():
            order = self.client.get_order(symbol=row['symbol'], orderId=row['orderId'])
            qty_diff = float(order['executedQty']) - float(row['executedQty'])
            if qty_diff > .00001:
                print(qty_diff)
                self.record_fill(qty_diff, float(order['price']), order['side'])
                position_changed = True

        self.fetch_all_orders()
        print("{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " " +
              "current position: " + str(self.position) + " avg fill price: " + str(self.avg_price))
        return position_changed

    def record_fill(self, qty_diff, price, side):
        if side.upper() == 'BUY' and self.position >= 0:
            self.avg_price = (self.avg_price * self.position + qty_diff * price)/(qty_diff + self.position)
            self.position += qty_diff
        if side.upper() == 'SELL' and self.position <= 0:
            self.avg_price = (self.avg_price * self.position - qty_diff * price)/(self.position - qty_diff)
            self.position -= qty_diff
        if side.upper() == 'BUY' and self.position < 0:
            self.position += qty_diff
            if self.position > 0:
                self.avg_price = price
        if side.upper() == 'SELL' and self.position > 0:
            self.position -= qty_diff
            if self.position < 0:
                self.avg_price = price

    def run(self):
        self.cancel_all()
        init_mid = self.set_mid_price()
        self.place_one_side("BUY", init_mid)
        self.place_one_side("SELL", init_mid)
        self.fetch_all_orders()

        print(self.open_orders)
        while True:
            change = self.update_position()
            time.sleep(1)




m = MarketMaker(api_key, api_secret, "NEOBTC", 2)
m.run()
