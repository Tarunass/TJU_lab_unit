# !/usr/bin/env python
import socket
import sys
import time

TCP_IP = '192.168.2.20'
TCP_PORT = 60000
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((TCP_IP, TCP_PORT))
    s.send('Stop_control')
    s.close()
    time.sleep(15)

except:
    print("Login failed")
    sys.exit(1)
