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
import utils.error_logger as err_log
import traceback


class GsmSms:
    def __init__(self, num, sender, data, dt):
        self.num = num
        self.simnum = sender
        self.data = data
        self.dt = dt

class DefaultSettings:
    def __new__(self):
        config = configparser.ConfigParser()
        config.read('/home/pi/dyna3_gsm/utils/config.cnf')
        config["MASTER_DB_CREDENTIALS"]
        return config

class ResetException(Exception):
    pass

class GsmModem:
    defaults = None

    def __init__(self, ser_port='/dev/ttyUSB1', ser_baud=57600, pow_pin=33,
                 ring_pin=15):
        self.defaults = DefaultSettings()
        self.ser_port = ser_port
        self.ser_baud = ser_baud
        self.gsm = self.initialize_serial()
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pow_pin, GPIO.OUT)
        GPIO.output(pow_pin, 0)
        GPIO.setup(ring_pin, GPIO.IN)
        self.pow_pin = pow_pin
        self.ring_pin = ring_pin
        self.error_logger = err_log.ErrorLogger(0, 'Gsm Module')

    def initialize_serial(self):
        print('Connecting to GSM modem at', self.ser_port)
        
        gsm = serial.Serial()
        gsm.port = self.ser_port
        gsm.baudrate = self.ser_baud
        gsm.timeout = 2
        if(gsm.isOpen() == False):
            gsm.open()

        return gsm

    def set_gsm_defaults(self):
        GPIO.output(self.pow_pin, 0)
        time.sleep(
            int(self.defaults['GSM_DEFAULT_SETTINGS']['POWER_ON_DELAY']))
        try:
            for i in range(0, 4):
                self.gsm.write(str.encode('AT\r\n'))
                time.sleep(float(self.defaults['GSM_DEFAULT_SETTINGS']['WAIT_FOR_BYTES_DELAY']))
            print("<< Switching to no-echo mode: ", end=" ")
            print(self.execute_atcmd('ATE0').strip('\r\n'))
            print("<< Switching to PDU mode: ", end=" ")
            print(re.sub(r"[\n\t\s]*", "",
                         self.execute_atcmd('AT+CMGF=0').rstrip('\r\n')))
            print("<< Disabling unsolicited CMTI: ", end=" ")
            print(
                re.sub(r"[\n\t\s]*", "", self.execute_atcmd('AT+CNMI=2,0,0,0,0').rstrip('\r\n')))
            return True
        except AttributeError as err:
            self.error_logger.store_error_log(self.exception_to_string(err))
            return None

    def execute_atcmd(self, cmd="", expected_reply='OK'):
        if cmd == "":
            raise ValueError("No cmd given")
        try:
            self.gsm.flushInput()
            self.gsm.flushOutput()
            a = ''
            now = time.time()
            self.gsm.write(str.encode(cmd+'\r\n'))

            while (a.find(expected_reply) < 0 and a.find('ERROR') < 0):
                a = a + self.gsm.read(self.gsm.inWaiting()).decode('utf-8')
                time.sleep(float(self.defaults['GSM_DEFAULT_SETTINGS']['WAIT_FOR_BYTES_DELAY']))

            if time.time() > now + int(self.defaults['GSM_DEFAULT_SETTINGS']['REPLY_TIMEOUT']):
                a = '>> Error: GSM Unresponsive'
                except_str = (">> Raising exception to reset code "
                              "from GSM module reset")
                raise ResetException(except_str)
            elif a.find('ERROR') >= 0:
                print("Error (execute_atcmd): Error executing AT+ Command")
                return False
            else:
                return a
        except serial.SerialException as err:
            self.error_logger.store_error_log(self.exception_to_string(err))
            print("NO SERIAL COMMUNICATION (gsm_cmd)")

    def get_all_sms(self):
        allmsgs = 'd' + self.execute_atcmd('AT+CMGL=4')
        allmsgs = re.findall("(?<=\+CMGL:).+\r\n.+(?=\n*\r\n\r\n)", allmsgs)
        msglist = []
        tpdu_header = 0
        multi_sms_construct = ""
        for msg in allmsgs:
            try:
                pdu = re.search(r'[0-9A-F]{20,}', msg).group(0)
            except AttributeError as err:
                self.error_logger.store_error_log(self.exception_to_string(err))
                print(">> Error: cannot find pdu text", msg)
                continue
            try:
                smsdata = PduDecoder.decodeSmsPdu(pdu)
            except ValueError as err:
                print(">> Error: conversion to pdu (cannot decode "
                      "odd-length)")
                print(">> Error (get_all_sms): ", err)
                self.error_logger.store_error_log(self.exception_to_string(err))
                continue
            except IndexError as err:
                self.error_logger.store_error_log(self.exception_to_string(err))
                print(">> Error: convertion to pdu (pop from empty array)")
                continue

            if smsdata == "":
                continue
            try:
                txtnum = re.search(r'(?<= )[0-9]{1,2}(?=,)', msg).group(0)
            except AttributeError as err:
                print(">> Error: message may not have correct "
                      "construction", msg)
                self.error_logger.store_error_log(self.exception_to_string(err))
                continue

            txtdatetimeStr = smsdata['time']
            txtdatetimeStr = txtdatetimeStr.strftime('%Y-%m-%d %H:%M:%S')

            if smsdata['tpdu_length'] < 159:
                if tpdu_header != 0:
                    tpdu_header =self.increamentHexPDU(tpdu_header)
                    if (tpdu_header in pdu):
                        smsdata['text'] = multi_sms_construct + smsdata['text']
                        tpdu_header = self.increamentHexPDU(tpdu_header)
                        smsItem = GsmSms(txtnum, smsdata['number'].strip('+'),
                            str(smsdata['text']), txtdatetimeStr)
                        msglist.append(smsItem)
                else:
                    smsdata['text'] = smsdata['text'].encode('utf-16','surrogatepass').decode('utf-16')
                    smsItem = GsmSms(txtnum, smsdata['number'].strip('+'),
                                     str(smsdata['text']), txtdatetimeStr)
                    msglist.append(smsItem)
            else:
                multi_sms_construct = multi_sms_construct + smsdata['text']
                tpdu_header = pdu[54:66]
        return msglist

    def increamentHexPDU(self, pdu):
        tpdu_parts = int(str(pdu[-4:]), 16) + 1
        tpdu_parts = hex(tpdu_parts)[2:]
        isolated_part = str(pdu[:-3])
        increamented_tpdu = str(isolated_part)+str(tpdu_parts)
        return increamented_tpdu

    def send_sms(self, msg, number):
        start_time = time.time()
        try:
            pdulist = PduDecoder.encodeSmsSubmitPdu(number, msg)
        except Exception as e:
            self.error_logger.store_error_log(self.exception_to_string(e))
            print("Error in pdu conversion. Skipping message sending")
            return -1
        parts = len(pdulist)
        count = 1
        for pdu in pdulist:
            a = ''
            now = time.time()
            temp_pdu = self.formatPDUtoSIM800(str(pdu))
            preamble = "AT+CMGS="+str(int((len(temp_pdu)-2)/2))
            self.gsm.write(str.encode(preamble+"\r"))
            now = time.time()
            while (a.find('>') < 0 and a.find("ERROR") < 0 and
                   time.time() < now + int(self.defaults['GSM_DEFAULT_SETTINGS']['SEND_INITIATE_REPLY_TIMEOUT'])):
                a = a + self.gsm.read(self.gsm.inWaiting()).decode('utf-8')
                time.sleep(
                    float(self.defaults['GSM_DEFAULT_SETTINGS']['WAIT_FOR_BYTES_DELAY']))
                print('.', end = " ")

            if (time.time() > now + int(self.defaults['GSM_DEFAULT_SETTINGS']['SEND_INITIATE_REPLY_TIMEOUT']) or
                    a.find("ERROR") > -1):
                print('>> Error: GSM Unresponsive at finding >')
                return-1
            else:
                print('>', end=" ")

            a = ''
            now = time.time()
            self.gsm.write(str.encode(str(temp_pdu)+chr(26)))
            while (a.find('OK') < 0 and a.find("ERROR") < 0 and
                   time.time() < now + int(self.defaults['GSM_DEFAULT_SETTINGS']['REPLY_TIMEOUT'])):
                a += self.gsm.read(self.gsm.inWaiting()).decode('utf-8')
                time.sleep(
                    float(self.defaults['GSM_DEFAULT_SETTINGS']['WAIT_FOR_BYTES_DELAY']))
                print('-', end=" ")

            if time.time() - int(self.defaults['GSM_DEFAULT_SETTINGS']['SENDING_REPLY_TIMEOUT']) > now:
                print('>> Error: timeout reached')
                return -1
            elif a.find('ERROR') > -1:
                print('>> Error: GSM reported ERROR in SMS reading')
                return -1
            else:
                print("Sending execution time:", (time.time() - start_time))
                print(">> Part %d/%d: Message sent!" % (count, parts))
                count += 1
        return 0

    def count_sms(self):
        while True:
            b = ''
            c = ''
            b = self.execute_atcmd("AT+CPMS?")

            try:
                c = int(b.split(',')[1])
                if c > 0:
                    print('\n>> Received', c, 'message/s; CSQ:', self.get_csq())

                return c
            except IndexError as err:
                self.error_logger.store_error_log(self.exception_to_string(err))
                print('count_sms b = ', b)
                if b:
                    return 0
                else:
                    return -1
            except (ValueError, AttributeError) as err:
                self.error_logger.store_error_log(self.exception_to_string(err))
                print('>> ValueError:')
                print(b)
                print("ERROR (count_sms):", err)
                print('>> Retryring message reading')
            except TypeError as err:
                self.error_logger.store_error_log(self.exception_to_string(err))
                print(">> TypeError")
                return -2

    def get_csq(self):
        csq_reply = self.execute_atcmd("AT+CSQ")
        try:
            csq_val = int(re.search("(?<=: )\d{1,2}(?=,)", csq_reply).group(0))
            return csq_val
        except (ValueError, AttributeError, TypeError) as err:
            self.error_logger.store_error_log(self.exception_to_string(err))
            raise ResetException

    def delete_sms(self, module = 2):
        print("\n>> Deleting all read messages")
        try:
            if module == 1:
                self.execute_atcmd("AT+CMGD=0,2").strip()
            elif module == 2:
                self.execute_atcmd("AT+CMGDA=1").strip()
            else:
                raise ValueError("Unknown module type")
        except ValueError as err:
            self.error_logger.store_error_log(self.exception_to_string(err))
            print('>> Error deleting messages')

    def reset(self):
        print(">> Resetting GSM Module ...")
        try:
            GPIO.output(self.pow_pin, 1)
            time.sleep(int(self.defaults['GSM_DEFAULT_SETTINGS']['RESET_DEASSERT_DELAY']))
            try:
                self.execute_atcmd("AT+CPOWD=1", "NORMAL POWER DOWN")
            except ResetException:
                print (">> Error: unable to send powerdown signal. "
                    "Will continue with hard reset")
            GPIO.output(self.pow_pin, 0)
            time.sleep(int(self.defaults['GSM_DEFAULT_SETTINGS']['RESET_ASSERT_DELAY']))
            GPIO.output(self.pow_pin, 1)
            time.sleep(int(self.defaults['GSM_DEFAULT_SETTINGS']['RESET_DEASSERT_DELAY']))
            GPIO.cleanup()
            print ('>> Done')
            sys.exit(0)
        except ImportError as err:
            self.error_logger.store_error_log(self.exception_to_string(err))
            return

    def formatPDUtoSIM800(self, pdu):
        first = str(pdu[:2])
        second = str(int(pdu[2:4])-10)
        third = "000C91"
        fourth = str(pdu[10:22])
        fifth = str(pdu[22:26])
        sixth = "AA"
        seventh = str(pdu[26:])
        if len(str(second)) == 1:
            second = "0"+str(second)
        final = str(first)+str(second)+str(third)+str(fourth)+str(fifth)+str(sixth)+str(seventh)
        return final

    def exception_to_string(self, excp):
        stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=?? 
        pretty = traceback.format_list(stack)
        return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)
