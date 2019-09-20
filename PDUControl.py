from pysnmp.hlapi import *
import time


def raritan_set(ch, val):
    """
    Set PDU values by port number and status value.
    val=1 is on, val=2 is off
    :param ch: port number
    :param val: status value
    :return: None
    """
    for (errorIndication, errorStatus, errorIndex, varBinds) in setCmd(
            SnmpEngine(),
            CommunityData('private'),
            UdpTransportTarget(('192.168.1.5', 161)),
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.3.1.1.4.'
                                      + str(ch)), Integer(val)),
            lookupMib=False):
        # Check for errors and print out results
        if errorIndication:
            print(errorIndication)
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                            errorIndex
                                            and varBinds[int(errorIndex) - 1][0]
                                            or '?'))
        else:
            for name, val in varBinds:
                print('%s = %s' % (name.prettyPrint(),
                                               val.prettyPrint()))


def turn_all_on():
    raritan_set(1, 1)
    raritan_set(2, 1)
    raritan_set(3, 1)
    raritan_set(4, 1)
    raritan_set(5, 1)
    raritan_set(6, 1)
    raritan_set(7, 1)
    raritan_set(8, 1)

def turn_all_off():
    raritan_set(1, 2)
    raritan_set(2, 2)
    raritan_set(3, 2)
    raritan_set(4, 2)
    raritan_set(5, 2)
    raritan_set(6, 2)
    raritan_set(7, 2)
    raritan_set(8, 2)


if __name__ == "__main__":
    turn_all_off()
    time.sleep(10)
    turn_all_on()
