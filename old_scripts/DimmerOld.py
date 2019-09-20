from subprocess import Popen, PIPE
import time
import socket
import sys
import threading

TCP_IP_U = '192.168.1.7'
TCP_PORT_U = 50003

TCP_IP = '192.168.1.3'
TCP_PORT = 50000
BUFFER_SIZE = 1000
A1 = 32.27
A2 = 0.28
A3 = 7.51
A4 = 39.49
A5 = 61.19
A6 = 100
A7 = 6.67
A8 = 41.72

Param = [None]*8
Param[0] = A1
Param[1] = A2
Param[2] = A3
Param[3] = A4
Param[4] = A5
Param[5] = A6
Param[6] = A7
Param[7] = A8



mgr = multiprocessing.Manager()
ns = mgr.Namespace()
ns.STATUS = "STOP"

class server(threading.Thread):
  def __init__(self):
  while True:
    u = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      u.bind ((TCP_IP_U, TCP_PORT_U))
    except socket.error as msg:
      print ("Bind failed. Error code: " + str(msg[0]) + " Message: " + msg[1])
      sys.exit()
    print ("Socket bind compelete")
    u.listen(1)
    while 1:
      print ("Waiting for client")
      (client, address) = u.accept()
      print ("Accepted client")
      while 1:
      # If the client breake connection, stat accepting more clients
        try:
          data = client.recv(BUFFER_SIZE)
      # If the client terminate the connection, go back and wait for another client
        except:
          break
        if not data:
          break

        dataS = data.strip().split()
        print dataS
        if dataS[0].lower() == 'stop':
          ns.STATUS = 'STOP'
          p = Popen(['iono', 'o1', 'open'], stdout=PIPE, stderr=PIPE)
	  print (ns.STATUS)
        if dataS[0].lower() == 'start':
          ns.STATUS = 'START'
          p = Popen(['iono', 'o1', 'close'], stdout=PIPE, stderr=PIPE)
	  print (ns.STATUS)

def analog():
  res_old = 0
  while True:
#    print (ns.STATUS)
    if ns.STATUS == "STOP":
      try:
        p = Popen(['iono', 'ai1'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        res = float(stdout)
        # print res
        if (res - res_old)*(res-res_old) > 0.01:
          PaToLi = [i * res/10 for i in Param]
          print ("Voltage: %2.1f" % res)
          msg = 'SetRawIp 1 ' + str(PaToLi[0]) + ' ' + str(PaToLi[1]) + ' ' \
    	 + str(PaToLi[2]) + ' ' + str(PaToLi[3]) + ' ' + str(PaToLi[4]) + ' ' \
    	 + str(PaToLi[5]) + ' ' + str(PaToLi[6]) + ' ' + str(PaToLi[7])

          print msg
          res_old = res
          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.connect((TCP_IP, TCP_PORT))
          s.send(msg)
          s.close()
      except ValueError:
        print "ADC not responding"
    time.sleep(0.1)

if __name__ == '__main__':
  p1 = multiprocessing.Process(name = 'p1', target = server)
  p2 = multiprocessing.Process(name = 'p2', target = analog)
  p1.start()
  p2.start()
  p1.join()
  p2.join()
