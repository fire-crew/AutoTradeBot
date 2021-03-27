import os
import jwt
import uuid
import hashlib
import socket
from urllib.parse import urlencode
import requests
from pybithumb import Bithumb
"""
💎💎💎💎💎💎💎💎💎

Copyright : iLoveDev-Crew
LastUpdate : 2021-03-26
Title : Auto Crypto Trading Bot 
Version 1.0

💎💎💎💎💎💎💎💎💎
"""

with open("bithumb.txt", "r") as f:
    access_key = f.readline().replace("\n","")
    secret_key = f.readline().replace("\n","")

bithumb = Bithumb(access_key,  secret_key)

balance = bithumb.get_balance("BTC")


print("보유중 원화 : ",balance[2])


