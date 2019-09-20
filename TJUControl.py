import threading
from EventScheduler import EventScheduler, generate_test_file
import LightServer
import socket
#from pysnmp.hlapi import *
import logging
import logging.config
import time


class TJUControl(threading.Thread):
    def __init__(self, logger=None,
                       event_list_file="spreadsheets/Data.txt",
                       control_address=("192.168.2.22", 60000),
                       light_server_address=("192.168.2.22", 50000),
                       relay_address=("192.168.2.41", 50000)):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("Initializing TJU Control thread")
        super(TJUControl, self).__init__(name="TJUControl")
        self._stop_event = threading.Event()

        # System modes
        self.standard_mode = 0
        self.experiment_mode = 1
        self.demo_mode = 2

        # Server parameters
        self.event_list_file = event_list_file
        self.control_address = control_address
        self.light_server_address = light_server_address
        self.relay_address = relay_address

        # PDU Channels
        self.pdu_experiment = 1
        self.pdu_switch = 2
        self.pdu_task = 4

        # Turn on all PDU channels -> Not on this version
       # self.logger.info("Turning on all PDU channels")
       # self.raritan_set(1, 1)
       # self.raritan_set(2, 1)
       # self.raritan_set(3, 1)
       # self.raritan_set(4, 1)
       # self.raritan_set(5, 1)
       # self.raritan_set(6, 1)
       # self.raritan_set(7, 1)
       # self.raritan_set(8, 1)

        # Create socket to receive commands
        self.logger.info("Creating control socket at %s, port %s" %
                         self.control_address)
        self.s_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s_control.bind(self.control_address)

        # Create relay socket
        self.s_relay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Start light server and enter standard operating mode
        self.logger.info("Waiting for lights to start-up")
        time.sleep(10)  # Wait for lights to start up
        self.logger.info("Creating light server object and starting thread")
        self.ls = LightServer.LightServer(self.light_server_address)
        self.ls.start()
        self.ls.set_mode(self.standard_mode, startup=True)

        # Initialize event scheduler
        self.es = EventScheduler(self.event_list_file,
                                 self.light_server_address)

        self.logger.info("TJU Control thread initialized")

    def run(self):
        self.logger.info("Starting TJU Control thread")
        self.s_control.listen(1)
        self.s_control.settimeout(10)
        while not self._stop_event.isSet():
            self.logger.info("Waiting for client")
            client, address = None, None
            while not client and not self._stop_event.isSet():
                try:
                    client, address = self.s_control.accept()
                    client.settimeout(5)
                except socket.timeout:
                    pass
            while not self._stop_event.isSet():
                try:
                    data = client.recv(1024)
                    if not data:
                        break
                    elif data.lower() == "start":
                        self._start_sequence()
                    elif data.lower() == 'stop' or data.lower() == 'end':
                        self._stop_sequence()
                    elif data.lower() == "demo":
                        self._demo()
                    elif data.lower() == "stop_control":
                        self.stop()
                    else:
                        self.logger.warning("Unrecognized control "
                                            "command received")
                except socket.error as msg:
                    self.logger.error(msg)
        self.logger.info("TJU Control thread ended")

    def stop(self):
        self.logger.info("Received stop_control command")
        if self.ls.is_alive():
            self.ls.stop()
        if self.es.is_alive():
            self.es.stop()
        self.logger.info("Turning off all PDU channels")
#        self.raritan_set(1, 2)
#        self.raritan_set(2, 2)
#        self.raritan_set(3, 2)
#        self.raritan_set(4, 2)
#        self.raritan_set(5, 2)
#        self.raritan_set(6, 2)
#        self.raritan_set(7, 2)
#        self.raritan_set(8, 2)
        self.logger.info("Closing control socket")
        self.s_control.close()
        self.logger.info("Stopping control thread")
        self._stop_event.set()

    def _start_sequence(self):
        """
        Execute start sequence
        1. Send "Start" to 192.168.2.41:50000
        2. Turn on PDU 1 (Main experiment lights)
        3. Turn off PDU 8 (Keypad)
        4. Start LightServer thread (if not running)
        4. Start EventScheduler thread

        :return: None
        """
        self.logger.info("Received start command, starting control sequence")
        if not self.es.is_alive():
            try:
                self.ls.set_mode(self.experiment_mode)
                self.logger.info("Sending start command to relay")
                try:
                    self.logger.info("Connecting to relay socket at %s, port %s" %
                         self.relay_address)
                    self.s_relay.connect(self.relay_address)
                    self.logger.info("Sending start message to relay")
                    self.s_relay.send("start")
                    self.s_relay.close()
                except socket.error as m:
                    self.logger.error("Error sending message to relay: %s", m)
#                self.logger.info("Turning off keypad")
#                self.raritan_set(8, 2)
                # Start event scheduler
#                generate_test_file(self.event_list_file, 5)
                self.es = EventScheduler(self.event_list_file,
                                         self.light_server_address)
                self.es.start()
            except Exception as e:
                self.logger.error("Error starting control thread: %s" % e)
        else:
            self.logger.warning("Event scheduler thread already running"
                                " - cannot start thread twice")

    def _stop_sequence(self):
        """
        Execute stop sequence
        1. Stop "EventScheduler.py" script
        2. Return to standard mode
        3. Send "Stop" to relay 

        :return: None
        """
        self.logger.info("Received stop command, executing stop sequence")
        try:
            self.es.stop()
            self.logger.info("Sending stop command to relay")
            try:
                self.logger.info("Connecting to relay socket at %s, port %s" %
                         self.relay_address)
                self.s_relay.connect(self.relay_address)
                self.logger.info("Sending stop message to relay")
                self.s_relay.send("stop")
                self.s_relay.close()
            except socket.error as m:
                self.logger.error("Error sending message to relay: %s", m)
#            self.logger.info("Turning on keypad")
#            self.raritan_set(8, 1)
            time.sleep(1)
            self.ls.set_mode(self.standard_mode)
        except Exception as msg:
            self.logger.error("Error stopping control script: %s" % msg)

    def _demo(self):
        """
        Execute demo sequence
        1. Send "Start" to 192.168.2.41:50000
        2. Turn on PDU 1 (Main experiment lights)
        3. Start "LightServer.py" (if not running)

        :return: None
        """
        self.logger.info("Received demo command, executing demo sequence")
        try:
            try:
                self.logger.info("Connecting to relay socket at %s, port %s" %
                                 self.relay_address)
                self.s_relay.connect(self.relay_address)
                self.logger.info("Sending start command to relay")
                self.s_relay.send("start")
                self.s_relay.close()
            except socket.error as se:
                self.logger.error("Error sending message to relay: %s", se)
            self.ls.set_mode(self.demo_mode)
        except Exception as e:
            self.logger.error("Error starting demo script:", e)

#    def raritan_set(self, ch, val):
#        """
#        Set PDU values by port number and status value.
#        val=1 is on, val=2 is off
#        :param ch: port number
#        :param val: status value
#        :return: None
#        """
#        for (errorIndication, errorStatus, errorIndex, varBinds) in setCmd(
#                SnmpEngine(),
#                CommunityData('private'),
#                UdpTransportTarget(('192.168.1.5', 161)),
#                ContextData(),
#                ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.3.1.1.4.'
#                                          + str(ch)), Integer(val)),
#                lookupMib=False):
            # Check for errors and print out results
#            if errorIndication:
#                self.logger.error(errorIndication)
#            elif errorStatus:
#                self.logger.error('%s at %s' % (errorStatus.prettyPrint(),
#                                                errorIndex
#                                                and varBinds[int(errorIndex)-1][0]
#                                                or '?'))
#            else:
#                for name, val in varBinds:
#                    self.logger.debug('%s = %s' % (name.prettyPrint(),
#                                                   val.prettyPrint()))


if __name__ == "__main__":
    logging.config.fileConfig("/home/arunas/Documents/TJU/logging_config.ini")

    tju_control = TJUControl()
    tju_control.start()
    try:
        while 1:
            pass
    except KeyboardInterrupt:
        tju_control.stop()
    except Exception as m:
        print(m)
        tju_control.stop()
