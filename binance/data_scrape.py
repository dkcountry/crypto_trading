from binance.client import Client
import time
import datetime
import csv
import util.time_converter as tc


client = Client(api_key, api_secret)

# get market depth
depth = client.get_order_book(symbol='LTCBTC')

klines = client.get_historical_klines("LTCBTC", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")

info = client.get_symbol_info("LTCBTC")


def collect_order_data(depth):
    order_book = client.get_order_book(symbol='LTCBTC')
    row = [round(time.time())]
    for i in range(depth):
        row.append(order_book['bids'][0][0])
        row.append(order_book['bids'][0][1])
        row.append(order_book['asks'][0][0])
        row.append(order_book['asks'][0][1])

    with open('order_book.csv', 'a') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(row)

    print("wrote row at: " + str(round(time.time())))
    time.sleep(1)