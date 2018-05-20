import numpy as np
import time
from util.binance_trader import *


class NeoBTCBot(MarketMaker):
    """NEO BTC market making bot"""

    def set_mid_price(self):
        """set mid point price """

        order_book = self.client.get_order_book(symbol=self.ticker)
        best_bid = float(order_book['bids'][0][0])
        best_ask = float(order_book['asks'][0][0])
        mid = round(np.average([best_bid, best_ask]), 6)
        return mid

    def adjust_orders(self):
        """dynamically adjust orders"""

        # if a position change results in flat position, reset markets
        if abs(self.position) < self.rounding_delta:
            self.cancel_all()
            return

        # handle buy orders
        least_agro_buy = self.open_orders[self.open_orders.side == 'BUY'].price.min()
        if least_agro_buy < (self.avg_price - 2.5*self.edge) and self.position <= self.max_position:
            order = self.open_orders[(self.open_orders.price == least_agro_buy)].iloc[0]
            cancel = self.client.cancel_order(symbol=self.ticker, orderId=order.orderId)
            self.o = self.client.order_limit_buy(symbol=self.ticker, quantity=self.qty,
                                                 price=round(self.avg_price - 2*self.edge, 6))
            self.add_single_order(self.o)

        if pd.isna(least_agro_buy) and self.position <= self.max_position:
            self.o = self.client.order_limit_buy(symbol=self.ticker, quantity=self.qty,
                                                 price=round(self.avg_price - 2 * self.edge, 6))
            self.add_single_order(self.o)

        # handle sell orders
        least_agro_sell = self.open_orders[self.open_orders.side == 'SELL'].price.max()
        if least_agro_sell > (self.avg_price + 2.5*self.edge) and -self.position <= self.max_position:
            order = self.open_orders[(self.open_orders.price == least_agro_sell)].iloc[0]
            cancel = self.client.cancel_order(symbol=self.ticker, orderId=order.orderId)
            self.o = self.client.order_limit_sell(symbol=self.ticker, quantity=self.qty,
                                                  price=round(self.avg_price + 2*self.edge, 6))
            self.add_single_order(self.o)

        if pd.isna(least_agro_sell) and -self.position <= self.max_position:
            self.o = self.client.order_limit_sell(symbol=self.ticker, quantity=self.qty,
                                                  price=round(self.avg_price + 2 * self.edge, 6))
            self.add_single_order(self.o)

    def run(self):
        """run algo """

        self.set_init_market()
        while True:
            change = self.update_position()
            if change:
                self.adjust_orders()

            # if no open orders, reset markets
            if len(self.open_orders) == 0:
                self.set_init_market()

            time.sleep(1)


if __name__ == "__main__":
    m = NeoBTCBot(api_key, api_secret, "NEOBTC", 2, .16, 0.000005)
    m.run()
