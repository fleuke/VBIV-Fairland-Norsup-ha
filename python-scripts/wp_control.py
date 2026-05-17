"""
wp_control.py - Interactief controlemenu voor de Fairland VBIV warmtepomp
Auteur: Tom Van Hoof
Project: https://github.com/[jouw-naam]/fairland-vbiv-ha
"""

import socket
import time

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


def read_reg(s, reg, scale=1.0, signed=False):
    req = bytearray([SLAVE_ID, 0x03, reg >> 8, reg & 0xFF, 0x00, 0x01])
    req += crc16(req)
    s.sendall(req)
    time.sleep(0.3)
    try:
        resp = s.recv(512)
        for i in range(len(resp) - 4):
            if resp[i] == SLAVE_ID and resp[i+1] == 0x03 and resp[i+2] == 0x02:
                raw = int.from_bytes(resp[i+3:i+5], 'big')
                if signed and raw > 32767:
                    raw -= 65536
                return round(raw * scale, 1), raw
        return None, None
    except Exception:
        return None, None


def write_reg(s, reg, value):
    req = bytearray([SLAVE_ID, 0x06, reg >> 8, reg & 0xFF, value >> 8, value & 0xFF])
    req += crc16(req)
    s.sendall(req)
    time.sleep(0.5)
    try:
        resp = s.recv(512)
        for i in range(len(resp) - 5):
            if resp[i] == SLAVE_ID and resp[i+1] == 0x06:
                echo_reg = (resp[i+2] << 8) | resp[i+3]
                echo_val = (resp[i+4] << 8) | resp[i+5]
                if echo_reg == reg:
                    return True, echo_val
        return False, resp.hex()[:30]
    except Exception:
        return False, "TIMEOUT"


def toon_status(s):
    print("\n--- HUIDIGE STATUS ---")
    items = [
        (1011, "AAN/UIT",          1.0, False),
        (1012, "Modus instelling",  1.0, False),
        (2012, "Modus actief",      1.0, False),
        (1013, "Doeltemp",          0.1, True),
        (1135, "Set Koelen",        0.1, True),
        (1136, "Set Verwarmen",     0.1, True),
        (1137, "Set Auto",          0.1, True),
        (1076, "Stille modus",      1.0, False),
        (2021, "Freq Hz",           1.0, False),
        (2046, "T02 Inlaat",        0.1, True),
        (2047, "T03 Uitlaat",       0.1, True),
    ]
    for reg, naam, sc, sg in items:
        val, raw = read_reg(s, reg, sc, sg)
        if val is not None:
            extra = ""
            if reg in (1011, 2011):
                extra = "AAN" if raw == 1 else "UIT"
            elif reg in (1012, 2012):
                extra = ["Koelen", "Verwarmen", "Auto"][raw] if raw in (0, 1, 2) else str(raw)
            elif reg == 1076:
                extra = "Stil" if raw == 1 else "Normaal"
            print(f"  {reg}  {naam:<20} {val:>8}  {extra}")
        time.sleep(0.1)


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect((EW11_IP, EW11_PORT))
print(f"Verbonden met {EW11_IP}:{EW11_PORT}\n")

while True:
    print("\n" + "=" * 50)
    print("  WARMTEPOMP BEDIENING")
    print("=" * 50)
    print("  1  = Pomp UIT")
    print("  2  = Pomp AAN")
    print("  3  = Modus KOELEN")
    print("  4  = Modus VERWARMEN")
    print("  5  = Modus AUTO")
    print("  6  = Stille modus AAN")
    print("  7  = Stille modus UIT")
    print("  8  = Setpoint Koelen instellen")
    print("  9  = Setpoint Verwarmen instellen")
    print("  10 = Setpoint Auto instellen")
    print("  s  = Toon status")
    print("  q  = Stoppen")

    keuze = input("\nKeuze: ").strip().lower()

    if keuze == "q":
        break
    elif keuze == "s":
        toon_status(s)
    elif keuze == "1":
        ok, val = write_reg(s, 1011, 0)
        print(f"Pomp UIT -> {'OK' if ok else 'FOUT: ' + str(val)}")
        time.sleep(1)
        cur, _ = read_reg(s, 1011)
        print(f"Verificatie register 1011 = {cur}")
    elif keuze == "2":
        ok, val = write_reg(s, 1011, 1)
        print(f"Pomp AAN -> {'OK' if ok else 'FOUT: ' + str(val)}")
        time.sleep(1)
        cur, _ = read_reg(s, 1011)
        print(f"Verificatie register 1011 = {cur}")
    elif keuze == "3":
        ok, val = write_reg(s, 1012, 0)
        print(f"Modus KOELEN -> {'OK' if ok else 'FOUT: ' + str(val)}")
    elif keuze == "4":
        ok, val = write_reg(s, 1012, 1)
        print(f"Modus VERWARMEN -> {'OK' if ok else 'FOUT: ' + str(val)}")
    elif keuze == "5":
        ok, val = write_reg(s, 1012, 2)
        print(f"Modus AUTO -> {'OK' if ok else 'FOUT: ' + str(val)}")
    elif keuze == "6":
        ok, val = write_reg(s, 1076, 1)
        print(f"Stille modus AAN -> {'OK' if ok else 'FOUT: ' + str(val)}")
    elif keuze == "7":
        ok, val = write_reg(s, 1076, 0)
        print(f"Stille modus UIT -> {'OK' if ok else 'FOUT: ' + str(val)}")
    elif keuze == "8":
        temp = input("Koelen setpoint (bv 30): ")
        val_int = int(float(temp) * 10)
        ok, echo = write_reg(s, 1135, val_int)
        print(f"Setpoint Koelen {temp}°C -> {'OK' if ok else 'FOUT'}")
        time.sleep(1)
        cur, _ = read_reg(s, 1135, 0.1, True)
        print(f"Verificatie = {cur}°C")
    elif keuze == "9":
        temp = input("Verwarmen setpoint (bv 28): ")
        val_int = int(float(temp) * 10)
        ok, echo = write_reg(s, 1136, val_int)
        print(f"Setpoint Verwarmen {temp}°C -> {'OK' if ok else 'FOUT'}")
        time.sleep(1)
        cur, _ = read_reg(s, 1136, 0.1, True)
        print(f"Verificatie = {cur}°C")
    elif keuze == "10":
        temp = input("Auto setpoint (bv 25): ")
        val_int = int(float(temp) * 10)
        ok, echo = write_reg(s, 1137, val_int)
        print(f"Setpoint Auto {temp}°C -> {'OK' if ok else 'FOUT'}")
        time.sleep(1)
        cur, _ = read_reg(s, 1137, 0.1, True)
        print(f"Verificatie = {cur}°C")

s.close()
print("Klaar!")
