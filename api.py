#########################################################
#                                                       #
#                      api.py                           #
#                                                       #
# (c) 2014 Telelumen LLC.  All rights reserved.         #
#                                                       #
# v1.00 - 15 January 2014   Initial version  rda        #
# v1.10 - 11 October 2016   Clean up a bit; add new fns #
#         from Dima's viewer program                    #
# v1.20 - 2 Feb 2017        Add file send & receive,    #
#                           Firmware upgrade.  Still    #
#                           a long way from finished    #
# v1.30 - 21 March 2017     Restructure discovery       #
#                           Now discover is two-pass:   #
#                           First pass kills existing   #
#                           connections; second pass    #
#                           establishes new connections #
#                                                       #
# v1.31  23 June 2017       Add exception handling      #
# v1.32  26 Sept 2017       Minor tweaks to ID for LR   #
# v1.33  27 Sept 2017       Start to object-orientify   #
# v1.34   5 Oct 2017        Remove all sorts of debug-  #
#                           ging prints                 #
#                                                       #
# v1.40  22 March 2018      Add load-and-pause          #
# v2.00  28 Sept 2017       Grow into a more mature API #
# v2.01  27 Dec 2017        Add UDP message I/O         #
# v2.10  27 March 2018      Remove dependency on        #
#                           netifaces                   #
# v2.11  29 March 2018      Add sendMessageParallel     #
#                           sendMessageParallelRetry    #
#                           and use for "simultinaity"  #
#                                                       #
# v2.12  8 May 2018         Minor debug message removal #
#                                                       #
##########################################################

import sys
import os
import threading
import telnetlib
import socket
import subprocess
import time
import datetime
import logging
import array as array
import json
import binascii
import copy
import time
import re
from datetime import datetime as dt

network_candidate_list = ['192.168.1.', '192.168.0.', '192.168.1.', '192.168.2.', '192.168.11.']
luminairePort = 57007
disconnectRequestPort = 57011

telnetObj = {}  # dictionary correlating ip address to socket
refused_list = []
# Set Luminaire Network to a class C network prefix on which the luminaires
# reside.  This will usually be the same network as the wireless router.
luminaireNetwork = '0.0.0.'
# The port number is fixed by the Luminaire firmware.  It can be changed
# by configuration message, but this is not recommended as it will break
# backward compatibility with older applications.

socket_list = {} # dictionary correlating ip address to socket
sendTask = [0 for i in range (0,256)]


def get_timestamp():
    try:
        ts = time.time()
        tss = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')+':'
        return tss
    except:
        return ""

################## Basic Communications I/O ##################
def log_error(errtag):
    try:
        logging.error(get_timestamp()+errtag+":"+str(sys.exc_info()[0]))
    except:
        pass

def log_info(infotag):
    try:
        logging.info(get_timestamp()+infotag)
    except:
        pass

def log_warn(warntag):
    try:
        logging.warn(get_timestamp()+warntag)
    except:
        pass

TELNET_CONNECTION_TIMEOUT = 2.0
# Create a telnet connection with the device at the specified address & port
def openConnection(ip, portno):
    try:
        tn = None
        tn = telnetlib.Telnet(ip, portno, TELNET_CONNECTION_TIMEOUT)
        log_str = 'OK: openConnection(%s): returns %s' % (ip, str(tn))
        log_info(log_str)
        telnetObj[ip] = tn  # Remember our associated telnet object
        return 0    # Connection OK
    except socket.error, exc:
        if 'Connection refused' in str(exc):
            log_debug('FAIL:CONNECTION REFUSED %s!' % ip)
            refused_list.append(ip)
        log_str = 'FAIL: openConnection(%s):%s' % (ip, str(exc))
        log_debug(log_str)

    except:
        return -1  # Connection failed 
    return -1  # Connection failed

# Open a luminaire at the legacy port # 57007
def openLuminaire(ip, port):
    try:
        rv = openConnection(ip, port)
        return rv
    except:
        return -1

# Close the luminaire at the specified full IP address
def closeLuminaire(ip):
    global telnetObj
    global socket_list
    global sendTask
    global luminaire_list
    global luminaireTask

    try:
        telnetobj = telnetObj[ip]
        telnetobj.close()
        telnetObj.clear()
        socket_list.clear()
        sendTask = [0 for i in range(0,256)]
        luminaireNetwork = '0.0.0.'
        luminaire_list = []
        luminaireTask = [0 for i in range (0,256)]
        return 0
    except:
        return -1

# Given a list of luminaire full IP addresses, close all of them
def closeList(hostlist):
    try:
        for host_ip in hostlist:
            closeLuminaire(host_ip)
    except:
        pass

# Get a standard luminaire reply, which always ends in (and does not otherwise
# contain) a semicolon:
def getReply(ip):
    try:
        telnetobj = telnetObj[ip]
        reply = telnetobj.read_until(';')
        info_tag = 'getReply(ip=%s): %s' % (ip, reply)
        log_info(info_tag)
        return reply
    except:
        try:
            errtag = 'getReply(ip=%s) exception' % (ip)
            log_error(errtag)
            return ""
        except:
            return ""

# Get a standard luminaire reply, which always ends in (and does not otherwise
# contain) a semicolon:
def getReplyWithTimeout(ip, timeout):
    try:
        telnetobj = telnetObj[ip]
        reply = telnetobj.read_until(';', timeout)
        info_tag = 'getReply(ip=%s): %s' % (ip, reply)
        log_info(info_tag)
        return reply
    except:
        try:
            errtag = 'getReply(ip=%s) exception' % (ip)
            log_error(errtag)
            return ""
        except:
            return ""


# Just send a message.  Don't wait for a reply. Don't get a reply.
# You can pair this with getReply() to get the equivalent of sendMessage()
def sendMessageRaw(ip, outMsg):
    try:
        telnetobj = telnetObj[ip]
        telnetobj.write(outMsg+'\r')
        info_tag = 'sendMessageRaw(%s): %s' % (ip, outMsg)
        log_info(info_tag)
        return 0
    except:
        try:
            errtag = 'sendMessageRaw(ip=%s,msg=%s)' % (ip, outMsg)
            log_error(errtag)
            return -1
        except:
            return -1

# Send a message and wait for and return the reply from the luminaire
def sendMessage(ip, outMsg):
    try:
        info_tag = 'sendMessage(%s): %s' % (ip, outMsg)
        log_info(info_tag)
        sendMessageRaw(ip, outMsg)
        return getReply(ip)
    except:
        "" 

# Send a message with the specified number of retries before failing.
def sendMessageRetries(ip, retries, outMsg):
    try:
        info_tag = 'sendMessageRetries(%s:%d): %s' % (ip, retries, outMsg)
        log_info(info_tag)

        for count in range(0, retries):
            if (count > 0):
                info_tag = 'Retry #%d' % (count)
                log_info(info_tag)
            result = sendMessage(ip, outMsg)
            if (result):
                return result
        errtag = 'sendMessageRetries(ip=%s, retries=%s, msg=%s)' % (ip, str(retries), outMsg)
        log_error(errtag)
        return ""
    except:
        return ""

# Note that due to possible stateful sequences of messages, and unexpected
# side-effects of mindlessly repeating a command without considering context,
# this function only retries a command until SOME response is returned.
# If the luminaires are in different states, it might be "normal" to have
# some "complain" with an error code but not others, and retrying a failure
# with no context or knowledge of state in a general function is not wise,
# so we concentrate on making sure the message is delivered and responded to,
# and let higher-level logic decide if further action is required on units that
# respond but return a non-zero (error) return value.
def sendMessageParallel(hostip_list, outmsg, tries=3, timeout=2.0):
    #####################################################################################
    # can accept list of messages, one per luminaire, or one message to be sent to all
    #
    if isinstance(hostip_list, str):
        hostip_list = [ hostip_list ]

    if isinstance(outmsg, str):
        outmsg = [ outmsg ] * len(hostip_list)
    else:
        assert len(outmsg) == len(hostip_list)
    host_msg_dic = dict(zip(hostip_list, outmsg))
    #
    #####################################################################################

    if isinstance(hostip_list, list) == False:
        return -1, [], [] # Garbage in, garbage out.  Must be a list
    
    try_count = 0
    cmdreply_dict = dict(zip(hostip_list, ['' for i in range(0,len(hostip_list))]))
    worklist = [k for k in cmdreply_dict.keys() if ';' not in cmdreply_dict[k]]
    
    while try_count < tries and len(worklist) > 0:
        try_count = try_count + 1
        infotag = 'Try #:%d addresses=%s' % (try_count, worklist)
        log_info(infotag)
        # Make a list of all luminaires that haven't yet responded in worklist
        try:
            for ip in worklist:
                sendMessageRaw(ip, host_msg_dic[ip])
        except:
            errtag = 'sendMessageParallel(ips=%s,msg=%s,tries=%d,timeout=%f):%s' % \
                     (str(worklist), outmsg, tries, timeout, sys.exc_info()[0])
            log_error(errtag)

        giveup_time = time.time() + timeout
        # Accumulate reponses for the required time
        while time.time() < giveup_time:
            try:
                for ip in worklist:
                    telnetobj = telnetObj[ip]
                    reply = ''
                    try:
                        reply = telnetobj.read_eager()
                        if reply != '':
                            cmdreply_dict[ip] = cmdreply_dict[ip] + reply
                    except:
                        pass
            except:
                errtag = 'sendMessageParallel(ips=%s,msg=%s,tries=%d,timeout=%f):%s' % \
                     (str(worklist), outmsg, tries, timeout, sys.exc_info()[0])
                log_error(errtag)
                print(hostip_list)
                print(cmdreply_dict)

                print(telnetObj)

            worklist = [k for k in cmdreply_dict.keys() if ';' not in cmdreply_dict[k]]
            for ip in hostip_list:
                if ';' not in cmdreply_dict[ip]:
                    cmdreply_dict[ip] = ''

            if len(worklist) == 0:
                break

    return worklist, [(addr, cmdreply_dict[addr]) for addr in hostip_list]


########################################
# Basic luminaire functionality access #
########################################

# Send a command.  Return the reply as a string
# or False if there was an error or no reply
def ll_command_reply(ip, cmd):
    try:
        res = sendMessageRetries(ip, 3, cmd)
        if "00;" not in res:
            return False
        return res
    except:
        return False

# Send a command. Return 0 if it was successful, 
# -1 otherwise
def ll_command(ip, cmd):
    try:
        res = sendMessageRetries(ip, 3, cmd)
        if "00;" not in res:
            return -1
        return 0
    except:
        return -1	# Exception exit

def get_pwm_vector_string(ip):
    drive_levels = []
    try:
        res = ll_command_reply(ip, "PS?")
        # FIXME: This is too tied to the particular format and best to do
        # something more sophisticated. This is a time-to-delivery KLUDGE
        try:
            str1 = res.split('\r')
            str2 = str1[1].split('\r')
            return str2[0]
        except:
            return []
    except:
        return []


# Script Player functions:
def play_octa(ip, scriptname, wait_to_play=False):
    try:
        if (len(scriptname) == 0):
            cmd = 'PLAY\r\n'
        else:
            if (wait_to_play):
                cmd = 'PLAYPAUSED ' + str(scriptname) + '\r\n'
            else:
                cmd = 'PLAY ' + str(scriptname) + '\r\n'
        
        return ll_command(ip, cmd)
    except:
        return -1
            
def play_lr(ip, scriptname):
    try:
        cmd = 'SETPAT=' + str(scriptname) + '\r\n'
        return ll_command(ip, cmd)
    except:
        return -1

def pause_octa(ip):
    try:
        return ll_command(ip, 'PAUSE')
    except:
        return -1

def pause_lr(ip):
    try:
        return ll_command(ip, 'Q5')
    except:
        return -1

def resume_octa(ip):
    try:
        return ll_command(ip, 'RESUME')
    except:
        return -1

def resume_lr(ip):
    try:
        return ll_command(ip, 'Q2')
    except:
        return -1


def stop_octa(ip):
    try:
        return ll_command(ip, 'STOP')
    except:
        return -1

def stop_lr(ip):
    ret = -1
    try:
        ret = ll_command(ip, 'Q8')
        if (ret != -1):
            ll_command(ip, 'B')     # LR doesn't go dark on stop.  Make it consistent
        return ret
    except:
        return -1



def get_current_script(ip):
    try:
        res = ll_command_reply(ip, 'CURRENT')
        if "00;" in res:
            # FIXME: This is too tied to the particular format and best to do
            # something more sophisticated. This is a time-to-delivery KLUDGE
            try:
                str = res.split('\r')
                str2 = str[1].split('\r')
                return str2[0]
            except:
                return False
        return False    # Some error must have occurred
    except:
        return False

def next_script(ip):
    try:
        res = ll_command(ip, 'NEXT')
        return res
    except:
        return -1

def prev_script(ip):
    try:
        res = ll_command(ip, 'PREV')
        return res
    except:
        return -1

def get_serial_number(ip):
    try:
        res = ll_command_reply(ip, 'NS')
        return res
    except:
        return False
    
# File stuff
def legacy_get_directory(ip):
    try:
        res = ll_command_reply(ip, 'DIR')
        dirs = []
        if "00;" in res:
            lines = res.split('\r\n')
            for s in lines:
                if len(s.strip()) > 0 and '00;' not in s:
                    # Look for LightReplicator metadata separator tick
                    finfopos = s.find('`')
                    if finfopos > 0:
                        s = s[0:finfopos]   # Strip out LR metadata from line  
                    # Add this line
                    dirs.append(s.strip())
            return dirs
        return False    # Some error must have occurred
    except:
        return False


def legacy_delete(ip, cmd, filename):
    try:
        c = cmd + ' ' + str(filename) + '\r\n'
        return ll_command(ip, c)
    except:
        return -1


def delete_lr(ip, filename):
    return legacy_delete(ip, 'ERASE', filename)

def delete_octa(ip, filename):
    return legacy_delete(ip, 'DELETE', filename)


def format(ip):
    try:
        return ll_command(ip, 'FORMAT')
    except:
        return -1



################## Discovery Stuff ##################

maxDiscoverTime = 0.6
luminaireTask = [0 for i in range (0,256)]
luminaire_list = []

# Return the network part and trailing dot if network may contain Penta/Octa,
# else return None
def is_rfc822_network(net):
    try:
        # Look for a canonical ip address
        aa = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", net)
        if aa:
            ip_candidate = aa.group()
            if (ip_candidate.startswith('192.168.')):
                ab = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.", net)
                ip_net = str(ab.group())
                return ip_net
        return None
    except:
        return None


def find_luminaire_network():
        return network_candidate_list


def addLuminaire(ip):
    try:
        if (ip not in luminaire_list):
            luminaire_list.append(ip)
            luminaire_list.sort()
            msg_tag = "addLuminaire(ip=%s)" % ip
            log_info(msg_tag)
    except:
        return None


def removeLuminaire(ip):
    try:
        if (ip in luminaire_list):
            luminaire_list.remove(ip)
            info_tag = "removing Luminaire(%s)" % (ip)
            log_info(info_tag)
    except:
        return None


def discoveryPoll(address, port):
    try:
        ipAddy = luminaireNetwork + str(address)

        if (openLuminaire(ipAddy, port) == 0):
            try:
                sn = get_serial_number(ipAddy)
                if (sn != False):
                    addLuminaire(ipAddy)
                else:
                    removeLuminaire(ipAddy)
            except:
                removeLuminaire(ipAddy)
        else:
            removeLuminaire(ipAddy)
        return 0
    except:
        return -1

###### discover_all() returns a list of all IP addresses associated with a luminaire.
###### Call this function to find out what luminaires are active on the network.
###### Note that it may take up to a minute after a luminaire is first powered
###### on before it will have successfully connected to the network. 20 seconds
###### is a more typical value.

def is_alive():
    try:
        for i in range(2, 255): # FUBAR - fix the limits
            if (luminaireTask[i].isAlive()):
                return True
        return False
    except:
        return False
            
def discover_one(net, port):
    global luminaireNetwork
    global luminaire_list

    try:
        luminaire_list = []
        refused_list = []
    
        luminaireNetwork = net
        logging.basicConfig(filename='api.log', level=logging.INFO, filemode='w')

        info_tag = 'discover_one(net=%s): Discovering Luminaires on network ' %  luminaireNetwork
        log_info(info_tag)

        log_info('discover_one():create threads!')
        for i in range(2,255):
            nextaddr = luminaireNetwork + str(i)
            luminaireTask[i] = threading.Thread(target=discoveryPoll, args=(i,port),)

        log_info('discover_one():start threads!')
        for i in range(2,255):
            luminaireTask[i].start()

        log_info('discover_one(): isAlive() wait')
    
        while (is_alive()):
            time.sleep(1.0)

        log_info('discover_one(): isAlive() wait completed')
        
        log_info('discover_one(): Join has completed: exiting')
        luminaire_list.sort()
        log_info('discover_one() returns: %s' % str(luminaire_list))
        return luminaire_list
    except:
        return luminaire_list


def discover_all(override_net=None):
    try:
        if (override_net):
            logging.basicConfig(filename='api.log', level=logging.INFO, filemode='w')
            log_info('Attempting discover on ' + override_net + ' only')
            log_info('discover(net=%s' % override_net)
            x = discover_one(override_net, disconnectRequestPort)
            x = discover_one(override_net, luminairePort)
            return x
        else:
            netlist = find_luminaire_network()
            log_info('find_luminaire_network() returns: %s' % str(netlist))
            for nn in netlist:
                logging.basicConfig(filename='api.log', level=logging.INFO, filemode='w')
                lumlist = discover_one(str(nn), disconnectRequestPort)
                lumlist = discover_one(str(nn), luminairePort)
                if lumlist: 
                    return lumlist      # If any luminaire found, return the list
        return []
    except:
        return []

############
# File I/O #
############

def read_script(input_filename):
    script = []

    try:
        n = open(input_filename, 'rb')
        lines = n.read()

        log_info('Opening input filename:%s' % input_filename)
        with open(input_filename, 'rb') as source:
            script = source.read()
            return script
    except:
            return -1


def compute_xor32(dat, lens):
    try:
        if (lens < 512):
            addin = 512-lens
            dat = dat + chr(0)*addin
            lens = 512
    
        xorsum = array.array('L')   # Must be 32 bits
        nextxor = array.array('L')  # Must be 32 bits
        nextxor.append(0)
        xorsum.append(0)            # Start with empty LRC sum
    
        a = array.array('L')
        b = array.array('L')
        c = array.array('L')
        d = array.array('L')

        a.append(0)
        b.append(0)
        c.append(0)
        d.append(0)


        xorsum[0] = 0
        for i in range(0, lens, 4):
            if (i <= (lens - 4)):
                a[0] = ord(dat[i+3])
                b[0] = ord(dat[i+2])
                c[0] = ord(dat[i+1])
                d[0] = ord(dat[i])
            else:
                a[0] = 0 #  /* definitely no index+3 element */ 
                if ((i + 2) < lens): 
                    b[0] = ord(dat[i + 2])
                    c[0] = ord(dat[i + 1])
                    d[0] = ord(dat[i])
                elif ((i + 1) < len):
                    b[0] = 0
                    c[0] = ord(dat[i + 1])
                    d[0] = ord(dat[i])
                else:
                    b[0] = c[0] = 0
                    d[0] = ord(dat[i])
       
            nextxor[0] = (a[0] << 24) | (b[0] << 16) | (c[0] << 8) | d[0]
            xorsum[0] = xorsum[0] ^ nextxor[0]
        return xorsum[0]
    except:
        return 0

def send_block(ip, dat, reliable, lens):
    try:
        if (reliable == True):
            lrc = compute_xor32(dat, lens)
            cmd = 'WRITE %08X:' % lrc
        else:
            cmd = 'WRITE '

        for i in range(0, lens):
            cmd = cmd + '%02X' % ord(dat[i])

        result = sendMessageRetries(ip, 10, cmd)
        return result
    except:
        return ""

def compute_file_lrc(fn):
    try:
        data = read_script(fn)
    except:
        return -1
    try:
        dl = len(data)

        if (dl < 1):
            return -1
        return compute_xor32(data, dl)
    except:
        return -1

# Receive using OPEN/READAT/LRC paradigm used by Penta and Octa,
# future products
def receive_file_octa(ip, luminaire_filename, filesys_filename):
    rxfile = ""
    chksum = ""

    cmd = 'OPEN %s' % luminaire_filename
    result = sendMessageRetries(ip, 10, cmd)
    if '00;' not in result:
        info_tag = "Unable to open file(%s)" % (luminaire_filename)
        log_info(info_tag)
        return -1

    result= '00;'
    index = 0

    while ('01;' not in result):
        file_sum = 1
        lrc = 0
        while (file_sum != lrc):
            cmd = 'READAT %d\r\n' % index
            # Point to the next data block now

            result = sendMessageRetries(ip, 3, cmd)
            if '00;' not in result:
                break

            block_data = result.split()
            nxt = ''
            for b in block_data:
                if b.endswith('00;'):
                    pass
                elif b.startswith('='):
                    chksum = b.split(':')
                else:
                    nxt = nxt + binascii.unhexlify(b)

            lrc_val = compute_xor32(nxt, len(nxt))
            lrc = "%08X" % lrc_val
            file_sum = str(chksum[1])
            if (lrc == file_sum):
                rxfile = rxfile + nxt
                index = index + 512

    try:
        with open(filesys_filename, 'wb') as wf:
            wf.write(rxfile)
    except:
        log_error("cannot write file %s" % filesys_filename)
    return 0

def receive_file(ip, luminaire_filename, filesys_filename):
    rxfile = ""
    chksum = ""

    cmd = 'OPEN %s' % luminaire_filename
    result = sendMessageRetries(ip, 10, cmd)

    if '00;' not in result:
        info_tag = "Unable to open file(%s)" % (luminaire_filename)
        log_info(info_tag)
        return -1

    result= '00;'
    index = 0

    while ('01;' not in result):
        file_sum = 1
        lrc = 0
        while (file_sum != lrc):
            cmd = 'READAT %d\r\n' % index
            # Point to the next data block now

            result = sendMessageRetries(ip, 3, cmd)
            if '00;' not in result:
                break

            block_data = result.split()
            nxt = ''
            for b in block_data:
                if b.endswith('00;'):
                    pass
                elif b.startswith('='):
                    chksum = b.split(':')
                else:
                    nxt = nxt + binascii.unhexlify(b)

            lrc_val = compute_xor32(nxt, len(nxt))
            lrc = "%08X" % lrc_val
            file_sum = str(chksum[1])
            if lrc == file_sum:
                rxfile = rxfile + nxt
                index = index + 512

    try:
        with open(filesys_filename, 'wb') as wf:
            wf.write(rxfile)
    except:
        log_error("cannot write file %s" % filesys_filename)

    return 0

# Legacy Light Replicator file receive: OPEN/READ paradigm
def receive_file_lr(ip, luminaire_filename, filesys_filename):
    rxfile = ''
    cmd = 'OPEN %s' % luminaire_filename
    result = sendMessageRetries(ip, 10, cmd)

    if '00;' not in result:
        info_tag = "Unable to open file(%s)" % (luminaire_filename)
        log_info(info_tag)
        return -1

    nxt = ''
    result= '00;'
    while '00;' in result:
        # Point to the next data block now
        cmd = 'READ'
        result = sendMessageRetries(ip, 3, cmd)
        if '00;' in result:
            lines = result.split('\n')
            for s in lines:
                pos = s.find(':')
                if pos > 0:
                    s = s[pos+1:-1].replace(' ', '')
                    nxt = nxt + binascii.unhexlify(s)

    try:
        with open(filesys_filename, 'wb') as wf:
            wf.write(nxt)
    except:
        log_error("cannot write file %s" % filesys_filename)

    return 0


# Send file at inpath to Penta at ip address ip, using
# filename outfn.  Optionally, use LRC redundancy code to ensure reliable receipt.
# Light Replicator does not support LRC, so be sure to set reliable to False.
def legacy_send_file_lrc(ip, inpath, outfn, reliable=True, wait=True):
    try:
        data = read_script(inpath)
    except:
        return -1

    if (isinstance(data, int)):
        return -1
    
    actual_file_length = len(data)
    
    if (actual_file_length < 1):
        return -1
    
    leftover = actual_file_length % 512
    if (leftover > 0):
        block_file_length = actual_file_length + (512 - leftover)
        data = data + chr(0)*(512-leftover)
    else:
        block_file_length = actual_file_length
    
    cmd = 'CREATE '
    cmd = cmd + outfn + '\r\n'

    try:
        result = sendMessage(ip, cmd)
    except:
        return -1

    if ('00;' not in result):
        return -1

    block_count = 0
    bytes_left = block_file_length
    sent_bytes = 0
    size = 0

    while (bytes_left > 0):
        if (bytes_left > 512):
            size = 512
        else:
            size = bytes_left
        
        while True:
            res = send_block(ip, data[512*block_count:512*block_count+size], reliable, size)
            
            if (res == ""):
                pass

            if ('42;' in res) and (bytes_left >= 512):
                pass
            else:
                break

        bytes_left = bytes_left - size
        sent_bytes = sent_bytes + size
        block_count = block_count + 1

    filelen = '%08x' % actual_file_length
    if (wait == True):
        cmd = 'CLOSEPAUSED,'
    else:
        cmd = 'CLOSE,'

    cmd = cmd + filelen + '\r\n'
    
    try:
        result = sendMessageRetries(ip, 10, cmd)
        return 0
    except:
        return -1


def send_file_unreliable(ip, inpath, outfn):
    return send_file_lrc(ip, inpath, outfn, False, False)

def upgrade_one_raw_nosafety (ip, fpn):
    fixed_target_name = 'Penta.bin'
    send_retries = 10
    sendMessage(ip, 'PS00000000000000000000000000007FFF')
    # Read the specified file
    print 'Upgrading luminaire at %s' % ip
    lrc = compute_file_lrc(fpn)
    res = -1
    retries = 0
    while (res != 0) and (retries < send_retries):
        retries = retries + 1
        print 'Sending the binary image %s as %s' % (fpn, fixed_target_name)
        res = legacy_send_file_lrc(ip, fpn, fixed_target_name, True, False)
    sendMessage(ip, 'PS00000000000000000000000000007FFF')
    time.sleep(1.0)
    upgrade_str = "upgrade %08X" % lrc
    print upgrade_str
    sendMessageRaw(ip, upgrade_str)
    sendMessageRaw(ip, upgrade_str)
    return 0

def is_not_version (ip_list, versubstr):
    not_list_list = []
    for ip in ip_list:
        res = sendMessage(ip, "VER")
        if (versubstr not in res):
            not_list_list.append(ip)
            print 'Luminaire at %s: UPGRADE REQUIRED' % ip
        else:
            print 'Luminaire at %s: %s : OK' % (ip, versubstr)
    return not_list_list

def get_image_lrc(ip):
    res = sendMessage(ip, "lrc Penta.bin")
    v = res.split()
    return v[2].replace('LRC:', '')  # FUBAR - this has to be done better when there's 5 seconds more

            
def upgrade_group (ip_list, fpn, versubstr, ver_lrc):
    send_retries = 3
    fixed_target_name = 'Penta.bin'
    upgrade_list = is_not_version(ip_list, versubstr)

    if len(upgrade_list) == 0:
        print 'No upgrade required -- all luminaires have the current firmware'
        sys.exit(0)
    print 'upgrade_list = %s' % str(upgrade_list)
    for ip in upgrade_list:
        sendMessage(ip, "PS0000")
        sendMessage(ip, "PS0000")
        
    for ip in upgrade_list:
        res = -1
        retries = 0
        while (res != 0) and (retries < send_retries):
            retries = retries + 1
            print 'Luminaire at %s: Sending the binary image %s as %s' % (ip, fpn, fixed_target_name)
            res = legacy_send_file_lrc(ip, fpn, fixed_target_name, True, False)
        if (res == 0):
            print 'Success %s' % ip
            sendMessage(ip, "7FFF")
        else:
            print 'Fail %s' % ip
            sendMessage(ip, "0000000000000000000000000000FFFF")
            del ip
            continue
    
    for ip in upgrade_list:
        lrc = get_image_lrc(ip)
        if lrc in ver_lrc:
            print 'Upgrading %s' % ip
            msg = 'upgrade ' + ver_lrc
            print msg
            sendMessageRaw(ip, msg)
            sendMessageRaw(ip, msg)
        else:
            print 'CRC mismatch at %s: file=%s received %s - no upgrade!' % (ip, lrc, ver_lrc)
        
    if (len(upgrade_list) != 0):
        time.sleep(60.0)
        print 'Now please power cycle the luminaires and re-discover'

    
################################################################################
#
# Added by Dima, Oct 10, 2016
#
################################################################################
def get_device_config():
    with open('device_config.json', mode='r') as fh:
        config = json.load(fh)
    return config

class DeviceError(Exception):
    pass

class Device:

    def __init__(self, ip_address):
        self.ip = ip_address
        self.read_fw_ver()
        self.read_sn()
        self.read_type()
        self.config = get_device_config()[self.lumtype]
        
    def get_type (self):
        try:
            return self.lumtype
        except:
            return ""
    
    def write_to_luminaire(self, cmd):
        retval = sendMessageRetries(self.ip, 3, cmd).replace('\r', ' ').replace('\n', ' ')
        if not retval.endswith('00;'):
            raise DeviceError('send message to %s failed with return value %s' % (self.ip, retval))
        return retval

    def read_fw_ver(self):
        retval = sendMessage(self.ip, 'VER')
        if retval == "":
            raise DeviceError('telnetlib.Telnet object error')
        # if not a communication error, will return a string
        # example retval: '\r\n\r\n431188213936424305D7FF31\r\n00;'
        ret_list = retval.split()
        if ret_list[-1] != '00;':
            raise DeviceError('Unexpected return value: %s' % ret_list[-1])
        self.fw_ver = ' '.join(ret_list[: -1])
        return

    def read_sn(self):
        retval = sendMessage(self.ip, 'NS')
        if retval == "":
            raise DeviceError('telnetlib.Telnet object error')
        # if not a communication error, will return a string
        # example retval: '\r\n\r\n431188213936424305D7FF31\r\n00;'
        ret_list = retval.split()
        if ret_list[-1] != '00;':
            raise DeviceError('Unexpected return value: %s' % ret_list[-1])
        self.serial_number = ret_list[0]
        return

    def read_type(self):
        retval = sendMessage(self.ip, 'ID')
        if retval == "":
            raise DeviceError('telnetlib.Telnet object error')
        # if not a communication error, will return a string
        try:
            # LR does not have an 'ID' command.  This returns power data
            # instead.  Beause it's legacy firmware, we'll deduce it's a
            # Light replicator.  No future product will fail the 'ID' command.
            if 'mV' in retval and 'mA' in retval:
                lumtype = 'LightReplicator'
                self.lumtype = lumtype
                return
            
            lumtype = retval.split('00;')[0].strip().split(': ')[0]
        except:
            raise DeviceError('Cannot read luminaire type; returned: ' % retval)
        self.lumtype = lumtype
        return

    # ************ Begin "legacy functions moved to Device class" block:
    def get_directory(self):
        return legacy_get_directory(self.ip)

    def receive_file(self, luminaire_filename, filesys_filename):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('receive_file(): Unknown device type: cannot receive file from it.')
        if 'LightReplicator' in lumtype:
            ret = receive_file_lr(self.ip, luminaire_filename, filesys_filename)
        else:
            ret = receive_file_octa(self.ip, luminaire_filename, filesys_filename)
            
        return ret
     
    def send_file(self, inpath, outfn, idle_after_load=True):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('send_file: Unknown device type: cannot send file to it.')
            
        if 'LightReplicator' in lumtype:
            lrc = False
        else:
            lrc = True

        return legacy_send_file_lrc(self.ip, inpath, outfn, lrc, idle_after_load)

    def delete(self, filename):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('delete(): Unknown luminaire type: cannot delete file.')
        if 'LightReplicator' in lumtype:
            ret = delete_lr(self.ip, filename)
        else:
            ret = delete_octa(self.ip, filename)
        return ret

    def play(self, filename, wait=False):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('play(): Unknown luminaire type: cannot play file')
        if 'LightReplicator' in lumtype:
            ret = play_lr(self.ip, filename)
        else:
            ret = play_octa(self.ip, filename, wait)
        return ret

    def pause(self):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('pause(): Unknown luminaire type: cannot play file')
        if 'LightReplicator' in lumtype:
            ret = pause_lr(self.ip)
        else:
            ret = pause_octa(self.ip)
        return ret

    def resume(self):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('resume(): Unknown luminaire type: cannot play file')
        if 'LightReplicator' in lumtype:
            ret = resume_lr(self.ip)
        else:
            ret = resume_octa(self.ip)
        return ret

    def stop(self):
        try:
            lumtype = self.lumtype
        except:
            raise DeviceError('stop(): Unknown luminaire type: cannot play file')
        if 'LightReplicator' in lumtype:
            ret = stop_lr(self.ip)
        else:
            ret = stop_octa(self.ip)
        return ret

    def get_pwm_vector(self):
        # TODO: does not work for LR
        return get_all_drive_levels(self.ip)

    # ********** End "legacy functions moved to Device class" block

    # RDA: Directly from ancient lore (algorithm in C# written in 2008 or so)
    def __pwm_am_from_drive_level(self, intensity):
        tol = 1E-4
        try:
            am_bits = int(self.config['Modulation']['AMBits'])
            pwm_bits = int(self.config['Modulation']['PWMBits'])
            am_min = int(self.config['Modulation']['AMMin'])
        except:
            am_bits = 4
            pwm_bits = 16
            am_min = 4
        
        am_max = (2**am_bits) - 1
        pwm_max = (2**pwm_bits) - 1

        fam = float(am_max) * intensity
        iam = int(fam)

        if (fam > iam):
            if ((fam - iam) > tol):
                iam = iam + 1
            if (iam > am_max):
                iam = 63
        elif (iam > fam):
            if ((iam - fam) > tol):
                iam = iam + 1
            if (iam > am_max):
                iam = am_max

        if (iam < am_min):
            iam = am_min

        # 4 <= iam <= 63
        pwm = int(fam*float(pwm_max)/float(iam))
        return pwm, iam

   
    def __send_drive_level_to_troffer(self, channel, level):
        assert level >= 0 and level <= 1.0
        msg = 'P%02d%04X' % (channel, round(level * (2 ** self.config['Modulation']['PWMBits'] - 1)))
        self.write_to_luminaire(msg)
        return


    def __send_drive_levels_to_troffer(self, levels):
        for level in levels:
            assert level >= 0 and level <= 1.0
        msg = 'PS' + ''.join(['%04X' % round(level * (2 ** self.config['Modulation']['PWMBits'] - 1)) for level in levels])
        self.write_to_luminaire(msg)
        return

    def __get_physical_channels(self, channel):
        indices = [i for i,x in enumerate(self.config['Map']) if x==channel]
        return indices

    def __send_drive_level_to_LR(self, channel, level):
        pwm, am = self.__pwm_am_from_drive_level(level)
        phys_channels = self.__get_physical_channels(channel)
        # must be consecutive:
        assert phys_channels == range(phys_channels[0], phys_channels[0] + len(phys_channels))
        for c in range(phys_channels[0], phys_channels[-1] + 1):
            self.write_to_luminaire('PC%02d%04X%02X\r\n' % (c, pwm, am))
        return

    def __send_drive_levels_to_LR(self, channel_levels):
        cmd = 'PA'
        for m in self.config['Map']:
            cmd += '%04X%02X' % self.__pwm_am_from_drive_level(channel_levels[m])
        self.write_to_luminaire(cmd)
        return

    def send_drive_level(self, channel, level):
        if self.lumtype in ['Octa', 'Penta']:
            self.__send_drive_level_to_troffer(channel, level)
            return
        self.__send_drive_level_to_LR(channel, level)
        return

    def send_drive_levels(self, levels):
        if self.lumtype in ['Octa', 'Penta']:
            self.__send_drive_levels_to_troffer(levels)
            return
        self.__send_drive_levels_to_LR(levels)
        return

def send_vectors_to_devices(devices, drive_level_vectors):
    for d in devices:
        assert isinstance(d, Device)
        assert d.lumtype in ['Octa', 'Penta']
    assert len(devices) == len(drive_level_vectors)
    messages = []
    for i in range(len(devices)):
        for level in drive_level_vectors[i]:
            assert level >= 0 and level <= 1.0
        messages.append('PS' + ''.join(['%04X' % round(level * (2 ** devices[i].config['Modulation']['PWMBits'] - 1))
                                        for level in drive_level_vectors[i]]))
    sendMessageParallel([d.ip for d in devices], messages)
    return

#########################################################
# The approved interface for external users begins here #
#########################################################

##########################################################
# Basic network and discovery operations at start of use #
##########################################################

# Define our Class-C network address here.  Three octets, exactly, with or
# without a trailing dot:
# If the supplied address does not fit this pattern, or this function isn't
# called, then the default values are used from network_candidate_list
def set_network (ip_network):
    global network_candidate_list
    if ip_network.endswith('.'):
        ip_network = ip_network[0:-1]
        
    nl = ip_network.split('.')
    lynn = len(nl)
    if lynn == 3:
        network_candidate_list = ['.'.join(nl)+'.']

    return network_candidate_list
    
def discover ():
    return discover_all(None)

#############################
# Basic message function(s) #
#############################
def send_message (ip, msg):
    try:
        sp3 = ""
        res = sendMessage(ip, msg)
        res2 = copy.copy(res)
        status_code = int(res2.split()[-1][0:-1], 16)
        sp2 = res.split('\n')[0:-1]
        for st in sp2:
            if st != '\r':
                sp3 = sp3 + st + '\n'
    except:
        status_code = -1    # Error occured
        sp3 = ''
        
    return status_code, sp3

def generic_message_str_reply (ip, msg):
    rc, rs = send_message(ip, msg)
    if rc >= 0:
        return rs
    else:
        return ""
    
########################################
# Luminaire identity & info. functions #
########################################

def get_sn (ip):
    return generic_message_str_reply(ip, 'NS')

def get_id (ip):
    return generic_message_str_reply(ip, 'ID')

def get_custom_device_name(ip):
    return generic_message_str_reply(ip, 'GETNAME')

def set_custom_device_name(ip, custom_name):
    msg = 'SETNAME %s' % custom_name
    return generic_message_str_reply(ip, msg)

def get_custom_device_serial_number(ip):
    return generic_message_str_reply(ip, 'GETSERNO')

def set_custom_device_serial_number(ip, custom_sn):
    msg = 'SETSERNO %s' % custom_sn
    return generic_message_str_reply(ip, msg)

def get_custom_device_id(ip):
    return generic_message_str_reply(ip, 'GETID')

def set_custom_device_id(ip, custom_id):
    msg = 'SETID %s' % custom_id
    return generic_message_str_reply(ip, msg)

def get_flash_manufacturer_id (ip):
    return generic_message_str_reply(ip, 'FLASH-ID')

def get_ip_status (ip):
    return generic_message_str_reply(ip, 'GETIP')

def get_temperature (ip):
    res = generic_message_str_reply(ip, 'TEMPC')
    for lin in res:
        if 'Temp(C):' in lin:
            outs = lin.split('Temp(C):')
            return float(outs[1])
    return 0


########################################################
# Direct light output manipulation and query functions #
########################################################

def set_all_dark (ip):
    return generic_message_str_reply(ip, 'DARK')

# Feed us a list of integer drive levels from 0 to 65535
def set_all_drive_levels_raw (ip, list_of_sixteen_bit_values):
    try:
        cmd = 'PS'
        for lev in list_of_sixteen_bit_values:
            hex_lev = '{:04X}'.format(lev)
            cmd = cmd + str(hex_lev)
        return generic_message_str_reply(ip, cmd)
    except:
        return ''


def set_all_drive_levels (ip, list_of_floating_point_levels_zero_to_one_point_zero):
    try:
        cmd = 'PS'
        for lev_chan in list_of_floating_point_levels_zero_to_one_point_zero:
            lev = int(lev_chan*65535.0)
            hex_lev = '{:04X}'.format(lev)
            cmd = cmd + str(hex_lev)
        return generic_message_str_reply(ip, cmd)
    except:
        return ''

def get_all_drive_levels_raw (ip):
    try:
        drive_vector = []
        st = generic_message_str_reply(ip, 'PS?')
        rep = st.split(',')

        for ndl in rep:
            drive_vector.append(int(ndl, 16))            
    except:
        drive_vector = []
    return drive_vector

def get_all_drive_levels (ip):
    try:
        drive_vector = []
        dv = get_all_drive_levels_raw(ip)
        if len(dv) < 1:
            return []
        for ndl in dv:
            drive_vector.append(float(ndl)/65535.0)
    except:
        pass
    return drive_vector

# Get the channel map:
def get_led_channel_map (ip):
    channel_map = []
    resp = generic_message_str_reply(ip, 'MAP-GET')
    lin = resp.split()[-1]
    mp = lin.split(',')
    for n in mp:
        channel_map.append(int(n))
        
    return channel_map

# Set channel map.  Do NOT do this unless you fully understand the
# channel map and all the consequences of changing it.
def set_led_channel_map (ip, channel_map):
    if len(channel_map) != 8:
        return ''

    msg = 'MAP-PUT '
    for i in range(0,8):
        phy_chan = channel_map[i]
        msg = msg + str(phy_chan)
        if (i < 7):
            msg = msg + ','
    resp = generic_message_str_reply(ip, msg)
    
    return resp

 
#########################
# File System functions #
#########################

# Get a directory listing of all files on the luminaire
def filesys_get_directory (ip):
    return generic_message_str_reply(ip, 'DIR')

def filesys_send_file (ip, inpath, outfn):
    return legacy_send_file_lrc(ip, inpath, outfn, True, False)

def filesys_receive_file (ip, luminaire_filename, local_filepath):
    receive_file(ip, luminaire_filename, local_filepath)


# Return a boolean value indicating whether the specified file exists on the
# Luminaire.
def filesys_file_exists (ip, filename):
    msg = 'FIND %s' % filename
    rc, rs = send_message(ip, msg)
    
    if rc == 0:
        return True
    return False

def filesys_delete_file (ip, filename):
    msg = 'DELETE %s' % filename
    return generic_message_str_reply(ip, msg)

def filesys_format (ip):
    return generic_message_str_reply(ip, 'FORMAT')

def filesys_get_lrc (ip, filename):
    msg = 'LRC %s' % filename
    resp = generic_message_str_reply(ip, msg)
    lines = resp.split('\n')
    for ln in lines:
        if 'LRC:' in ln:
            return ln.replace('LRC:','')
    return ''

def filesys_get_size (ip, filename):
    msg = 'LRC %s' % filename
    resp = generic_message_str_reply(ip, msg)
    lines = resp.split('\n')
    for ln in lines:
        if 'SIZE:' in ln:
            return ln.replace('SIZE:','')
    return ''


###########################
# Script player functions #
###########################

def get_player_status (ip):
    return generic_message_str_reply(ip, 'STAT')

def get_player_current (ip):
    return generic_message_str_reply(ip, 'CURRENT')

def get_script_frame_position (ip):
    return generic_message_str_reply(ip, 'POS')

def player_play_script (ip, script_name):
    if len(script_name) == 0:
        msg = 'PLAY'  # Version of PLAY that resumes an already-selected script
    else:
        msg = 'PLAY ' + script_name

    return generic_message_str_reply(ip, msg)

def player_seek_script (ip, seek_type, value=0.0):
    if seek_type == 'FRAME':
        cmd = 'SEEK FRAME %d' % int(value)
    elif seek_type == 'PERCENT':
        pct = int(float(value)*100.0)   # 0.00-100.00 --> 0-10,000
        cmd = 'SEEK PERCENT %d' % pct
    elif seek_type == 'TIME':
        cmd = 'SEEK TIME %d' % int(value)
    elif seek_type == 'NOW':
        cmd = 'SEEK NOW'
    else:
        return ''
    return generic_message_str_reply(ip, cmd)

def player_pause_script (ip):
    return generic_message_str_reply(ip, 'PAUSE')

def player_stop_script (ip):
    return generic_message_str_reply(ip, 'STOP')

def player_resume_script (ip):
    return generic_message_str_reply(ip, 'RESUME')

def player_stop_script (ip):
    return generic_message_str_reply(ip, 'STOP')

def player_first_script (ip):
    return generic_message_str_reply(ip, 'FIRST')

def player_last_script (ip):
    return generic_message_str_reply(ip, 'LAST')

def player_next_script (ip):
    return generic_message_str_reply(ip, 'NEXT')

def player_prev_script (ip):
    return generic_message_str_reply(ip, 'PREV')

# Select the power-up script the next time the luminaire powers up.
# Note that if this name is invalid or the script is deleted, the setting
# remains in force until it is overwritten with an empty string "".
# The firmware is smart enough not to play a non-existent script, but a human
# might not be... for example, if you restore a deleted file that happens to be
# named by this command, it will RESUME being the first script.  Something to note
# Also, be aware this function does no sanity checking on the provided script
# name so use a directory command to confirm the specified first script is
# actually present before using.
def player_set_first (ip, script_name):
    msg = 'SETFIRST %s' % script_name
    return generic_message_str_reply(ip, msg)
    
def player_get_first (ip):
    return generic_message_str_reply(ip, 'GETFIRST')


# Determine whether script counts are in milliseconds or timer ticks
def player_get_realtime (ip):
    resp = generic_message_str_reply(ip, 'REALTIME')
    lines = resp.split('\n')
    if 'REALTIME=0' in lines[0]:
        return False
    return True

def player_set_realtime (ip, realtime_bool):
    if (realtime_bool):
        msg = 'REALTIME=1'
    else:
        msg = 'REALTIME=0'
    return generic_message_str_reply(ip, msg)

def player_get_rate (ip):
    resp = generic_message_str_reply(ip, 'RATE ?')
    lines = resp.split('\n')
    for ln in lines:
        if '32 Khz' in ln:
            return 32
        elif '16 Khz' in ln:
            return 16
        elif '8 Khz' in ln:
            return 8
        elif '4 Khz' in ln:
            return 4
        elif '2 Khz' in ln:
            return 2
        elif '1 Khz' in ln:
            return 1

    return 0    # If no valid rate in response, we didn't see a valid setting

# Valid settings are 2, 4, 8, 16, and 32 (Khz)
def player_set_rate (ip, rate):
    if is_instance(rate, int) == False:
        return ""

    cmd = 'RATE 4'
    if rate == 32:
        cmd = 'RATE B'
    elif rate == 16:
        cmd = 'RATE A'
    elif rate == 8:
        cmd = 'RATE 8'
    elif rate == 2:
        cmd = 'RATE 2'

    return generic_message_str_reply(ip, msg)


# Forcibly rebuild the pattern list
def player_sync_script_list (ip):
     return generic_message_str_reply(ip, 'SYNC')   

def get_player_smoothing (ip):
    ret = generic_message_str_reply(ip, 'SMOOTH')
    # TODO: decode the return values
    return ret

def set_player_smoothing (ip, smoothing):
    if smoothing == 'ON' or smoothing == 'on':
        msg = 'SMOOTHING=1'
    elif smoothing == 'ON' or smoothing == 'on':
        msg = 'SMOOTHING=0'
    else:
        msg = 'SMOOTHING=2' # This is the default
        
    return generic_message_str_reply(ip, msg)

# Pass in a dimming multiplier from 0.01% to 100.00% --> 1 to 10000
def player_dim (ip, dim_multiplier):
    dim_number = int(100.0*dim_multiplier)
    if dim_number < 0:
        dim_number = 0
    if dim_number > 10000:
        dim_number = 10000

    msg = 'DIM %d' % dim_number
    return generic_message_str_reply(ip, msg)

#################################################################
# Infrequently-used commands to directly control the luminaires #
#################################################################

# Do an ordinary (soft) reset:
def luminaire_control_soft_reset (ip):
    sendMessageRaw(ip, 'RESET')
    
# Do a forced hard reset of the specified luminaire.
# Be aware that any connections and communications will be permanently disrputed
# Do a new discover()

def luminaire_control_hard_reset (ip):
    sendMessageRaw(ip, 'HARDRESET')

 # Remote keypress from 1 through 14   
def luminaire_control_simulated_ir_remote_key (ip, key):
    if key < 0:
        return ''
    if key > 14:
        return ''

    msg = 'Q'+str(key)
    return generic_message_str_reply(ip, msg)
