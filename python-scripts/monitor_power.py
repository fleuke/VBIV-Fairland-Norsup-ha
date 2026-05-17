"""
monitor_power.py - Live vermogen monitor voor Fairland VBIV
Vergelijkt register 2056 met berekend V*A vermogen
Auteur: Tom Van Hoof
"""

import socket
import time
from datetime import datetime

EW11_IP = "192.168.178.254"
EW11_PORT = 8899
SLAVE_ID = 50


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return bytes([crc & 0xFF, crc >> 8])


def read_reg(s, reg, scale=1.0):
    req = bytearray([SLAVE_ID, 0x03, reg >> 8, reg & 0xFF, 0x00, 0x01])
    req += crc16(req)
    s.sendall(req)
    time.sleep(0.3)
    try:
        resp = s.recv(512)
        for i in range(len(resp) - 4):
            if resp[i] == SLAVE_ID and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                raw = int.from_bytes(resp[i+3:i+5], 'big')
                return round(raw * scale, 1), raw
        return None, None
    except Exception:
        return None, None


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect((EW11_IP, EW11_PORT))
print("Live vermogen monitor - elke 15s - Ctrl+C om te stoppen\n")
print(f"{'TIJD':<10} {'2056x0.1':>10} {'2056raw':>8} {'V':>6} {'A':>6} {'V*A':>8} {'Hz':>6}")
print("-" * 60)

try:
    while True:
        v,  _  = read_reg(s, 2063, 1.0)
        a,  _  = read_reg(s, 2022, 0.1)
        w,  rw = read_reg(s, 2056, 0.1)
        hz, _  = read_reg(s, 2021, 1.0)
        va = round(v * a, 0) if v and a else 0
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"  {ts:<10} {str(w):>10} {str(rw):>8} {str(v):>6} {str(a):>6} {str(va):>8} {str(hz):>6}")
        time.sleep(15)
except KeyboardInterrupt:
    print("\nGestopt!")
finally:
    s.close()
