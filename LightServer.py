"""
Author: Arunas Tuzikas, John Rollinson
Description: Manage outputs to the Light
Date: 5/7/2018
"""

import socket
import threading
import multiprocessing
import sys
import api
import logging

if sys.version_info[0] < 3:
    import Queue
else:
    import queue as Queue

# Global constants used by the server
BUFFER_SIZE = 1000


class LightServer(threading.Thread):
    def __init__(self, address=("192.168.2.20", 50000), logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("Initializing light control server")
        super(LightServer, self).__init__(name="LightServer")
        self.msg_queue = Queue.Queue()

        # System modes
        self.standard_mode = 0
        self.experiment_mode = 1
        self.demo_mode = 2

        # API Setup
        api.set_network('192.168.2')  # Select the base network address
        self.logger.info("Performing API IP address discovery")
        self.ip_list = api.discover()
        self.logger.info("Discovered connections: %s" % str(self.ip_list))
        if not self.ip_list:
            self.logger.warning("No luminaires detected")

        # Scan through fixtures to classify each
        self.experiment_fixtures = []
        self.switch_fixtures = []
        self.task_fixtures = []
        for ip in self.ip_list:
            name = api.get_custom_device_name(ip)
            if name.lower().startswith("experiment"):
                self.experiment_fixtures.append(ip)
            elif name.lower().startswith("switch"):
                self.switch_fixtures.append(ip)
            elif name.lower().startswith("task"):
                self.task_fixtures.append(ip)
            else:
                self.logger.warning("Unrecognized fixture name: %s, "
                                    "fixture is assumed to be an experiment light" % name)
                self.experiment_fixtures.append(ip)
        if len(self.experiment_fixtures) == 0:
            self.logger.warning("No experiment fixtures found")
        else:
            self.logger.info("Experiment fixture ip's found: %s" % (self.experiment_fixtures))
        if len(self.switch_fixtures) == 0:
            self.logger.warning("No switch-controlled fixtures found")
        else:
            self.logger.info("Switch fixture ip's found: %s" % (self.switch_fixtures))
        if len(self.task_fixtures) == 0:
            self.logger.warning("No task fixtures found")
        else:
            self.logger.info("Task fixture ip's found: %s" % (self.task_fixtures))

        # Create socket thread to receive packets
        self.packet_server = PacketServer(self.msg_queue, address)
        self.logger.info("Light control server initialized")

    def run(self):
        self.packet_server.start()
        while self.packet_server.isAlive():
            while self.msg_queue.empty() and self.packet_server.isAlive():
                pass
            try:
                data = self.msg_queue.get(block=False)
                dataS = data.strip().split()
                self.logger.info("Received packet: %s" % str(dataS))
                if dataS[0] == 'SetRawAll':
                    SendToLight = self.ConvertRaw(data)
                    self.logger.debug(SendToLight)
                    if SendToLight > 0:
                        self.logger.debug("Sending command to light fixture")
                        response = api.sendMessageParallel(self.ip_list,
                                                           SendToLight,
                                                           tries=5,
                                                           timeout=1.0)
                        self.logger.debug("Response from light fixture %s" % str(response))
                    else:
                        self.logger.error('%s\n' % str(SendToLight))
                elif dataS[0] == 'SetRawIp':
                    SendToLight = self.ConvertRawIp(data)
                    self.logger.debug(SendToLight)
                    if SendToLight > 0:
                        fix_number = int(SendToLight[0])
                        if fix_number < len(self.ip_list):
                            del SendToLight[0]
                            self.logger.debug(self.ip_list[fix_number])
                            api.set_all_drive_levels(
                                self.ip_list[fix_number],
                                map(float, SendToLight))
                    else:
                        self.logger.error('%s\n' % str(SendToLight))
                else:
                    self.logger.error("Unrecognized command at start of packet")
            except Exception as m:
                self.logger.error("Error trying to get object from message queue: %s" % m)
        self.logger.info("Light server thread ended")

    def stop(self, timeout=None):
        self.logger.info("Stopping light server thread")
        self.packet_server.stop()
        self.join(timeout=timeout)
        self.logger.info("Light server thread terminated")

    def set_mode(self, mode, startup=False):
        if mode == 0:
            self.ip_list = self.task_fixtures + self.switch_fixtures
            self.logger.info("Turning off experiment fixtures")
            msg = self.ConvertRaw("SetRawAll 0 0 0 0 0 0 0 0")
            api.sendMessageParallel(self.experiment_fixtures, msg)
            # for ip in self.experiment_fixtures:
            #     api.set_all_dark(ip)
            if not startup:
                self.logger.info("Turning on main switch controllable lights")
                for ip in self.ip_list:
                    api.player_play_script(ip, api.player_first_script(ip))
        elif mode == 1:
            self.logger.info("Disabling main switch controllable lights and task light")
            self.ip_list = self.task_fixtures + self.experiment_fixtures + self.switch_fixtures
        elif mode == 2:
            self.logger.info("Turning on all fixtures for demo mode")
            self.ip_list = self.task_fixtures + self.experiment_fixtures + self.switch_fixtures

            # Light Channel Settings
            a1 = 10.8
            a2 = 5.54
            a3 = 14.1
            a4 = 10.62
            a5 = 69.75
            a6 = 38.84
            a7 = 9.12
            a8 = 20.02

            # Set all fixtures to the default setting
            msg = self.ConvertRaw("SetRawAll %s %s %s %s %s %s %s %s"
                                  % (a1, a2, a3, a4, a5, a6, a7, a8))
            api.sendMessageParallel(self.ip_list, msg)

            # for ip in self.ip_list:
            #     api.player_play_script(ip, api.player_first_script(ip))

    def ConvertRaw(self, data):
        data = data.strip().split()
        if len(data) >= 9:
            if len(data) > 9:
                self.logger.debug("Multiple messages received at once - using last message")
                data = data[-9:]
                data[0] = "SetRawAll"
            COL = []
            for x in range(1, 9):
                try:
                    if 0 <= float(data[x]) <= 100:
                        COL.append('%04x' % int(float(data[x]) * 655.35))
                    else:
                        self.logger.error('value %d is out of range' % x)
                        return -1
                except:
                    self.logger.error('value %d is not a float' % x)
                    return -2
            SentToLight = 'PS' + COL[0] + COL[1] + COL[2] + COL[3] + COL[4] \
                          + COL[5] + COL[6] + COL[7]
            return SentToLight
        else:
            self.logger.error('wrong amount of arguments, should be 8, received %d' % (
                  len(data) - 1))
            return -3

    def ConvertRawIp(self, data):
        data = data.strip().split()
        if len(data) == 10:
            COL = []
            for x in range(1, 10):
                try:
                    if 0 <= float(data[x]) <= 100:
                        COL.append('%f' % (float(data[x]) / 100))
                    else:
                        self.logger.error('value %d is out of range' % x)
                        return -1
                except:
                    self.logger.error('value %d is not a float' % x)
                    return -2
            COL[0] = data[1]  # Address of fixture
            SentToLight = COL
            return SentToLight
        else:
            self.logger.error('wrong amount of arguments, should be 8, received %d' % (
                  len(data) - 2))
            return -3


class PacketServer(threading.Thread):
    def __init__(self, output_queue, address, logger=None):
        super(PacketServer, self).__init__(name="PacketServer")
        self._stop_event = threading.Event()
        self.logger = logger or logging.getLogger(__name__)
        self.output_queue = output_queue

        # Socket setup
        self.address = address
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.logger.info("Binding to %s, port %s" % address)
            self.s.bind(address)
        except socket.error as msg:
            self.logger.error("Bind failed. %s" % (str(msg.args[1])))
            self.logger.info("Exiting light server thread")
            sys.exit()
        self.logger.info("Socket bind complete")

    def run(self):
        self.logger.info("Running light control server thread")
        self.s.listen(1)
        self.s.settimeout(5)
        while 1:
            if self._stop_event.isSet():
                break
            self.logger.info("Waiting for client")
            client, address = (None, None)
            while not client:
                if self._stop_event.isSet():
                    self.output_queue.clear()
                    break
                try:
                    client, address = self.s.accept()
                    self.logger.info("Accepted client")
                except socket.timeout:
                    pass
            while not self._stop_event.isSet():
                # If the client breaks connection,
                # start accepting more clients
                try:
                    client.settimeout(5)
                    data = ""
                    while not data and not self._stop_event.isSet():
                        try:
                            data = client.recv(BUFFER_SIZE)
                            self.logger.debug("Received packet: %s" % data)
                            if not data:
                                break
                            else:
                                self.output_queue.put_nowait(data)
                        except socket.timeout:
                            pass
                # if the client terminates the connection,
                # go back and wait for another client
                except Exception as m:
                    self.logger.error("Exception receiving packet: %s" % m)
                    break
                if not data:
                    break
        self.logger.info("Closing light server socket connection")
        self.s.close()
        self.logger.info("Socket closed")

    def stop(self):
        self._stop_event.set()
        self.join()


if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging_config.ini")

    ls = LightServer(("192.168.2.20", 50001))
    ls.start()
    try:
        while 1:
            pass
    except KeyboardInterrupt:
        ls.stop()
