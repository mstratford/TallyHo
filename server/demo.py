#!/usr/bin/env python
"""
TallyHo Server for serving the TallyHo client with camera updates from a switcher
"""
import socket
import json

HOST = ""  # Everywhere
PORT = 8000  # Port to listen on (non-privileged ports are > 1023)
from time import sleep


def send_message(conn, message):
    print(f"Sending {message}")
    conn.sendall(f"{json.dumps(message)}\n".encode())


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
            except:
                pass
