# !/usr/bin/env python
import socket
import sys

TCP_IP = '192.168.2.22'
TCP_PORT = 60000
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((TCP_IP, TCP_PORT))
    # s.send('Stop_control')
    s.send('Stop')
    s.close()

except:
    print("Login failed")
    sys.exit(1)
