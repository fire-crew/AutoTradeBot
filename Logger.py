import os
import jwt
import uuid
import hashlib
import time
import datetime
import logging
import requests
import json
import logging
import Util

from BithumbAPI import *
from pandas.io.json import json_normalize
from pybithumb import Bithumb
from urllib.parse import urlencode


class Logger:
    """
    Logger

    'Logger' : log class
    'Date' : 2021.03.29
    'Author' : 최푸름
    'func' : 날짜별 로그 관리(dir에 error folder) + slack(슬랙) alarm
    """
    year = datetime.datetime.now().year
    mon = datetime.datetime.now().month
    day = datetime.datetime.now().day
    logger = logging.getLogger("logger")

    #constructor
    def __init__(self):
        self.logger_set()
    
    #logger set
    def logger_set(self): 
        '''
        title : 로그 셋팅(매일자정 실행설정필요)
        '''
        year = datetime.datetime.now().year
        mon = datetime.datetime.now().month
        day = datetime.datetime.now().day
        #log_formatting
        title = "log/{0}/{1}".format(year,mon)
        #dir없을시 생성
        Util.createDirectory(title)
        #로깅
        file_handler = logging.FileHandler(title+"/{0}_log.txt".format(day))
        stream_handler = logging.StreamHandler()
        logger = self.logger
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.DEBUG)
    

    # slack alarm
    def sendMSG_to_slack(self,text):
        '''
        title : 슬랙 알람
        param : text(string)
        '''
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        url = slackURL
        payload = { "text" : "[{0}]".format(now)+"  "+text}
        requests.post(url, json=payload)

    
    # logging
    def log(self,type,text):       
        '''
        title : logWrite
        param : type(string) 
                로그레벨 : DEBUG,INFO, WARNING, ERROR, CRITICAL
        param : text(string)
        '''
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if(type=="DEBUG"):
            return self.logger.debug("[{0}]".format(now)+text)
        elif(type=="INFO"):
            return self.logger.info("[{0}]".format(now)+text)
        elif(type=="WARNING"):
            return self.logger.warning("[{0}]".format(now)+text)
        elif(type=="ERROR"):
            return self.logger.error("[{0}]".format(now)+text)
        elif(type=="CRITICAL"):
            return self.logger.critical("[{0}]".format(now)+text)
        else:
            return self.log("INFO","[typeError]/n","[{0}]".format(now)+text)
   
 
