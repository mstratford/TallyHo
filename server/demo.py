#!/usr/bin/env python
"""
TallyHo Server for serving the TallyHo client with camera updates from a switcher
"""
import socket

HOST = ""  # Everywhere
PORT = 8000  # Port to listen on (non-privileged ports are > 1023)
from time import sleep

while True:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, addr = s.accept()
        with conn:
            try:
                while True:
                    print(f"Connected by {addr}")
                    for i in range(4):

                        conn.sendall(str(i).encode())
                        sleep(1)
            except:
                pass
