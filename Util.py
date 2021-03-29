import os
import jwt
import uuid
import hashlib
import time
import datetime
import requests
import json
import Logger

from pandas.io.json import json_normalize
from urllib.parse import urlencode

#dir 없을시 생성
def createDirectory(directory): 
    '''
    title : 디렉토리 생성
    param : directory(string)
    '''
    try: 
        if not os.path.exists(directory): 
            os.makedirs(directory) 
    except OSError: 
        print("Error: Failed to create the directory.")
        logger.sendMSG_to_slack("---[Error]: log dir 생성오류---")

