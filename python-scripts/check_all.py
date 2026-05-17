"""
check_all.py - Leest alle bekende registers van de Fairland VBIV warmtepomp
Auteur: Tom Van Hoof
Project: https://github.com/[jouw-naam]/fairland-vbiv-ha
"""

import socket
import time

EW11_IP = "192.168.178.254"   # Pas aan naar jouw EW11A IP
EW11_PORT = 8899
SLAVE_ID = 50                  # Pas aan naar jouw slave ID (H37 in pomp menu)


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


registers = [
    # Instellingen
    (1011, "AAN/UIT instelling",          1.0, False),
    (1012, "Modus instelling",             1.0, False),
    (1013, "Doeltemp huidig",              0.1, True),
    (1019, "Modus restrictie",             1.0, False),
    # Frequentie grenzen
    (1020, "Min freq VERWARMEN Hz",        1.0, False),
    (1021, "Min freq KOELEN Hz",           1.0, False),
    (1022, "Max freq VERWARMEN Hz",        1.0, False),
    (1023, "Max freq KOELEN Hz",           1.0, False),
    (1047, "Max freq SILENT Hz",           1.0, False),
    # Ventilator
    (1063, "Max ventilator RPM",           1.0, False),
    (1065, "Min ventilator KOELEN",        1.0, False),
    (1067, "Min ventilator VERWARMEN",     1.0, False),
    (1071, "Ventilator stil RPM",          1.0, False),
    # Modus
    (1076, "Silent modus (0=nee 1=ja)",   1.0, False),
    (1081, "Waterpomp modus",              1.0, False),
    # Defrost
    (1101, "Defrost start temp",           0.1, True),
    (1103, "Defrost einde temp",           0.1, True),
    (1104, "Defrost cyclus min",           1.0, False),
    (1105, "Defrost max duur min",         1.0, False),
    # EEV
    (1116, "EEV modus (0=man 1=auto)",    1.0, False),
    # Setpoints
    (1135, "Setpoint Koelen",              0.1, True),
    (1136, "Setpoint Verwarmen",           0.1, True),
    (1137, "Setpoint Auto",                0.1, True),
    # Status
    (2011, "Status AAN/UIT",               1.0, False),
    (2012, "Status Modus actief",          1.0, False),
    (2019, "Output bits",                  1.0, False),
    (2020, "EEV klep positie",             1.0, False),
    (2021, "Compressor freq Hz",           1.0, False),
    (2022, "Compressor stroom A",          0.1, False),
    (2023, "IPM temperatuur",              1.0, False),
    # Temperaturen
    (2045, "T01 Zuiggas",                  0.1, True),
    (2046, "T02 Inlaat water",             0.1, True),
    (2047, "T03 Uitlaat water",            0.1, True),
    (2048, "T04 Coil",                     0.1, True),
    (2049, "T05 Buiten",                   0.1, True),
    (2050, "T06 Persgas",                  0.1, True),
    (2054, "Druk bar",                     0.1, False),
    (2056, "Vermogen 2056 (vast!)",        0.1, False),
    (2060, "T11 Superheat",                0.1, True),
    (2063, "Spanning V",                   1.0, False),
    (2065, "T15 Antivorst",                0.1, True),
    (2067, "Ventilator 1 RPM",             1.0, False),
    (2068, "Ventilator 2 RPM",             1.0, False),
    # Fouten
    (2074, "Fout register 1 (P/E)",        1.0, False),
    (2075, "Fout register 2 (F)",          1.0, False),
    (2076, "Fout register 3",              1.0, False),
]

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect((EW11_IP, EW11_PORT))
print(f"Verbonden met {EW11_IP}:{EW11_PORT} (slave {SLAVE_ID})\n")

print(f"{'REG':<6} {'BESCHRIJVING':<34} {'WAARDE':<10} RAW")
print("-" * 70)

for reg, naam, sc, sg in registers:
    val, raw = read_reg(s, reg, sc, sg)
    if val is not None:
        extra = ""
        if reg in (1012, 2012) and raw in (0, 1, 2):
            extra = f"  ({['Koelen', 'Verwarmen', 'Auto'][raw]})"
        elif reg == 1076:
            extra = f"  ({'Stil' if raw == 1 else 'Normaal'})"
        elif reg == 2019:
            extra = f"  (comp={'AAN' if raw & 1 else 'UIT'} pomp={'AAN' if raw & 8 else 'UIT'})"
        print(f"  {reg:<6} {naam:<34} {str(val):<10} {raw}{extra}")
    else:
        print(f"  {reg:<6} {naam:<34} TIMEOUT")
    time.sleep(0.15)

# Berekend vermogen
v, _ = read_reg(s, 2063)
a, _ = read_reg(s, 2022, 0.1)
if v and a:
    print(f"\n  Berekend vermogen (V x A): {v}V x {a}A = {round(v * a, 0)}W")

s.close()
print("\nKlaar!")
