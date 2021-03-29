import os
import jwt
import uuid
import hashlib
import time
import datetime
import logging
import requests
import json
import Logger
import pybithumb 

from BithumbAPI import *
from urllib.parse import urlencode
from pandas.io.json import json_normalize

class Strategy:
    print("안녕")
    """
    Strategy

    'Strategy' : log class
    'Date' : 2021.03.29
    'Author' : 최푸름
    'func' : 전략수립 클래스 
         - 1. 변동성 돌파 전략
         - 2. 실시간 기울기 파악매매법(작성중)
    """

    ############# 필드 상수  #####################################################################################
    INTERVAL = 3                                        # 매수 시도 interval (1초 기본)
    DEBUG = False                                       # True: 매매 API 호출 안됨, False: 실제로 매매 API 호출
    
    COIN_NUMS = 10                                      # 분산 투자 코인 개수 (자산/COIN_NUMS를 각 코인에 투자)
    LARRY_K = 0.5
    BALANCE = 0.5                                       # 자산의 50%만 투자 50%는 현금 보유

    GAIN = 0.3                                          # 30% 이상 이익시 50% 물량 익절
    DUAL_NOISE_LIMIT1 = 0.75                            # 듀얼 노이즈가 0.75 이하인 종목만 투자                        
    #############################################################################################################
    
    MIN_ORDERS = {"BTC": 0.001, "ETH": 0.01, "DASH": 0.01, "LTC": 0.01, "ETC": 0.1, "XRP": 10, "BCH": 0.001,
              "XMR": 0.01, "ZEC": 0.01, "QTUM": 0.1, "BTG": 0.1, "EOS": 0.1, "ICX": 1, "VEN": 1, "TRX": 100,
              "ELF": 10, "MITH": 10, "MCO": 10, "OMG": 0.1, "KNC": 1, "GNT": 10, "HSR": 1, "ZIL": 100,
              "ETHOS": 1, "PAY": 1, "WAX": 10, "POWR": 10, "LRC": 10, "GTO": 10, "STEEM": 10, "STRAT": 1,
              "ZRX": 1, "REP": 0.1, "AE": 1, "XEM": 10, "SNT": 10, "ADA": 10}


    #변수#
    logger = Logger.Logger()

    now = datetime.datetime.now()                                           # 현재 시간 조회
    sell_time1, sell_time2 = make_sell_times(now)                           # 초기 매도 시간 설정
    setup_time1, setup_time2 = make_setup_times(now)                        # 초기 셋업 시간 설정
    
    tickers = pybithumb.get_tickers()                                       # 티커 리스트 얻기
    targets = inquiry_targets(tickers)                                      # 코인별 목표가 계산
    mas = inquiry_moving_average(tickers)                                   # 코인별로 5일 이동평균 계산
    budget_per_coin = cal_budget()                                          # 코인별 최대 배팅 금액 계산
    
    portfolio = select_portfolio(tickers)                                   # 듀얼 노이즈 전략 기반으로 portfolio 선정
    holdings = {ticker:False for ticker in tickers}                       # 보유 상태 초기화
    high_prices = inquiry_high_prices(tickers)                              # 코인별 당일 고가 저장
                       

    def strategy1(self):
        '''
        title : 변동성 돌파전략
        '''
        now = datetime.datetime.now()

        # 당일 청산 (23:50:00 ~ 23:50:10)
        if sell_time1 < now < sell_time2:
            try_sell(tickers)                                                  # 각 가상화폐에 대해 매도 시도
            holdings = {ticker:True for ticker in tickers}                     # 당일에는 더 이상 매수되지 않도록
            time.sleep(10)

        # 새로운 거래일에 대한 데이터 셋업 (00:01:00 ~ 00:01:10)
        if setup_time1 < now < setup_time2:
            tickers = pybithumb.get_tickers()                                   # 티커 목록 갱신
            try_sell(tickers)                                                   # 매도 되지 않은 코인에 대해서 한 번 더 매도 시도

            noises = cal_noise(tickers)
            targets = inquiry_targets(tickers)                                  # 목표가 갱신
            mas = inquiry_moving_average(tickers)                               # 이동평균 갱신
            budget_per_coin = cal_budget()                                      # 코인별 최대 배팅 금액 계산

            sell_time1, sell_time2 = make_sell_times(now)                       # 당일 매도 시간 갱신
            setup_time1, setup_time2 = make_setup_times(now)                    # 다음 거래일 셋업 시간 갱신

            holdings = {ticker:False for ticker in tickers}                    # 모든 코인에 대한 보유 상태 초기화
            high_prices = {ticker: 0 for ticker in tickers}                    # 코인별 당일 고가 초기화
            time.sleep(10)

        # 현재가 조회
        prices = inquiry_cur_prices(tickers)
        update_high_prices(tickers, high_prices, prices)
        print_status(now, tickers, prices, targets, noises, mas, high_prices)

        # 매수
        if prices is not None:
            try_buy(tickers, prices, targets, noises, mas, budget_per_coin, holdings, high_prices)

        # 익절
        try_profit_cut(tickers, prices, targets, holdings)

        time.sleep(INTERVAL)


    def update_info(self): 
        '''
        title : 전략 업데이트(매일 자정 실행)
        '''
        ## 필드변수 초기화##
        now = datetime.datetime.now()                                           
        sell_time1, sell_time2 = make_sell_times(now)                           
        setup_time1, setup_time2 = make_setup_times(now)                        
        
        tickers = pybithumb.get_tickers()                                       
        
        noises = cal_noise(tickers)
        targets = inquiry_targets(tickers)                                     
        mas = inquiry_moving_average(tickers)                                  
        budget_per_coin = cal_budget()                                         
        
        holdings = {ticker:False for ticker in tickers}                         
        high_prices = inquiry_high_prices(tickers)                              
        ##########################################


