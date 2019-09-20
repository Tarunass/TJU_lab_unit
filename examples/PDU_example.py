from pysnmp.hlapi import *

def Raritanset(ch, val):
    for (errorIndication, errorStatus, errorIndex, varBinds) in  setCmd(
			SnmpEngine(),
			CommunityData('private'),
			UdpTransportTarget(('192.168.1.5', 161)),
			ContextData(),
			ObjectType(ObjectIdentity('1.3.6.1.4.1.318.1.1.12.3.3.1.1.4.' + str(ch)), Integer(val)),
			lookupMib=False):
	# Check for errors and print out results
	if errorIndication:
		print (erroIndication)
	elif errorStatus:
		print ('%s at %s' % (errorStatus.prettyPrint(),
			errorIndex and varBinds[int(erroIndex)-1][0] or '?'))
	else:
		for name, val in varBinds:
			print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))

def main():
#First value is a port number, second - status 1 is on, 2 is off
	Raritanset(8, 1)

if __name__ == '__main__':
	main()
