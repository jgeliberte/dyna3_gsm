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


class LoggerSMS:
    def __init__(self):
        print("<< Imported Logger SMS")
    
    def start_server(self, gsm_mod, gsm_info):
        print(">> Starting Logger SMS server.")
        print(">> GSM Details :")
        print(gsm_mod)
        print(gsm_info)