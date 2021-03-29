"""
💎💎💎💎💎💎💎💎💎
Copyright : iLoveDev-Crew
LastUpdate : 2021-03-29 최푸름
Title : Auto Trading Bot 
Version 1.0
💎💎💎💎💎💎💎💎💎
"""

import os
import jwt
import uuid
import hashlib
import time
import datetime
import pybithumb
import logging
import requests
import json
import Logger
import strategy
from BithumbAPI import *

from urllib.parse import urlencode
from slacker import Slacker
from pandas.io.json import json_normalize

#전략 수립
#my_strategy = strategy.Strategy().strategy1()

#logger 생성
logger = Logger.Logger()
## 로깅 ################################################
## logger.log("INFO","Test") 
##   -- 로그레벨 : DEBUG,INFO, WARNING, ERROR, CRITICAL
## logger.sendMSG_to_slack("Test 성공") 
##   --슬랙보내기
## logger.logger_set()
##   -- 로깅 세팅 - 자정 실행 스케쥴필요
########################################################

tickers = pybithumb.get_tickers()      






    






