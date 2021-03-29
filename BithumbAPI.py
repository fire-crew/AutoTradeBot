import os
import jwt
import uuid
import hashlib
import time
import datetime
import logging
import requests
import json
import Util

from pandas.io.json import json_normalize
from slacker import Slacker
from urllib.parse import urlencode
from pybithumb import Bithumb

with open("key.txt") as f:
    lines = f.readlines()
    key = lines[0].strip()
    secret = lines[1].strip()
    slackURL = lines[2].strip()
    #bithumb = pybithumb.Bithumb(key, secret)


INTERVAL = 1                                      
DEBUG = False                                      

COIN_NUMS = 15                                    
LARRY_K = 0.5

GAIN = 0.3                                         
DUAL_NOISE_LIMIT1 = 0.75                           

def cal_moving_average(window=5,ticker):
    try:
        df = pybithumb.get_ohlcv(ticker)
        close = df['close']
        ma = close.rolling(window=window).mean()
        return ma[-2]
    except:
        return None


def cal_target(ticker):
    try:
        df = pybithumb.get_ohlcv(ticker)
        yesterday = df.iloc[-2]

        today_open = yesterday['close']
        yesterday_high = yesterday['high']
        yesterday_low = yesterday['low']
        target = today_open + (yesterday_high - yesterday_low) * 0.5
        return target
    except:
        return None
