# !/usr/bin/env python
import socket
import sys

TCP_IP = '192.168.2.20'
# TCP_IP = "localhost"
TCP_PORT = 60000
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((TCP_IP, TCP_PORT))
    s.send('Start')
    s.close()

except:
    print("Login failed")
    sys.exit(1)
