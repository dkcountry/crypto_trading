import datetime
import pandas as pd
import numpy as np
from auth import *
from sklearn import linear_model
import matplotlib.pyplot as plt
import csv
import time


def collect_order_data(depth):
    """scrape order book data from GDAX
    param: depth - depth of book
    """

    api_url = 'https://api.gdax.com/'
    while True:
        r = requests.get(api_url + 'products/' + "LTC-USD" + "/book?level=2").json()
        row = [round(time.time())]
        for i in range(depth):
            row.append(r['bids'][0][0])
            row.append(r['bids'][0][1])
            row.append(r['asks'][0][0])
            row.append(r['asks'][0][1])

        with open('order_book.csv', 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(row)

        print("wrote row at: " + str(round(time.time())))
        time.sleep(1)


def read_data():
    """read from csv"""

    with open('order_book.csv', 'r') as f:
        reader = csv.reader(f, delimiter=',')
        data = [x for x in reader]
    df = pd.DataFrame(data[1:], columns=data[0])
    return df.apply(pd.to_numeric)


def extract_signal(data, max_quantity, ratio):
    """
    Given order book data, find instances of significant order book pressure and measure forward price impact
    :param data: order book data
    :param max_quantity: max ctx size to qualify for signal
    :param ratio: ask_size/bid_size or vice versa
    """

    data = data.values
    signal_data = []

    for i in range(len(data)):
        bid_pressure = data[i][2]/data[i][4]
        ask_pressure = data[i][4]/data[i][2]
        market_width = data[i][3] - data[i][1]

        if market_width < 0.011:
            if data[i][2] < max_quantity and ask_pressure > ratio:
                fut_price = np.average([x[1] for x in data[i+5:i+20]])
                signal_data.append([-ask_pressure, data[i][1], fut_price])

            elif data[i][4] < max_quantity and bid_pressure > ratio:
                fut_price = np.average([x[3] for x in data[i+5:i+20]])
                signal_data.append([bid_pressure, data[i][3], fut_price])

    df = pd.DataFrame(signal_data, columns=['signal', 'start_price', 'end_price'])
    return df.drop_duplicates(subset=['signal', 'start_price'], keep='last')


if __name__ == "__main__":
    data = read_data()
    signal = extract_signal(data, 10, 5)

    "Get price difference"
    signal['chg'] = signal.end_price - signal.start_price
    x_train = signal.signal.reshape(-1,1)
    y_train = signal.chg

    "Train on linear model"
    ols = linear_model.LinearRegression()
    model = ols.fit(x_train, y_train)

    "Plot data to realize that signal outliers are significant"
    plt.scatter(x_train, y_train)

    "Filter out signal noise"
    transform = signal[(abs(signal.signal) < 500) & (abs(signal.chg) > .01)]
    x_train = transform.signal.reshape(-1,1)
    y_train = transform.chg

    "Refit ols"
    ols = linear_model.LinearRegression()
    model = ols.fit(x_train, y_train)
    score = ols.score(x_train, y_train)

    plt.scatter(x_train, y_train)
