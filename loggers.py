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
    def __init__(self, gsm_mod, db, gsm_id):
        print("<< Imported Logger SMS")
        self.gsm_mod = gsm_mod
        self.db = db
        self.gsm_id = gsm_id
    
    def start_server(self):
        print(">> Starting Logger SMS server.")
        while(True):
            sms_count = self.gsm_mod.count_sms()
            print(">> Message count(s): ",sms_count)
            if sms_count > 0:
                sms = self.fetch_logger_inbox()
                if len(sms) > 0:
                    print("<< Storing logger inbox to database.")
                    for x in sms:
                        store_status = self.db.insert_logger_inbox_sms(x.simnum, x.data, x.dt, self.gsm_id )
                        if not store_status:
                            print(">> Unknown mobile number. Ignoring.")
                else:
                    print(">> No new message. Sleeping for 10 seconds.\n\n")
                    time.sleep(10)
                self.gsm_mod.delete_sms()
            else:
                print(">> No new data. Sleeping for 10 seconds.\n\n")
                time.sleep(10)
    
    def store_logger_data():
        print(">> Storing logger data.")
    
    def validate_logger_data():
        print(">> Validating logger data.")
    
    def fetch_logger_inbox(self):
        print("<< Fetching logger inbox.")
        sms = []
        sms = self.gsm_mod.get_all_sms()
        return sms
