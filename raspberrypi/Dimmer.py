from subprocess import Popen, PIPE
import multiprocessing
import commands
import time
import socket
import sys
import threading
import logging

TCP_IP_U = '192.168.1.7'
TCP_PORT_U = 50003

TCP_IP = '192.168.1.3'
TCP_PORT = 50000
BUFFER_SIZE = 1000

status = threading.Event()
status.set()


class Server(multiprocessing.Process):
    def __init__(self):
        super(Server, self).__init__(name="Server")
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()

    def run(self):
        global status
        while not self._stop_event.isSet():
            u = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                u.bind((TCP_IP_U, TCP_PORT_U))
            except socket.error as msg:
                self.logger.error("Bind failed. Error code: " + str(msg.errno)
                      + " Message: " + msg.strerror)
                sys.exit()
            self.logger.info("Socket bind complete")
            u.listen(1)
            while not self._stop_event.isSet():
                self.logger.info("Waiting for client")
                u.settimeout(5)
                client, address = None, None
                while not client and not self._stop_event.isSet():
                    try:
                        (client, address) = u.accept()
                        self.logger.info("Accepted client")
                    except socket.timeout:
                        pass
                while not self._stop_event.isSet():
                    # If the client breaks connection,
                    # start accepting more clients
                    client.settimeout(5)
                    data = None
                    while not data and not self._stop_event.isSet():
                        try:
                            data = client.recv(BUFFER_SIZE)
                            # If the client terminates the connection,
                            # go back and wait for another client
                            if not data:
                                break
                        except socket.timeout:
                            pass
                        except socket.error as msg:
                            self.logger.error(msg)
                    if not data:
                        break
                    data_s = data.strip().split()
                    self.logger.debug(data_s)
                    if data_s[0].lower() == 'stop':
                        status.set()
                        p = Popen(['iono', 'o1', 'open'], stdout=PIPE,
                                  stderr=PIPE)
                        self.logger.info(status)
                    elif data_s[0].lower() == 'start':
                        status.clear()
                        p = Popen(['iono', 'o1', 'close'], stdout=PIPE,
                                  stderr=PIPE)
                        self.logger.info(status)
                    elif data_s[0].lower() == 'stop_thread':
                        self.stop()
            u.close()

    def stop(self):
        self._stop_event.set()


class Analog(multiprocessing.Process):
    def __init__(self):
        super(Analog, self).__init__(name="Analog")
        self._stop_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        self.connected = False

        a1 = 10.8
        a2 = 5.54
        a3 = 14.1
        a4 = 10.62
        a5 = 69.75
        a6 = 38.84
        a7 = 9.12
        a8 = 20.02

        self.param = [0.0] * 8
        self.param[0] = a1
        self.param[1] = a2
        self.param[2] = a3
        self.param[3] = a4
        self.param[4] = a5
        self.param[5] = a6
        self.param[6] = a7
        self.param[7] = a8

    def run(self):
        global status
        res_old = -1
        while not self._stop_event.isSet():
            #    print (STATUS)
            if status.isSet():
                try:
                    self.logger.debug("Executing: iono ai1")
                    stdout = commands.getoutput('iono ai1')
                    res = float(stdout)
                    self.logger.debug(res)
                    if (res - res_old) * (res - res_old) > 0.01:
                        if res < 0.5:
                            res = 0.0
                        pa_to_li = [str(i * res / 10) for i in self.param]
                        self.logger.info("Voltage: %2.2f" % res)
                        msg = 'SetRawIp 0 ' + ' '.join(pa_to_li)

                        self.logger.debug(msg)
                        res_old = res
                        self.logger.debug("Creating socket")
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.connected = False
                        while not self.connected:
                            try:
                                self.logger.debug("Connecting to socket")
                                s.connect((TCP_IP, TCP_PORT))
                                self.connected = True
                            except:
                                time.sleep(5)
                        self.logger.debug("Sending msg: %s" % msg)
                        s.send(msg)
                        self.logger.debug("Closing socket")
                        s.close()
                        self.logger.debug("Socket closed")
                except ValueError:
                    self.logger.error("ADC not responding")
            time.sleep(0.05)

    def stop(self):
        self._stop_event.set()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting relay server")
    server = Server()
    logger.info("Listening on analog port")
    analog = Analog()
    server.start()
    analog.start()
    try:
        while True:
            pass
    except:
        analog.stop()
        server.stop()
