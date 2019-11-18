import time
import os
import sys
from datetime import datetime as dt
from datetime import timedelta as td

class ErrorLogger():
    def __init__(self, gsm_id, mod):
        self.gsm_id = gsm_id
        self.mod = mod
        ts = dt.today().strftime("%Y-%m-%d %H:%M:%S")
        message = ("Initialize logger after script reboot\n" \
            "Timestamp: %s \n" \
            "GSM ID#: %s \n" \
            "Module: %s\n\n") % (ts, gsm_id, mod)
        f = open("./logs/error_logs.txt", "a")
        f.write(message)
        f.close()
    
    def store_error_log(self, error_message):
        print("<< Saving error log..")
        ts = dt.today().strftime("%Y-%m-%d %H:%M:%S")
        message = (">> Error Log\n" \
            ">> Timestamp: %s \n" \
            ">> GSM ID#: %s \n" \
            ">> Module: %s\n" \
            ">> Error Log: %s") % (ts, gsm_id, mod, error_message)
        f = open("./logs/error_logs.txt", "a")
        f.write(message)
        f.close()