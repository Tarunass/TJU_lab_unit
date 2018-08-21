import Dimmer

print("Starting dimmer server")
server = Dimmer.Server()
server.start()
print("Starting analog listening")
analog = Dimmer.Analog()
analog.start()

try:
    while True:
        pass
except:
    print("Stopping dimmer server")
    analog.stop()
    server.stop()
