import socket

HOST = '192.168.1.3'
PORT = 51000

keypad_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
keypad_sock.bind((HOST, PORT))
keypad_sock.listen(1)
print("Listening on port %s:%s" % (HOST, PORT))

while True:
    print("Waiting for client")
    client = keypad_sock.accept()
    print("Client received %s:%s" % client)
    try:
        while True:
            data = client.recv(1024)
            if not data:
                break
            else:
                print(data)
    except Exception as e:
        print(e)
