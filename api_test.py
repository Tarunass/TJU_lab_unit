import time
import api

print("Setting API network")
api.set_network("192.168.2")
print("Discovering luminaire IP's")
ip_list = api.discover()
print("Luminaires found at ip address(es):", ip_list)

# def build_cmd(vector):
#     cmd = "PS"

# for i in range(10):
#     print("Setting light level")
#     start = time.time()
#     for ip in ip_list:
#         response = api.set_all_drive_levels(ip, [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25])
#         print(response)
#     print("%s seconds" % (time.time() - start))
#     time.sleep(1)
#     print("Turning off light")
#     start = time.time()
#     for ip in ip_list:
#         response = api.set_all_drive_levels(ip, [0, 0, 0, 0, 0, 0, 0, 0])
#         print(response)
#     print("%s seconds" % (time.time() - start))
#     time.sleep(1)

for i in range(10):
    print("Setting light level")
    start = time.time()
    response = api.sendMessageParallel(ip_list, "PS00FF00FF00FF00FF00FF00FF00FF00FF", tries=5, timeout=1.0)
    print(response)
    print("%s seconds" % (time.time() - start))
    time.sleep(1)
    print("Turning off light")
    start = time.time()
    response = api.sendMessageParallel(ip_list, "PS00000000000000000000000000000000", tries=5, timeout=1.0)
    print(response)
    print("%s seconds" % (time.time() - start))
    time.sleep(1)
