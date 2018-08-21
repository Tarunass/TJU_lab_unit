#!/usr/bin/python

import socket
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.connect(('192.168.1.7', 50003))
    s.send('stop_thread')
    time.sleep(15)
except:
    logger.error('DimmerStop could not connect to Dimmer')


