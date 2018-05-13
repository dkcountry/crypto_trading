import time
import datetime


def ms_to_datetime(ms):
    return datetime.datetime.fromtimestamp(ms/1000.0)


def epoch_to_iso(seconds_since_epoch):
    dt = datetime.datetime.utcfromtimestamp(seconds_since_epoch)
    iso_format = dt.isoformat() + 'Z'
    return iso_format


def iso_to_datetime(iso):
    return datetime.datetime(*time.strptime(iso[:-1], "%Y-%m-%dT%H:%M:%S")[:6])
