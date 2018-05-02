import datetime
import pandas as pd
from auth import *
from sklearn import linear_model
import matplotlib.pyplot as plt

def date_to_iso(date):
    return '{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}'.format(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=date.hour,
        minute=date.minute,
        second=date.second)


def epoch_to_iso(seconds_since_epoch):
    dt = datetime.datetime.utcfromtimestamp(seconds_since_epoch)
    iso_format = dt.isoformat() + 'Z'
    return iso_format


def iso_to_datetime(iso):
    return datetime.datetime(*time.strptime(iso[:-1], "%Y-%m-%dT%H:%M:%S")[:6])


def get_ohlc(pair, start, end):
    """Minute bars only"""
    if (end-start).seconds/60 <= 300:
        order = {
            'start': date_to_iso(start),
            'end': date_to_iso(end),
            'granularity': 60
        }
        r = requests.get(api_url + 'products/' + pair + '/candles', order)
        return pd.DataFrame(r.json())


api_url = 'https://api.gdax.com/'
start = datetime.datetime(2018,4,30,19)
end = datetime.datetime(2018,5,1)

order = {
    'start': date_to_iso(start),
    'end': date_to_iso(end),
    'granularity': 60
}

ltc = requests.get(api_url + 'products/LTC-USD/candles', order)
btc = requests.get(api_url + 'products/BTC-USD/candles', order)


col = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
ltc = pd.DataFrame(ltc.json(), columns=col)
btc = pd.DataFrame(btc.json(), columns=col)

ltc['chg'] = ltc.close/ltc.close.shift(1) - 1
btc['chg'] = btc.close/btc.close.shift(1) - 1

ltc_close = ltc[['timestamp', 'chg']]
btc_l1 = btc[['chg', 'volume']].shift(1)
btc_l2 = btc[['chg', 'volume']].shift(2)
btc_l1.columns = ['btc_chg_l1', 'btc_vol_l1']
btc_l2.columns = ['btc_chg_l2', 'btc_vol_l2']


df = pd.concat([ltc_close, btc_l1, btc_l2], axis=1)
df = df[3:]
train = df[:200]
test = df[200:]

x_train = df[['btc_chg_l1', 'btc_vol_l1', 'btc_chg_l2', 'btc_vol_l2']]
y_train = df['chg']

ols = linear_model.LinearRegression()
model = ols.fit(x_train, y_train)

print(ols.score(x_train, y_train))
