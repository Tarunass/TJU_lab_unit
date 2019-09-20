'''
Author: Arunas Tuzikas
Decription: Manage outputs to the Light
Date: 5/7/2018
'''

import socket
import threading
import sys
import time
import api

from pysnmp.hlapi import *

# Global constants used by the server
TCP_IP = '192.168.1.3'
TCP_SERVER_PORT = 50000
BUFFER_SIZE = 1000

api.set_network('192.168.1')  # Select the base network address


def Raritanset(ch, val):
    for (errorIndication, errorStatus, errorIndex, varBinds) in setCmd(
            SnmpEngine(),
            CommunityData('private'),
            UdpTransportTarget(('192.168.1.5', 161)),
            ContextData(),
            ObjectType(
                ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.3.1.1.4.' + str(ch)),
                Integer(val)),
            lookupMib=False):
        # Check for errors and print out results
        if errorIndication:
            print (errorIndication)
        elif errorStatus:
            print ('%s at %s' % (errorStatus.prettyPrint(),
                                 errorIndex and varBinds[int(errorIndex) - 1][
                                     0] or '?'))
        else:
            for name, val in varBinds:
                print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))


def ConvertRaw(data):
    data = data.strip().split()
    if len(data) == 9:
        COL = []
        for x in range(1, 9):
            try:
                if float(data[x]) >= 0 and float(data[x]) <= 100:
                    COL.append('%04x' % int(float(data[x]) * 655.35))
                else:
                    print ('value %d is out of range' % x)
                    return -1
                    break
            except:
                print ('value %d is not a float' % x)
                return -2
                break
        SentToLight = 'PS' + COL[0] + COL[1] + COL[2] + COL[3] + COL[4] + COL[
            5] + COL[6] + COL[7]
        return SentToLight
    else:
        print('wrong amount of arguments, should be 8, received %d' % (
        len(data) - 1))
        return -3


def ConvertRawIp(data):
    data = data.strip().split()
    if len(data) == 10:
        COL = []
        for x in range(1, 10):
            try:
                if float(data[x]) >= 0 and float(data[x]) <= 100:
                    COL.append('%f' % (float(data[x]) / 100))
                else:
                    print ('value %d is out of range' % x)
                    return -1
                    break
            except:
                print ('value %d is not a float' % x)
                return -2
                break
        COL[0] = data[1]  # Address of fixture
        SentToLight = COL
        return SentToLight
    else:
        print('wrong amount of arguments, should be 8, received %d' % (
        len(data) - 2))
        return -3


def main():
    print ("Running Light Controll Server")
    # Discovery is mandatory.  It will return a list of all the IP addresses
    # associated with luminaires connected to your network
    Raritanset(1, 1)
    Raritanset(2, 1)
    Raritanset(3, 1)
    Raritanset(4, 1)
    Raritanset(5, 1)
    Raritanset(6, 1)
    Raritanset(7, 1)
    Raritanset(8, 1)

    time.sleep(10)
    print("Starting api ip discovery")
    ip_list = api.discover()
    print("API discovery finished")
    ip_list = ['192.168.1.46', '192.168.1.47', '192.168.1.48', '192.168.1.49']

    while 1:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((TCP_IP, TCP_SERVER_PORT))
        except socket.error as msg:
            print(
            "Bind failed. Error conde: " + str(msg[0]) + " Message: " + msg[1])
            sys.exit()
        print ("Socket bind complete")
        s.listen(1)
        while 1:
            print("Waiting for client")
            (client, address) = s.accept()
            print ("Accepted client")
            while 1:
                # If the client breake connection, star accepting more clients
                try:
                    data = client.recv(BUFFER_SIZE)
                # if the client terminates the connection, goback and wait for another client
                except:
                    break
                if not data:
                    break

                dataS = data.strip().split()
                print(dataS)
                if dataS[0] == 'SetRawAll':
                    SendToLight = ConvertRaw(data)
                    print SendToLight
                    if SendToLight > 0:
                        print api.sendMessageParallel(ip_list, SendToLight,
                                                      tries=5, timeout=1.0)
                        client.send('0\n')
                    else:
                        client.send('%s\n' % str(SendToLight))

                if dataS[0] == 'SetRawIp':
                    SendToLight = ConvertRawIp(data)
                    print SendToLight
                    if SendToLight > 0:
                        Fix_number = int(SendToLight[0])
                        if Fix_number < len(ip_list):
                            del SendToLight[0]
                            print ip_list[Fix_number]
                            api.set_all_drive_levels(ip_list[Fix_number],
                                                     map(float, SendToLight))
                            client.send('0\n')
                        client.send('testas\n')
                    else:
                        client.send('%s\n' % str(SendToLight))


if __name__ == '__main__':
    main()
