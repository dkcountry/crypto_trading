import json, hmac, hashlib, time, requests, base64, datetime
from requests.auth import AuthBase


class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = signature.digest().encode('base64').rstrip('\n')

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request


def order_pressure(ratio, depth):
    r = requests.get(api_url + 'products/' + "LTC-USD" + "/book?level=2").json()
    bid_press = lin_weight(r['bids'][0:depth])
    ask_press = lin_weight(r['asks'][0:depth])

    if bid_press/ask_press > ratio:
        return bid_press/ask_press
    elif ask_press/bid_press > ratio:
        return (ask_press/bid_press) * (-1)
    else:
        return 0


def tightness():
    r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()
    return float(r['asks'][0][0]) - float(r['bids'][0][0])


def lin_weight(book):
    w = range(len(book))
    return sum([(x+1)**2*float(y[1]) for x, y in zip(w, book[::-1])])


def continued_signal(sig, new_sig, ratio):
    if sig > 0:
        return new_sig > ratio
    if sig < 0:
        return new_sig < ((-1) * ratio)


def get_nbbo_size(sig):
    r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()
    if sig > 0:
        return float(r['asks'][0][1])
    if sig < 0:
        return float(r['bids'][0][1])
    return None


def execute_trade(sig, size, product):
    r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()

    if sig > 0:
        side = 'buy'
        price = float(r['asks'][0][0])
    if sig < 0:
        side = 'sell'
        price = float(r['bids'][0][0])

    order = {
        'size': size,
        'price': price,
        'side': side,
        'product_id': product,
        'time_in_force': 'IOC'
    }
    trade = requests.post(api_url + 'orders', json=order, auth=auth).json()
    print("      " + side + " " + str(price) + " " + order['product_id'] + " at " + str(order['price']))
    print("====================")
    print(trade)
    print("====================")
    try:
        return trade
    except:
        return None


def exit_signal(sig, entry, profit, loss):
    r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()
    if sig > 0:
        exit_gain = entry + profit
        exit_loss = entry - loss
        price = float(r['asks'][0][0])
    if sig < 0:
        exit_gain = entry - profit
        exit_loss = entry + loss
        price = float(r['bids'][0][0])

    if price <= min(exit_gain, exit_loss) or price >= max(exit_gain, exit_loss):
        return True

    return False


def order_depth_bot():
    while True:
        traded = False
        filled_quantity = 0.0
        price = None

        r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()
        signal = order_pressure(ratio, depth)
        print("{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " signal: " + str(signal) + " bid: " +
              r['bids'][0][0] + " ask: " + r['asks'][0][0])

        if abs(signal) > ratio and tightness() <= .011:
            print("Signal Activated.... " + "tightness: " + str(tightness()))
            nbbo_size = get_nbbo_size(signal)
            new_signal = order_pressure(ratio, depth)

            while continued_signal(signal, new_signal, ratio) and not traded:
                new_nbbo_size = get_nbbo_size(new_signal)
                if (new_nbbo_size < (nbbo_size/3) and new_nbbo_size < max_size) or (new_nbbo_size < small_size):
                    trade = execute_trade(new_signal, trade_size, product_id)
                    if trade is not None:
                        traded = True
                        time.sleep(1)
                        order = requests.get(api_url + 'orders/' + trade['id'], auth=auth).json()
                        filled_quantity = float(order['filled_size'])
                        print("            position size: " + str(filled_quantity))
                        price = float(order['price'])
                        cancel = requests.delete(api_url + 'orders/', auth=auth).json()
                        print("      canceled: ")
                        print(cancel)
                    time.sleep(1)

                r = requests.get(api_url + 'products/' + "LTC-USD" + "/book").json()
                new_signal = order_pressure(ratio, depth)
                print("{:%Y-%m-%d %H:%M:%S}".format(datetime.datetime.now()) + " signal: " + str(new_signal) + " bid: "
                      + r['bids'][0][0] + " ask: " + r['asks'][0][0])

                time.sleep(1)

            while filled_quantity > 0.01:
                print("           Exiting Position....")
                if exit_signal(signal, price, profit, loss):
                    trade = execute_trade(-signal, filled_quantity, product_id)
                    if trade is not None:
                        time.sleep(1)
                        order = requests.get(api_url + 'orders/' + trade['id'], auth=auth).json()
                        filled_quantity = filled_quantity - float(order['filled_size'])
                        print("            position size: " + str(filled_quantity))
                        price = float(order['price'])
                        cancel = requests.delete(api_url + 'orders/', auth=auth).json()
                        print("      canceled: ")
                        print(cancel)
                time.sleep(1)

        time.sleep(1)


if __name__ == "__main__":
    ratio = 4
    depth = 5
    max_size = 5
    small_size = 1
    trade_size = .1
    product_id = 'LTC-USD'
    profit = .06
    loss = .03
    api_url = 'https://api.gdax.com/'
    auth = CoinbaseExchangeAuth()

    order_depth_bot()
