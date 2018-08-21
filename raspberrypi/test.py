from subprocess import Popen, PIPE
import time

p = Popen(['iono', 'ai1'], stdout=PIPE, stderr=PIPE)
stdout, stderr = p.communicate()

b = Popen(['iono', 'o1', 'open'], stdout=PIPE, stderr=PIPE)
time.sleep(1)
b = Popen(['iono', 'o1', 'close'], stdout=PIPE, stderr=PIPE)


print float(stdout)
