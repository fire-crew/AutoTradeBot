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
import pybithumb 

from pandas.io.json import json_normalize
from urllib.parse import urlencode


with open("key.txt") as f:
    lines = f.readlines()
    key = lines[0].strip()
    secret = lines[1].strip()
    slackURL = lines[2].strip()
    bithumb = pybithumb.Bithumb(key, secret)

############# 필드변수  #####################################################################################
INTERVAL = 1                                        # 매수 시도 interval (1초 기본)
DEBUG = False                                       # True: 매매 API 호출 안됨, False: 실제로 매매 API 호출

COIN_NUMS = 15                                      # 분산 투자 코인 개수 (자산/COIN_NUMS를 각 코인에 투자)
LARRY_K = 0.5
BALANCE = 0.5                                       # 자산의 50%만 투자 50%는 현금 보유

GAIN = 0.3                                          # 30% 이상 이익시 50% 물량 익절
DUAL_NOISE_LIMIT1 = 0.75                            # 듀얼 노이즈가 0.75 이하인 종목만 투자                        
#############################################################################################################

def make_sell_times(now):
    '''
    당일 23:50:00 시각과 23:50:10초를 만드는 함수
    :param now: DateTime
    :return:
    '''
    sell_time = datetime.datetime(year=now.year,
                                  month=now.month,
                                  day=now.day,
                                  hour=23,
                                  minute=50,
                                  second=0)
    sell_time_after_10secs = sell_time + datetime.timedelta(seconds=10)
    return sell_time, sell_time_after_10secs


def make_setup_times(now):
    '''
    익일 00:00:00 시각과 00:00:10초를 만드는 함수
    :param now:
    :return:
    '''
    tomorrow = now + datetime.timedelta(1)
    midnight = datetime.datetime(year=tomorrow.year,
                                 month=tomorrow.month,
                                 day=tomorrow.day,
                                 hour=0,
                                 minute=0,
                                 second=0)
    midnight_after_10secs = midnight + datetime.timedelta(seconds=10)
    return midnight, midnight_after_10secs


def inquiry_cur_prices(tickers):
    '''
    모든 가상화폐에 대한 현재가 조회
    :param tickers: 티커 목록, ['BTC', 'XRP', ... ]
    :return: 현재가, {'BTC': 7200000, 'XRP': 500, ...}
    '''
    try:
        all = pybithumb.get_current_price("ALL")
        cur_prices= {}
        for ticker in tickers:
            #key가 있는경우
            if ticker in all.keys():
                cur_prices[ticker] = float(all[ticker]['closing_price'])
            #key가 없는경우
            else:
                continue

        return cur_prices
    except:
        return None


def select_portfolio(tickers, window=5):
    '''
    최근 5일의 noise 평균이 낮은 순으로 포트폴리오를 기본으로 구성하는데 이때 절대 노이즈보다 작을때만 편입
    :param tickers: 티커 리스트
    :param window: 평균을 위한 윈도우 길이
    :return:
    '''
    try:
        portfolio = []

        noise_list = []
        for ticker in tickers:
            df = pybithumb.get_ohlcv(ticker)
            noise = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'])
            average_noise = noise.rolling(window=window).mean()
            noise_list.append((ticker, average_noise[-2]))

        # noise가 낮은 순으로 정렬
        sorted_noise_list = sorted(noise_list, key=lambda x:x[1])

        # 절대 노이즈 전략 기반으로 포트폴리오 구성
        for x in sorted_noise_list[:COIN_NUMS]:
            if x[1] < DUAL_NOISE_LIMIT:
                portfolio.append(x[0])

        return portfolio
    except:
        return None


def cal_target(ticker):
    '''
    각 코인에 대한 목표가 저장
    :param ticker: 티커, 'BTC'
    :return: 목표가
    '''
    try:
        df = pybithumb.get_ohlcv(ticker)
        yesterday = df.iloc[-2]
        today_open = yesterday['close']
        yesterday_high = yesterday['high']
        yesterday_low = yesterday['low']
        target = today_open + (yesterday_high - yesterday_low) * LARRY_K
        return target
    except:
        return None


def inquiry_high_prices(tickers):
    try:
        high_prices = {}
        for ticker in tickers:
            df = pybithumb.get_ohlcv(ticker)
            today = df.iloc[-1]
            today_high = today['high']
            high_prices[ticker] = today_high

        return high_prices
    except:
        return  {ticker:0 for ticker in tickers}


def inquiry_targets(tickers):
    '''
    모든 코인에 대한 목표가 계산
    :param tickers: 코인에 대한 티커 리스트
    :return:
    '''
    targets = {}
    for ticker in tickers:
        targets[ticker] = cal_target(ticker)
    return targets


def cal_moving_average(ticker="BTC", window=5):
    '''
    5일 이동평균을 계산
    :param ticker:
    :param window:
    :return:
    '''
    try:
        df = pybithumb.get_ohlcv(ticker)
        close = df['close']
        ma_series = close.rolling(window=window).mean()
        yesterday_ma = ma_series[-2]
        return yesterday_ma
    except:
        return None


def inquiry_moving_average(tickers):
    '''
    각 코인에 대해 5일 이동평균값을 계산
    :param tickers:
    :return:
    '''
    mas = {}
    for ticker in tickers:
        ma = cal_moving_average(ticker)
        mas[ticker] = ma
    return mas


def try_buy(portfolio, prices, targets, ma5s, budget_per_coin, holdings, high_prices):
    '''
    매수 조건 확인 및 매수 시도
    :param portfolio: 당일 선정된 포트폴리오
    :param prices: 각 코인에 대한 현재가
    :param targets: 각 코인에 대한 목표가
    :param ma5s: 5일 이동평균
    :param budget_per_coin: 코인별 최대 투자 금액
    :param holdings: 보유 여부
    :return:
    '''
    try:
        for ticker in portfolio:
            price = prices[ticker]              # 현재가
            target = targets[ticker]            # 목표가
            ma5 = ma5s[ticker]                  # 5일 이동평균
            high = high_prices[ticker]

            # 매수 조건
            # 1) 현재가가 목표가 이상이고
            # 2) 당일 고가가 목표가 대비 2% 이상 오르지 않았으며 (프로그램을 장중에 실행했을 때 고점찍고 하락중인 종목을 사지 않기 위해)
            # 3) 현재가가 5일 이동평균 이상이고
            # 4) 해당 코인을 보유하지 않았을 때
            if price >= target and high <= target * 1.02  and price >= ma5 and holdings[ticker] is False:
                orderbook = pybithumb.get_orderbook(ticker)
                asks = orderbook['asks']
                sell_price = asks[0]['price']
                unit = budget_per_coin/float(sell_price)

                if DEBUG is False:
                    bithumb.buy_market_order(ticker, unit)
                else:
                    print("BUY API CALLED", ticker, unit)

                time.sleep(INTERVAL)
                holdings[ticker] = True
    except:
        pass


def retry_sell(ticker, unit, retry_cnt=10):
    '''
    retry count 만큼 매도 시도
    :param ticker: 티커
    :param unit: 매도 수량
    :param retry_cnt: 최대 매수 시도 횟수
    :return:
    '''
    try:
        ret = None
        while ret is None and retry_cnt > 0:
            if DEBUG is False:
                ret = bithumb.sell_market_order(ticker, unit)
                time.sleep(INTERVAL)
            else:
                print("SELL API CALLED", ticker, unit)

            retry_cnt = retry_cnt - 1
    except:
        pass


def try_sell(tickers):
    '''
    보유하고 있는 모든 코인에 대해 전량 매도
    :param tickers: 빗썸에서 지원하는 암호화폐의 티커 목록
    :return:
    '''
    try:
        for ticker in tickers:
            unit = bithumb.get_balance(ticker)[0]
            min_order = MIN_ORDERS.get(ticker, 0.001)

            if unit >= min_order:
                if DEBUG is False:
                    ret = bithumb.sell_market_order(ticker, unit)
                    time.sleep(INTERVAL)
                else:
                    print("SELL API CALLED", ticker, unit)

                if ret is None:
                    retry_sell(ticker, unit, 10)
    except:
        pass


def try_trailling_stop(portfolio, prices, targets, holdings, high_prices):
    '''
    trailling stop
    :param portfolio: 포트폴리오
    :param prices: 현재가 리스트
    :param targets: 목표가 리스트
    :param holdings: 보유 여부 리스트
    :param high_prices: 각 코인에 대한 당일 최고가 리스트
    :return:
    '''
    try:
        for ticker in portfolio:
            price = prices[ticker]                          # 현재가
            target = targets[ticker]                        # 매수가
            high_price = high_prices[ticker]                # 당일 최고가

            gain = (price - target) / target                # 이익률
            gap_from_high = 1 - (price/high_price)          # 고점과 현재가 사이의 갭

            if gain >= TRAILLING_STOP_MIN_PROOFIT and gap_from_high >= TRAILLING_STOP_GAP and holdings[ticker] is True:
                unit = bithumb.get_balance(ticker)[0]
                min_order = MIN_ORDERS.get(ticker, 0.001)

                if unit >= min_order:
                    if DEBUG is False:
                        ret = bithumb.sell_market_order(ticker, unit)
                        time.sleep(INTERVAL)
                    else:
                        print("trailing stop", ticker, unit)

                    if ret is None:
                        retry_sell(ticker, unit, 10)

                    holdings[ticker] = False
    except:
        pass


def cal_budget(ticker):
    '''
    한 코인에 대해 투자할 투자 금액 계산
    :return: 원화잔고/투자 코인 수
    '''
    try:
        krw_balance = bithumb.get_balance(ticker)[2]
        budget_per_coin = int(krw_balance / COIN_NUMS)
        return budget_per_coin
    except:
        return 0


def update_high_prices(tickers, high_prices, cur_prices):
    '''
    모든 코인에 대해서 당일 고가를 갱신하여 저장
    :param tickers: 티커 목록 리스트
    :param high_prices: 당일 고가
    :param cur_prices: 현재가
    :return:
    '''
    try:
        for ticker in tickers:
            cur_price = cur_prices[ticker]
            high_price = high_prices[ticker]
            if cur_price > high_price:
                high_prices[ticker] = cur_price
    except:
        pass


def print_status(portfolio, now, tickers, prices, targets, high_prices):
    '''
    코인별 현재 상태를 출력
    :param tickers: 티커 리스트
    :param prices: 가격 리스트
    :param targets: 목표가 리스트
    :param high_prices: 당일 고가 리스트
    :param kvalues: k값 리스트
    :return:
    '''
    try:
        print("_" * 80)
        print(now)
        print(portfolio)
        for ticker in tickers:
            print("{:<6} 목표가: {:>8} 현재가: {:>8} 고가: {:>8}".format(ticker, int(targets[ticker]), int(prices[ticker]), int(high_prices[ticker])))
    except:
        pass
