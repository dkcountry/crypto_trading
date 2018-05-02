import datetime
import pandas as pd
from auth import *


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


api_url = 'https://api.gdax.com/'
start = datetime.datetime(2018,4,1)
end = datetime.datetime(2018,4,2)

order = {
    'start': date_to_iso(start),
    'end': date_to_iso(end),
    'granularity': 3600
}

r = requests.get(api_url + 'products/LTC-USD/candles', order)
print(r.json())
