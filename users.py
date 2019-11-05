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
    
    def start_server(self, gsm_mod, gsm_info, db, gsm_id):
        print(">> Starting Users SMS server.")
        while(True):
            sms_count = gsm_mod.count_sms()
            print(">> Message count(s): ",sms_count)
            if sms_count <= 0:
                sms = self.fetch_inbox(gsm_mod)
                if len(sms) > 0:
                    print(">> Storing inbox to database.")
                else:
                    print(">> No new message.\n\n")

            pending_sms = self.fetch_pending_user_outbox(db, gsm_id)

            if len(pending_sms) > 0:
                print(">> Pending message(s): ",len(pending_sms),"")
                self.send_pending_sms(pending_sms, gsm_mod)
            else:
                print(">> No pending message.\n\n")
    
    def fetch_inbox(self, gsm_mod):
        print("<< Fetching inbox.")
        sms = []
        sms = gsm_mod.get_all_sms()
        return sms

    def fetch_pending_user_outbox(self, db, gsm_id):
        print("<< Fetching outbox.")
        pending = db.get_all_outbox_sms_users_from_db(5, gsm_id)
        return pending
    
    def send_pending_sms(self, sms, gsm_mod):
        for (user_id, mobile_id, outbox_id, stat_id,
         sim_num, firstname, lastname, sms_msg) in sms:
            print("<< Sending SMS to: ", firstname, lastname, " (",sim_num,")")
            print("<< Message: ", sms_msg)
            stat = gsm_mod.send_sms(sms_msg, sim_num)
            print(stat)
            if stat is 0:
                print(">> SMS ID #:",outbox_id," has successfully sent!")
            else:
                print(">> Error sending please contact the developer.")

            # print(user_id)
            # print(mobile_id)
            # print(outbox_id)
            # print(stat_id)
            # print(sim_num)
            # print(firstname)
            # print(lastname)
            # print(sms_msg)