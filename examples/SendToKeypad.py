import getpass
import sys
import telnetlib

HOST = "192.168.1.6"

user = "admin"
password = "LESA2018"

tn=telnetlib.Telnet(HOST, "23")
tn.write(user + "\n")
tn.write(password + "\n")
tn.write("LEDREDS 99\n")
#tn.write("LEDBLUE 1 10\n")
tn.write("KEY_PRESS 8 HOLD\n")

#tn.read_all()
