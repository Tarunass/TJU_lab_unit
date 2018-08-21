import api
import time

api.set_network('192.168.1')
ip_list = api.discover()
print("API Discovery found the following fixture addresses: %s" % str(ip_list))

#api.sendMessageParallel(ip_list, "PS00000000000000000000000000000000")

for ip in ip_list:
    print("Turning on luminaire at IP %s" % ip)
    api.sendMessage(ip, "PS0FF000FF00FF00FF00FF00FF00FF00FF")
    print("S/N: %s" % api.get_sn(ip).rstrip("\n"))
    old_name = api.get_custom_device_name(ip).rstrip("\n")
    print("Current Name: %s" % old_name)
    option_selected = False
    select = raw_input("Would you like to rename this luminaire? (yes/no):")
    while not option_selected:
        if select.lower().startswith('y'):
            new_name = raw_input("Enter new luminaire name (experiment/switch/task):")
            api.set_custom_device_name(ip, new_name)
            time.sleep(.5)
            print("Luminaire name changed to %s" % new_name)
            option_selected = True
        elif select.lower().startswith('n'):
            option_selected = True
        else:
            select = raw_input("Invalid input. Please select an option (yes/no):")
    print("Turning off luminaire\n")
    api.sendMessage(ip, "PS00000000000000000000000000000000")
