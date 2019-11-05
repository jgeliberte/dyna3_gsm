import serial
import time
import re
import RPi.GPIO as GPIO
from gsmmodem import pdu as PduDecoder
from datetime import datetime as dt
from datetime import timedelta as td
import configparser
from pprint import pprint
import sys


class UserSMS:
    def __init__(self):
        print("<< Imported User SMS")
    
    def start_server(self, gsm_mod, gsm_info):
        print(">> Starting Users SMS server.")
        print(">> GSM Details :")
        pprint(vars(gsm_mod))
        pprint(gsm_info)