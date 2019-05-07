#!/bin/sh
import socket, threading
import getpass
import telnetlib
import time
import logging
#from pysnmp.hlapi import *
from ColorTemperature import cct_dict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

control_server_address = ("192.168.2.20", 60000)
lighting_server_address = ("192.168.2.20", 50000)

CCT = 3600
LUX = 1600


class ChatServer(threading.Thread):
    def __init__(self, (socket, address), tn, logger=None):
        threading.Thread.__init__(self)
        self.logger = logger or logging.getLogger(__name__)
        self.socket = socket
        self.address = address
        self.tn = tn
        self.l_sock = None

    def run(self):
        global KeyPushTimes
        global KeyPad_EN
        global CCT
        global LUX
	global LightConditions
	LightConditions = [0, 0, 0, 0, 0, 0, 0, 0]

        lock.acquire()
        clients.append(self)
        lock.release()

        self.logger.info('%s:%s connected. ' % self.address)
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            self.logger.info("Received data: %s" % data)
            if data == "KEYPAD_EN":
                self.logger.debug(KeyPushTimes)
                if not KeyPad_EN:
                    KeyPushTimes += 1
                if KeyPushTimes >= 4 and not KeyPad_EN:  # Enter demo mode
                    try:
                        self.tn.write("LEDBLUES 99\n")
                        KeyPad_EN = True
                        self.logger.info("Keypad is enabled")
                        self.l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.l_sock.connect(control_server_address)
                        self.l_sock.send('demo')
                        self.l_sock.close()
                        CCT = 3600
                        LUX = 1600
                    except Exception as m:
                        self.logger.error("Error while attempting to enable keypad: %s" % m)
                        # TODO: Write routine for reconnecting to keypad - raise telnet error to outer scope?
                    finally:
                        KeyPushTimes = 0

            elif data == "KEYPAD_DIS":
                try:
                    self.tn.write("LEDBLUES 0\n")
                    KeyPad_EN = False
                    self.logger.info("Keypad is disabled")
                    # self.tn.write("LEDREDS 0\n")
                    self.l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.l_sock.connect(control_server_address)
                    self.l_sock.send('stop')
                    self.l_sock.close()
                except Exception as m:
                    self.logger.error("Error while attempting to disable keypad: %s" % m)
                    # TODO: Write routine for reconnecting to keypad

            elif data == "CCT_UP":
                self.logger.debug("CCT+")
                if KeyPad_EN:
                    # self._flash_color()
                    CCT = CCT + 400
                    if CCT > 10000:
                        CCT = 10000
                    self.logger.debug("CCT: %s; LUX: %s" % (CCT, LUX))
                    self._set_lighting_condition(CCT, LUX)

            elif data == "CCT_DOWN":
                self.logger.debug("CCT-")
                if KeyPad_EN:
                    # self._flash_color()
                    CCT = CCT - 400
                    if CCT < 1600:
                        CCT = 1600
                    self.logger.debug("CCT: %s; LUX: %s" % (CCT, LUX))
                    self._set_lighting_condition(CCT, LUX)

            elif data == "LUX_UP":
                self.logger.debug("LUX+")
                if KeyPad_EN:
                    LUX = LUX + 200
                    if LUX > 1800:
                        LUX = 1800
                    self.logger.debug("CCT: %s; LUX: %s" % (CCT, LUX))
                    self._set_lighting_condition(CCT, LUX)

            elif data == "LUX_DOWN":
                self.logger.debug("LUX-")
                if KeyPad_EN:
                    LUX = LUX - 200
                    if LUX < 200:
                        LUX = 200
                    self.logger.debug("CCT: %s; LUX: %s" % (CCT, LUX))
                    self._set_lighting_condition(CCT, LUX)

            elif data == "DEMO_3":
                self.logger.debug("Demo_3")
		if KeyPad_EN:

            	    msg = "PLAY Day_of_sunlight.lso"
               	    self.logger.debug("Msg: %s" % msg)
            	    ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            	    ls_sock.connect(lighting_server_address)
            	    ls_sock.send(msg)

#                    self._set_lighting_condition(1600, 25)
#		    time.sleep(0.01)

#		    for indeks in range(1, 120):
#			CCT = 1600+100*indeks
#			INT = 25+25*indeks
#			CCT_p = 1600+100*(indeks-1)
#			INT_p = 25+25*(indeks-1)
#		        self._set_lighting_condition_Fix(0, CCT, INT, CCT_p, INT_p)
#			self._set_lighting_condition_Fix(1, CCT-1000, INT-200, CCT_p-1000, INT_p-200)
#			self._set_lighting_condition_Fix(2, CCT-2000, INT-400, CCT_p-2000, INT_p-400)
#			self._set_lighting_condition_Fix(3, CCT-2000, INT-400, CCT_p-2000, INT_p-400)
#			self._set_lighting_condition_Fix(4, CCT-3000, INT-600, CCT_p-3000, INT_p-600)
#			self._set_lighting_condition_Fix(5, CCT-3000, INT-600, CCT_p-3000, INT_p-600)
#			self._set_lighting_condition_Fix(6, CCT-4000, INT-800, CCT_p-4000, INT_p-800)
#			self._set_lighting_condition_Fix(7, CCT-5000, INT-900, CCT_p-5000, INT_p-900)
#			self._set_lighting_condition_Fix(8, CCT-5000, INT-900, CCT_p-5000, INT_p-900)
#		    indeks = 0
#		    for indeks in range(1, 120):
#			CCT = 15000-100*indeks
#			INT = 2800-25*indeks
#			INT=1000
#		        self._set_lighting_condition_Fix(0, CCT, INT)
#			self._set_lighting_condition_Fix(1, CCT-1000, INT-200)
#			self._set_lighting_condition_Fix(2, CCT-2000, INT-400)
#			self._set_lighting_condition_Fix(3, CCT-2000, INT-400)
#			self._set_lighting_condition_Fix(4, CCT-3000, INT-600)
#			self._set_lighting_condition_Fix(5, CCT-3000, INT-600)
#			self._set_lighting_condition_Fix(6, CCT-4000, INT-800)
#			self._set_lighting_condition_Fix(7, CCT-5000, INT-900)
#			self._set_lighting_condition_Fix(8, CCT-5000, INT-900)

	          #  	condition = cct_dict[CCT][INT]
        	  #  	condition = [str(x) for x in condition]
        	  #  	msg = "SetRawFix" + ' 0 ' + ' '.join(condition)
        	  #  	self.logger.debug("Msg: %s" % msg)
		  #  	self._send_message(msg)

            elif data == "DEMO_4":
		self.logger.debug("Demo_4")
		if KeyPad_EN:
   		    msg = "SetRawFix 0 11 0 0 0 0 0 0 0.01"
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 1 0 6 0 0 0 0 0 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 2 0 0 14 0 0 0 0 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 3 0 0 0 11 0 0 0 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 4 0 0 0 0 70 0 0 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 5 0 0 0 0 0 39 0 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 6 0 0 0 0 0 0 9 0.01"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(0.01)
   		    msg = "SetRawFix 7 0 0 0 0 0 0 0 20"
    		    self.logger.debug(msg)
		    self._send_message(msg)
		    time.sleep(5)
		    for intens in range(0, 50):
		    	msg = "SetRawAll " + str(10.8*intens/50) + " 0 0 0 0 0 0 0"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 " + str(5.54*intens/50)+ " 0 0 0 0 0 0"
		    	self._send_message(msg)
			time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 " + str(14.1*intens/50) + " 0 0 0 0 0"
		    	self._send_message(msg)
			time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 14.1 " + str(10.62*intens/50) + " 0 0 0 0"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 14.1 10.62 " + str(69.75*intens/50) + " 0 0 0"
		    	self._send_message(msg)
			time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 14.1 10.62 69.75 " + str(38.84*intens/50) + " 0 0"
		    	self._send_message(msg)
			time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 14.1 10.62 69.75 38.84 " + str(9.12*intens/50) + " 0"
		    	self._send_message(msg)
			time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 10.8 5.54 14.1 10.62 69.75 38.84 9.12 " + str(20.02*intens/50)
		    	self._send_message(msg)
		    	time.sleep(0.01)

		    time.sleep(5)
		    for intens in range(0, 50):
		    	msg = "SetRawAll " + str(10.8*(50-intens)/50) + " 5.54 14.1 10.62 69.75 38.84 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 " + str(5.54*(50-intens)/50) + " 14.1 10.62 69.75 38.84 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 " + str(14.1*(50-intens)/50) + " 10.62 69.75 38.84 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 0 " + str(10.62*(50-intens)/50) + " 69.75 38.84 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 0 0 " + str(69.75*(50-intens)/50) + " 38.84 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 0 0 0 " + str(38.84*(50-intens)/50) + " 9.12 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 0 0 0 0 " + str(9.12*(50-intens)/50) + " 20.02"
		    	self._send_message(msg)
		    	time.sleep(0.01)
		    time.sleep(3)
		    for intens in range(0, 50):
		    	msg = "SetRawAll 0 0 0 0 0 0 0 " + str(20.02*(50-intens)/50)
		    	self._send_message(msg)
		    	time.sleep(0.01)

# Color gradient
		   # for fix in range (0, 10):
#
#			msg = "SetRawFix " + str(fix) + " 1 2 3 4 5 6 7 8"
 #   		        self.logger.debug(msg)
#			self._send_message(msg)
#		        time.sleep(0.05)


            elif "FAILED" in data.split():
                self.logger.error("Error in keypad: %s" % data)

            else:
                self.logger.error("Unknown message received from keypad: %s" % data)

        self.socket.close()
        self.logger.info('%s:%s disconnected. ' % self.address)
        lock.acquire()
        clients.remove(self)
        lock.release()

    def _send_message(self, msg):
        ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls_sock.connect(lighting_server_address)
	ls_sock.send(msg)
	ls_sock.close()


    def _flash_color(self):
        # self.tn.write("LEDBLUES 5\n")
        # time.sleep(0.1)
        # self.tn.write("LEDREDS 0\n")
        # time.sleep(0.1)
        # self.tn.write("LEDRED 1 100\n")
        # time.sleep(1)
        # self.tn.write("LEDREDS 0\n")
        # time.sleep(0.1)
        # self.tn.write("LEDBLUES 99\n")
        pass

    def _set_lighting_condition(self, temperature, intensity):
        if temperature < 1600:
            temperature = 1600
        elif temperature > 10000:
            temperature = 10000
        if intensity < 25:
            intensity = 25
        elif intensity > 1900:
            intensity = 1900

        condition = cct_dict[temperature][intensity]
        condition = [str(x) for x in condition]
        msg = "SetRawAll" + ' ' + ' '.join(condition)
        self.logger.debug("Msg: %s" % msg)
        ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls_sock.connect(lighting_server_address)
        ls_sock.send(msg)
        ls_sock.close()

    def _set_lighting_condition_Fix(self, fix, temperature, intensity, temperature_p, intensity_p):
	SetToLight = [0,0,0,0,0,0,0,0]
        if (temperature > 1600) and (temperature < 5000) and (intensity > 25) and (intensity < 1900) and \
		(temperature_p > 1600) and (temperature_p < 5000) and (intensity_p > 25) and (intensity_p < 1900):
            condition = cct_dict[temperature][intensity]
	    LightConditions = cct_dict[temperature_p][intensity_p]
#            condition = [str(x) for x in condition]
# Here smooth transition needs to be implemented
            self.logger.debug("Condition ->$$$$$$: %s" % str(condition))

	    for k in range (1, 6):
	    	for i in range (0, 8):
		    SetToLight[i]=float(condition[i])+(float(condition[i])-float(LightConditions[i]))*k/5

	    	self.logger.debug(SetToLight)

		SetToLight = [str(x) for x in SetToLight]
            	msg = "SetRawFix" + ' ' + str(fix) + ' ' + ' '.join(SetToLight)
            	self.logger.debug("Msg: %s" % msg)
            	ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            	ls_sock.connect(lighting_server_address)
            	ls_sock.send(msg)
            	ls_sock.close()
	    	time.sleep(0.01)


def raritan_set(ch, val):
    """
    Set PDU values by port number and status value.
    val=1 is on, val=2 is off
    :param ch: port number
    :param val: status value
    :return: None
    """
    for (errorIndication, errorStatus, errorIndex, varBinds) in setCmd(
            SnmpEngine(),
            CommunityData('private'),
            UdpTransportTarget(('192.168.1.5', 161)),
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.3.1.1.4.'
                                      + str(ch)), Integer(val)),
            lookupMib=False):
        # Check for errors and print out results
        if errorIndication:
            print(errorIndication)
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex
                                and varBinds[int(errorIndex)-1][0]
                                or '?'))
        else:
            for name, val in varBinds:
                print('%s = %s' % (name.prettyPrint(),
                                   val.prettyPrint()))


#def keypad_reset():
#    raritan_set(8, 2)
#    time.sleep(1)
#    raritan_set(8, 1)


def keypad_ping(tn_sock):
    while True:
        try:
            tn_sock.write("VER\n")
            ver = tn_sock.read_until("\n")
            logger.debug("Version response: %s" % ver)
        except Exception as m:
            # keypad stuck
            logger.error("Error while connecting to keypad: %s" % m)
            logger.error("Keypad unresponsive - resetting keypad")
            keypad_reset()
        finally:
            time.sleep(10)


if __name__ == "__main__":
    HOST = '192.168.2.20'
    PORT = 51000

    KEYPAD_HOST = "192.168.2.21"
    KEYPAD_PORT = "23"

    logger.info("Starting keypad service")

#    logger.debug("Resetting keypad")
#    keypad_reset()
#    time.sleep(1)

    logger.debug("Creating socket to receive keypad messages")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.debug("Binding socket to (%s, %s)" % (HOST, PORT))
    s.bind((HOST, PORT))
    s.listen(4)
    logger.debug("Listening for clients")
    clients = []  # list of clients connected
    lock = threading.Lock()
    KeyPushTimes = 0
    KeyPad_EN = False
    tn = None

    while True:
        try:
            logger.debug("Starting telnet server for controlling keypad on socket (%s, %s)"
                         % (KEYPAD_HOST, KEYPAD_PORT))
            tn = telnetlib.Telnet(KEYPAD_HOST, KEYPAD_PORT)
            tn.write("admin\n")
            tn.write("LESA2018\n")
            # client = s.accept()
            # resp = client.recv(1024)
            # logger.info("Response from keypad: %s" % resp)
            logger.debug("Connected to keypad")
#            tn.write("REBOOT\n")
            keep_alive = threading.Thread(target=keypad_ping, args=(tn,))
            keep_alive.start()
#             keypad_ping(tn)

            while True:  # wait for socket to connect
                logger.info("Waiting for client")
                client = s.accept()
                ChatServer(client, tn, logger=logger).start()
        except Exception as e:
            logger.debug(e)
            if tn:
                try:
                    logger.debug("Closing telnet socket")
                    tn.close()
                except Exception as e:
                    logger.error("Error closing telnet socket: %s" % e)
            logger.info("Attempting to reconnect to keypad telnet server")
            continue
