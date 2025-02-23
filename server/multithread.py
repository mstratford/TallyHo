import socket  # Import socket module
from threading import Thread

import json

HOST = ""  # Everywhere
PORT = 8000  # Port to listen on (non-privileged ports are > 1023)
from time import sleep


def send_message(conn, message):
    print(f"Sending {message}")
    conn.sendall(f"{json.dumps(message)}\n".encode())


def on_new_client(conn, addr):
    print("Got connection from", addr)
    while True:
        for i in range(4):
            message = {
                "MAC": None,  # Send to all
                "CAM_LIVE": i,
                "CAM_PREV": i + 1,
            }
            send_message(conn, message)
            sleep(1)
        message = {
            "MAC": "F0:F5:BD:DF:3E:F8",  # Round Touch screen one
            "SET_CAM": 2,
        }
        send_message(conn, message)
        message = {
            "MAC": "A0:85:E3:47:F5:30",  # Round one
            "SET_CAM": 3,
        }
        send_message(conn, message)
        sleep(1)
        message = {
            "MAC": "A0:85:E3:47:F5:30",  # Round one
            "IDENTIFY": True,
        }
        send_message(conn, message)
        sleep(1)
    conn.close()


s = socket.socket()  # Create a socket object

print("Server started!")
print("Waiting for clients...")

s.bind((HOST, PORT))  # Bind to the port
s.listen(5)  # Now wait for client connection.

threads = []
try:
    while True:
        c, addr = s.accept()  # Establish connection with client.
        threads.append(Thread(target=on_new_client, args=[c, addr]))
        threads[-1].start()

        # Note it's (addr,) not (addr) because second parameter is a tuple
        # Edit: (c,addr)
        # that's how you pass arguments to functions when creating new threads using thread module.
except KeyboardInterrupt:
    for thread in threads:
        thread.join(1)

s.close()
