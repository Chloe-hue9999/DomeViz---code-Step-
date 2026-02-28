#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import sys

# 获取本地IP
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
except:
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        if ip_address.startswith('127.'):
            ip_address = "localhost"
    except:
        ip_address = "localhost"

url = f"http://{ip_address}:5000/phone"
print(f"QR Code URL: {url}")
print(f"Local IP: {ip_address}")
