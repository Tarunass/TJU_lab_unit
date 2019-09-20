from __future__ import print_function
import threading
from datetime import datetime, timedelta
import time
import sys
import socket
import logging


class EventScheduler(threading.Thread):
    def __init__(self, event_list_file="spreadsheets/Data.txt",
                 address=("192.168.2.22", 50000),
                 logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("Initializing event scheduler thread")
        super(EventScheduler, self).__init__(name="EventScheduler")
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.light_server_address = address
        self._stop_event = threading.Event()
        self._event_list_file = event_list_file
        self._event_list = None
        self._current_event = None
        self._ce_lock = threading.Lock()
        self._next_event = None
        self._ne_lock = threading.Lock()
        self._event_num = None
        self._en_lock = threading.Lock()
        self.trans_length = 100  # Transition time between two events (seconds)
        self.trans_step = 0.1  # Transition step size (seconds) (min=3s)
        self.logger.info("Lighting event scheduler thread initialized")
	#AT 4/16/2019
	self.connected = False
	#AT ---
    def run(self):
#        self._start_sequence()
	self._event_list = self._parse_event_list()
        if not self._stop_event.isSet():
            for i in range(len(self._event_list)):
                with self._ne_lock:
                    self._next_event = self._event_list[i]
                    exec_time = self._next_event[0]
                while datetime.now() < exec_time:
                    time.sleep(.1)
                    if self._stop_event.isSet():
                        break
                if not self._stop_event.isSet():
                    with self._en_lock:
                        self._event_num = i
                    with self._ne_lock:
                        if i == 0:
                            self._execute_event(self._next_event)
                            with self._ce_lock:
                                self._current_event = self._next_event
                        elif self._next_event[1] != -1:
                            self._transition(self._current_event,
                                             self._next_event)
                            with self._ce_lock:
                                self._current_event = self._next_event
                        else:
                            self.logger.info("End of event list reached")
                            control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            control_conn.connect(("192.168.2.20", 60000))
                            control_conn.send("end")
                            control_conn.close()
                            self._stop_sequence()
                else:
                    break
            self.logger.info("Disconnecting from light server")
            self._conn.close()
        self.logger.info("Lighting event scheduler thread terminated")

    def stop(self):
        self._stop_event.set()
        self._stop_sequence()

    def _start_sequence(self):
        self.logger.info("Starting lighting event scheduler thread")
        # Connect to light server
        self.logger.info("Connecting to light server address %s, port %s" % self.light_server_address)
        try:
            self._conn.connect(self.light_server_address)
        except socket.error as msg:
            self.logger.error("Connection to light server failed. "
                              "Error code: %s, Message: %s"
                              % (str(msg.errno), str(msg.args[1])))
            self.logger.info("Stopping event scheduler thread")
            self.stop()
        #self.logger.info("Parsing event list")
        #self._event_list = self._parse_event_list()
        #if not self._event_list:
        #    self.logger.error("No event list - exiting event scheduler "
        #                      "thread execution")
        #    sys.exit()
        # Insert any additional start-up sequence for event scheduler

    def _stop_sequence(self):
        self.logger.info("Executing stop sequence")
        # Insert any additional stop sequence for event scheduler

    def _execute_event(self, vals):
        #AT 4/16/2019
	self.logger.info("Connecting to light server")
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self.connected = False
	while not self.connected:
	    try:
	        s.connect((self.light_server_address))
		self.connected = True
	    except:
		time.sleep(1)
	#AT ---
        log_str = "Executing event: " + ' '.join(str(v) for v in vals)
        self.logger.info(log_str)
        msg = "SetRawAll {} {} {} {} {} {} {} {}".format(*vals[1:]).encode()
        self.logger.debug(msg)
        try:
            s.send(msg)
        except socket.error as msg:
            self.logger.error(msg)
            if msg.errno == 32:
                self.stop()
	#AT 4/16/2019
	s.close()
	#AT ---
    def _transition(self, start_vals, end_vals):
        # print("current state: ", start_vals)
        # print("next state: ", end_vals)
        n_steps = int(self.trans_length/self.trans_step)
        for i in range(n_steps+1):
            if self._stop_event.isSet():
                break
            t = end_vals[0] + timedelta(seconds=i*self.trans_step)
            setting = [t]
            for a, b in zip(start_vals[1:], end_vals[1:]):
                val = a + i * (b - a) / n_steps
                setting.append(val)
            while datetime.now() < setting[0]:
                pass
            self._execute_event(setting)

    @property
    def current_event(self):
        with self._ce_lock:
            return self._current_event

    @property
    def next_event(self):
        with self._ne_lock:
            return self._next_event

    @property
    def event_num(self):
        with self._en_lock:
            return self._event_num

    def _parse_event_list(self):
        events = []
        try:
            with open(self._event_list_file, "r") as infile:
                n = 0
                for line in infile:
                    line = line.split(' ')
                    if line[-1] != 'X\n':
                        self.logger.error("Error parsing lighting recipe: "
                                          "line %s: Unexpected termination "
                                          "in line %s"
                                          % (n, ' '.join(line)))
                        break
                    elif len(line) != 11:
                        self.logger.error("Error parsing lighting recipe: "
                                          "line %s: Invalid number "
                                          "of parameters in line %s"
                                          % (n, ' '.join(line)))
                        break
                    del line[-1]
                    d = line[0]
                    t = line.pop(1)
                    line[0] = datetime.strptime(d + ' ' + t,
                                                "%Y-%m-%d %H:%M:%S")
                    for i in range(1, len(line)):
                        line[i] = float(line[i])
                    events.append(line)
                    n += 1
            if events[-1][1] != -1:
                self.logger.warning("Warning: no termination line found "
                                    "in lighting sequence file")
            if datetime.now() > events[0][0]:
                self.logger.warning("Execution time of first event in "
                                    "event list is in the past")
            min_td = events[1][0] - events[0][0]
            for i in range(len(events)-1):
                td = events[i+1][0] - events[i][0]
                min_td = min(min_td, td)
            if min_td < timedelta(seconds=self.trans_length):
                self.logger.warning("Smallest time step of event list is less "
                                    "than the transition time between "
                                    "two events")
            self.logger.info("Successfully parsed event list")
            return events
        except Exception as msg:
            self.logger.error("Unable to parse event list file: %s" % msg)
            return None


def generate_test_file(filename, n):
    start_time = datetime.now() + timedelta(seconds=5)
    with open(filename, "w") as outfile:
        i = 0
        for i in range(n):
            t = start_time + timedelta(seconds=20 * i)
            line = [t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")]
            for j in range(8):
                line.append(str(2*i))
            line.append('X')
            outfile.write(' '.join(line)+'\n')
        t = start_time + timedelta(seconds=20 * (i+1))
        line = [t.strftime("%Y-%m-%d"), t.strftime("%H:%M:%S")]
        for j in range(8):
            line.append(str(-1))
        line.append('X')
        outfile.write(' '.join(line) + '\n')


if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("logging_config.ini")

    el = 'test_data.txt'
#    generate_test_file(el, 5)
    es = EventScheduler(el, address=("192.168.2.20", 50001))
    es.start()

    try:
        while es.is_alive():
            pass
    except Exception as e:
        print("Event scheduler exception:", e)
        es.stop()
        sys.exit()
