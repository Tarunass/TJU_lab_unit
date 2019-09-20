import api
import sys
import random
import time
# Setup operations:

api.set_network('192.168.1')    # Select the base network address

# Discovery is mandatory.  It will return a list of all the IP addresses
# associated with luminaires connected to your network
ip_list = api.discover()
#ip_list = []
ip_list = ['192.168.1.46', '192.168.1.47', '192.168.1.48', '192.168.1.49']
print 'Luminaires found at ip address(es):', ip_list[1]

print api.sendMessageParallel(ip_list, 'PS000000000000000000000000000000EE', tries=5, timeout=1.0)
#print api.sendMessageParallel(ip_list, 'PSF000F000F000F000F000F000F0000EEE', tries=5, timeout=1.0)
#print api.sendMessageParallel(['192.168.1.46'], 'PS00000000000000000000000000000000', tries=1, timeout=1.0)
#testas