from binance.client import Client
import pandas as pd
import datetime


class TradingBot(object):
    """Single security trading bot class"""

    def __init__(self, api_key, api_secret, ticker):
        self.client = Client(api_key, api_secret)
        self.ticker = ticker

        self.rounding_delta = 0.00001
        self.round = 6
        self.position = 0.0
        self.avg_price = 0.0
        self.fees = 0.0
        self.revenue = 0.0
        self.open_orders = pd.DataFrame()

    def fetch_all_orders(self):
        """Get all open orders and save to object df"""

        orders = self.client.get_open_orders(symbol=self.ticker)
        columns = ['symbol', 'orderId', 'price', 'origQty', 'executedQty', 'status', 'timeInForce',
                   'type', 'side']
        o = pd.DataFrame([[x[col] for col in columns] for x in orders], columns=columns)
        self.open_orders = o
        self.format_open_orders()

    def format_open_orders(self):
        """convert price and quantity columns in open orders to float"""

        self.open_orders.price = pd.to_numeric(self.open_orders.price)
        self.open_orders.origQty = pd.to_numeric(self.open_orders.origQty)
        self.open_orders.executedQty = pd.to_numeric(self.open_orders.executedQty)

    def cancel_one_side(self, side):
        """Cancel all orders for one side"""

        if len(self.open_orders) > 0:
            ids = self.open_orders[self.open_orders.side == side.upper()].orderId.values
            for orderId in ids:
                result = self.client.cancel_order(symbol=self.ticker, orderId=orderId)
        self.fetch_all_orders()

    def cancel_all(self):
        """cancel all orders"""

        self.cancel_one_side("BUY")
        self.cancel_one_side("SELL")

    def update_position(self):
        """Iterate through open orders; if executed quantity has changed, updated self.position and self.avg_price
            then update open orders
        """
        position_changed = False
        old_orders = self.open_orders.copy(deep=True)

        for ind, row in old_orders.iterrows():
            order = self.client.get_order(symbol=row['symbol'], orderId=row['orderId'])
            qty_diff = float(order['executedQty']) - float(row['executedQty'])

            if qty_diff > self.rounding_delta:
                print(qty_diff)
                self.record_fill(qty_diff, float(order['price']), order['side'])
                position_changed = True
                self.open_orders = self.open_orders[self.open_orders.orderId != order['orderId']]

                if order['status'] not in ['FILLED', 'CANCELED']:
                    self.add_single_order(order)

            if order['status'] in ['CANCELED']:
                self.open_orders = self.open_orders[self.open_orders.orderId != order['orderId']]

        print("{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " " +
              "current position: " + str(self.position) + " avg fill price: " + str(self.avg_price))
        return position_changed

    def add_single_order(self, order):
        """append single order to open orders"""

        columns = ['symbol', 'orderId', 'price', 'origQty', 'executedQty', 'status', 'timeInForce',
                   'type', 'side']
        new_order = [order[col] for col in columns]
        new_order = pd.Series(new_order, index=columns)
        self.new_order = new_order
        self.open_orders = self.open_orders.append(new_order, ignore_index=True)
        self.format_open_orders()
        print(new_order)

    def record_fill(self, qty_diff, price, side):
        """handles updating self.position and self.avg_price"""

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


class MarketMaker(TradingBot):
    """Abstract Market Maker Class; inherits from Trading Bot"""

    def __init__(self, api_key, api_secret, ticker, num_levels, qty, edge):
        super(MarketMaker, self).__init__(api_key, api_secret, ticker)

        self.num_levels = num_levels
        self.qty = qty
        self.edge = edge
        self.max_position = self.qty * 2

    def set_init_market(self):
        """initialize orders"""

        self.cancel_all()
        init_mid = self.set_mid_price()
        self.place_one_side("BUY", init_mid)
        self.place_one_side("SELL", init_mid)
        self.fetch_all_orders()

    def place_one_side(self, side, mid):
        if side.upper() == 'BUY':
            best = mid - self.edge
            for i in range(self.num_levels):
                o = self.client.order_limit_buy(symbol=self.ticker, quantity=self.qty,
                                                price=round(best-self.edge*i, self.round))
        if side.upper() == 'SELL':
            best = mid + self.edge
            for i in range(self.num_levels):
                o = self.client.order_limit_sell(symbol=self.ticker, quantity=self.qty,
                                                 price=round(best+self.edge*i, self.round))

    # USER Implemented Functions #
    def set_mid_price(self):
        """set mid point price """

        return None

    def adjust_orders(self):
        """dynamically adjust orders"""

        return None

    def run(self):
        """run algo """

        pass

