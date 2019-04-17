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
		    msg = "SetRawAll 0 0 0 0 0 0 0 0"
		    ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		    ls_sock.connect(lighting_server_address)
		    ls_sock.send(msg)
		    ls_sock.close()
		    time.sleep(2)

		    self.logger.debug("Start -> Dark to blue enriched light <-")
		    for x in range(25, 1875, 25):
			PS_a = cct_dict[10000][x]
			PS_b = cct_dict[10000][x+25]
			for xx in range(1, 2):
		            PS_0 = str((PS_a[0] + (PS_b[0] - PS_a[0])*xx/2))
			    PS_1 = str((PS_a[1] + (PS_b[1] - PS_a[1])*xx/2))
			    PS_2 = str((PS_a[2] + (PS_b[2] - PS_a[2])*xx/2))
			    PS_3 = str((PS_a[3] + (PS_b[3] - PS_a[3])*xx/2))
			    PS_4 = str((PS_a[4] + (PS_b[4] - PS_a[4])*xx/2))
			    PS_5 = str((PS_a[5] + (PS_b[5] - PS_a[5])*xx/2))
			    PS_6 = str((PS_a[6] + (PS_b[6] - PS_a[6])*xx/2))
			    PS_7 = str((PS_a[7] + (PS_b[7] - PS_a[7])*xx/2))
			    msg = "SetRawAll" + ' ' + PS_0 + ' ' + PS_1 + ' ' + PS_2 + ' ' + PS_3 + ' ' + PS_4 + ' ' + PS_5 + ' ' + PS_6 + ' ' + PS_7
			    ls_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			    ls_sock.connect(lighting_server_address)
			    ls_sock.send(msg)
			    ls_sock.close()
			    time.sleep(0.01)
		    self.logger.debug("Complete -> Dark to blue enriched light <-")

            elif data == "DEMO_4":
                pass

            elif "FAILED" in data.split():
                self.logger.error("Error in keypad: %s" % data)

            else:
                self.logger.error("Unknown message received from keypad: %s" % data)

        self.socket.close()
        self.logger.info('%s:%s disconnected. ' % self.address)
        lock.acquire()
        clients.remove(self)
        lock.release()

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
