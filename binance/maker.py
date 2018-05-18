from binance.client import Client
import pandas as pd
import numpy as np
import time
import datetime


class MarketMaker(object):
    def __init__(self, api_key, api_secret, ticker, num_levels, qty, edge):
        self.client = Client(api_key, api_secret)
        self.ticker = ticker
        self.num_levels = num_levels
        self.qty = qty
        self.edge = edge
        self.max_position = self.qty * 2

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
            best = mid - self.edge
            for i in range(self.num_levels):
                o = self.client.order_limit_buy(symbol=self.ticker, quantity=self.qty,
                                                price=round(best-self.edge*i, 6))

        if side.upper() == 'SELL':
            best = mid + self.edge
            for i in range(self.num_levels):
                o = self.client.order_limit_sell(symbol=self.ticker, quantity=self.qty,
                                                 price=round(best+self.edge*i, 6))

    def cancel_all(self):
        self.cancel_one_side("BUY")
        self.cancel_one_side("SELL")

    def update_position(self):
        position_changed = False
        old_orders = self.open_orders.copy(deep=True)
        for ind, row in old_orders.iterrows():
            order = self.client.get_order(symbol=row['symbol'], orderId=row['orderId'])
            qty_diff = float(order['executedQty']) - float(row['executedQty'])
            if qty_diff > .00001:
                print(qty_diff)
                self.record_fill(qty_diff, float(order['price']), order['side'])
                position_changed = True
                self.open_orders = self.open_orders[self.open_orders.orderId != order['orderId']]
                columns = ['symbol', 'orderId', 'price', 'origQty', 'executedQty', 'status', 'timeInForce',
                           'type', 'side', 'isWorking']
                if order['status'] not in ['FILLED', 'CANCELED']:
                    mod_o = [order[col] for col in columns]
                    mod_o = pd.Series(mod_o, index=columns)
                    self.open_orders = self.open_orders.append(mod_o)
                    print(self.open_orders)


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

    def adjust_orders(self):
        if pd.to_numeric(self.open_orders[self.open_orders.side == 'BUY'].price).max() < (self.avg_price - 2.5*self.edge) \
                and self.position <= self.max_position:
            sm_prc = self.open_orders[self.open_orders.side == 'BUY'].price.min()
            order = self.open_orders[(self.open_orders.side == 'BUY') & (self.open_orders.price == sm_prc)].iloc[0]
            cancel = self.client.cancel_order(symbol=self.ticker, orderId=order.orderId)
            o = self.client.order_limit_buy(symbol=self.ticker, quantity=self.qty,
                                            price=round(self.avg_price - 2*self.edge, 6))
            print(o)

        if pd.to_numeric(self.open_orders[self.open_orders.side == 'SELL'].price).min() > (self.avg_price + 2.5*self.edge) \
                and -self.position <= self.max_position:
            lg_prc = self.open_orders[self.open_orders.side == 'SELL'].price.max()
            order = self.open_orders[(self.open_orders.side == 'SELL') & (self.open_orders.price == lg_prc)].iloc[0]
            cancel = self.client.cancel_order(symbol=self.ticker, orderId=order.orderId)
            o = self.client.order_limit_sell(symbol=self.ticker, quantity=self.qty,
                                             price=round(self.avg_price + 2*self.edge, 6))
            print(o)

    def set_init_market(self):
        self.cancel_all()
        init_mid = self.set_mid_price()
        self.place_one_side("BUY", init_mid)
        self.place_one_side("SELL", init_mid)
        self.fetch_all_orders()

    def run(self):
        self.set_init_market()

        while True:
            change = self.update_position()
            if change:
                self.adjust_orders()

            # if no open orders, restart script
            if len(self.open_orders) == 0:
                self.set_init_market()

            time.sleep(1)


if __name__ == "__main__":


    m = MarketMaker(api_key, api_secret, "NEOBTC", 2, .16, 0.000005)
    m.run()
