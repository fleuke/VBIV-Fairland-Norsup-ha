# VBIV Pool Heat Pump — Home Assistant Integration via Modbus TCP

> **Complete Modbus TCP integration of the VBIV pool heat pump (VB Klimaattechniek / Pollet Pool Group) with Home Assistant using an EW11A WiFi-RS485 adapter.**
>
> Likely also compatible with other pumps using the same PC1004 mainboard — see [Compatible brands](#compatible-brands).

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.5+-blue)
![Modbus TCP](https://img.shields.io/badge/Protocol-Modbus%20TCP-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [Hardware](#hardware)
- [Discovery & Approach](#discovery--approach)
- [Verified working registers](#verified-working-registers)
- [EW11A configuration](#ew11a-configuration)
- [Home Assistant configuration](#home-assistant-configuration)
- [Python test scripts](#python-test-scripts)
- [Dashboard](#dashboard)
- [Known issues](#known-issues)
- [Compatible brands](#compatible-brands)
- [References](#references)

---

## Hardware

| Component | Details |
|-----------|---------|
| Heat pump | VBIV 20/3F H8 — VB Klimaattechniek / Pollet Pool Group (3-phase, 380V, 20kW) |
| WiFi adapter | EW11A (Waveshare) on **CN13** connector |
| Connection | Direct connection to CN13 (dedicated RS485 port) |
| Adapter IP | `192.168.178.254`, port `8899` |
| Protocol | **Modbus TCP** (NOT None/Transparent!) |
| Slave ID | **50** (configurable via H37 in pump menu) |

### EW11A wiring to CN13

```
CN13 (dedicated RS485 port on the mainboard):
RS485 A → RS485 A
RS485 B → RS485 B
GND     → GND
+V      → can also be picked up here for powering the EW11A
```

> ⚠️ **Important: use CN13, NOT CN8 (the display port)!**
>
> We first tried connecting the EW11A **in parallel** with the display on **CN8** (using a Y-splitter). This did **not** work reliably — timeouts and no usable data.
>
> The same conclusion was reached by others in the community (see the AquaTemp thread). CN13 is the dedicated RS485 remote control port and is the correct connector to use.
>
> The display continues to work normally when the EW11A is connected to CN13.

---

## Discovery & Approach

### Step 1: Configure the EW11A

The EW11A must be set to **Modbus TCP mode** (NOT "None" or "Transparent").

Settings:
```
Baudrate: 9600
Data bits: 8
Parity: None
Stop bits: 1
Mode: Modbus TCP Server
Port: 8899
```

> ⚠️ **Critical:** In "None" mode, communication is unreliable. Only Modbus TCP mode provides stable connections.

### Step 2: Set the Slave ID on the pump display

> ⚠️ **This is a critical step that must be done before anything else will work!**

The slave ID is configured directly on the pump's display panel:

1. Press the **gear/settings icon** on the display
2. Enter password **`022`** when prompted
3. Scroll through the menu to find **H37**
4. Change the value from `1` (default) to **`50`**
5. Confirm and exit

**Why not leave it at 1?** Slave ID 1 is the default and may conflict with other Modbus devices on your network. ID 50 works reliably.

> 💡 The parameter name H37 caused a lot of confusion — some people interpreted it as hexadecimal 0x37 = 55 decimal. It is simply the menu item labeled H37 on the pump display, and the value you enter (50) is the actual slave ID.

### Step 3: Register discovery

We read all registers using Python Modbus scripts. The registers use **FC03 (holding registers)**. FC04 (input registers) returns no useful data on this pump.

**What we tried:**
- FC04 registers at addresses 0–80 → no usable data
- Swap/no-swap combinations → not needed with FC03
- Various slave IDs → 50 works
- AppDaemon climate entity → works but limited (only auto/off modes)
- Modbus `numbers` and `selects` entities → conflict when sensors use the same register → solved using `input_number` / `input_select` helpers with automations

### Step 4: Power measurement

Register 2056 returns a **fixed value** (raw 23205 = 2320.5W) that does not change with actual load. Register 2055 always returns 0.

**Solution:** Calculate power via **V × A** (voltage × current):
- Voltage: register 2063
- Current: register 2022 × 0.1
- A template sensor calculates live V×A

---

## Verified working registers

All registers use **FC03 (holding)** with slave ID 50.

### Status registers (read-only)

| Register | Description | Scale | Signed | Notes |
|----------|-------------|-------|--------|-------|
| 2011 | ON/OFF status | 1.0 | no | 0=Off, 1=On |
| 2012 | Active mode status | 1.0 | no | 0=Cool, 1=Heat, 2=Auto |
| 2019 | Output bits | 1.0 | no | bit0=comp, bit1=fan high, bit3=water pump, bit4=4-way valve |
| 2034 | Switch bits | 1.0 | no | HP/LP/flow/remote status |

### Temperature sensors

| Register | Description | Scale | Signed |
|----------|-------------|-------|--------|
| 2045 | T01 Suction gas | 0.1 | yes |
| 2046 | T02 Water inlet | 0.1 | yes |
| 2047 | T03 Water outlet | 0.1 | yes |
| 2048 | T04 Coil | 0.1 | yes |
| 2049 | T05 Ambient | 0.1 | yes |
| 2050 | T06 Discharge gas | 0.1 | yes |
| 2060 | T11 Superheat | 0.1 | yes |
| 2065 | T15 Antifreeze | 0.1 | yes |
| 2023 | IPM module temperature | 1.0 | no |

### Electrical & mechanical

| Register | Description | Scale | Notes |
|----------|-------------|-------|-------|
| 2063 | Voltage V | 1.0 | Reliable |
| 2022 | Current A | 0.1 | Reliable |
| 2056 | Power W | 0.1 | ⚠️ Fixed value — use V×A instead! |
| 2021 | Compressor frequency Hz | 1.0 | |
| 2054 | Pressure bar | 0.1 | |
| 2020 | EEV valve position | 1.0 | steps |
| 2067 | Fan 1 RPM | 1.0 | |
| 2068 | Fan 2 RPM | 1.0 | |
| 2074 | Fault register 1 | 1.0 | P/E faults |
| 2075 | Fault register 2 | 1.0 | F faults |
| 2076 | Fault register 3 | 1.0 | |

### Settings (read & write via FC03/FC06)

| Register | Description | Scale | Write values |
|----------|-------------|-------|--------------|
| 1011 | ON/OFF | 1.0 | 0=Off, 1=On |
| 1012 | Mode | 1.0 | 0=Cool, 1=Heat, 2=Auto |
| 1013 | Current active setpoint | 0.1 | yes (°C × 10) |
| 1135 | Cooling setpoint | 0.1 | yes (°C × 10) |
| 1136 | Heating setpoint | 0.1 | yes (°C × 10) |
| 1137 | Auto setpoint | 0.1 | yes (°C × 10) |
| 1076 | Silent mode | 1.0 | 0=Normal, 1=Silent |

### Factory settings (do not change without good reason!)

| Register | Description | Factory value |
|----------|-------------|---------------|
| 1020 | Min freq heating | 20 Hz |
| 1021 | Min freq cooling | 20 Hz |
| 1022 | Max freq heating | **65 Hz** |
| 1023 | Max freq cooling | 40 Hz |
| 1047 | Max freq silent mode | 52 Hz |
| 1063 | Max fan speed | 700 RPM |
| 1071 | Fan speed in silent mode | 300 RPM |
| 1101 | Defrost start temp | -7°C |
| 1103 | Defrost end temp | 13°C |
| 1104 | Defrost cycle interval | 45 min |
| 1105 | Defrost max duration | 8 min |

### Silent mode explained

- `1076 = 1`: compressor max 52 Hz + fan 300 RPM → ~270W less power consumption
- `1076 = 0`: compressor max 65 Hz + fan 700 RPM
- Register 1047 sets the maximum compressor frequency during silent mode

---

## EW11A configuration

The required EW11A mode **depends on what you are connecting with**:

| Use case | EW11A mode |
|----------|-----------|
| Home Assistant Modbus integration | **Modbus TCP mode** |
| Python test scripts (direct TCP socket) | **None / Transparent mode** |

> ⚠️ This is a common point of confusion. If your Python scripts work but HA gives timeouts (or vice versa), the EW11A mode is almost certainly the cause.

### For Home Assistant

Set the EW11A to **Modbus TCP mode**:

EW11A web interface → Serial Port Settings → Protocol -> **Modbus**

**Symptoms of wrong mode (None instead of Modbus TCP):**
```
modbus zwembad_warmtepomp: No response received, CLOSING CONNECTION
modbus zwembad_warmtepomp: Not connected
```

### For Python scripts

Set the EW11A to **None / Transparent mode**:

EW11A web interface → Serial Port Settings → Protocol → **None**

In None mode the EW11A passes raw bytes through without wrapping them in Modbus TCP framing. The Python scripts build the raw Modbus RTU frames themselves and send them directly over a TCP socket — so the EW11A must not add any extra framing.

---

## Home Assistant configuration

See the `ha-config/` folder for all files.

### File structure

```
config/
├── packages/
│   ├── zwembad.yaml             ← Modbus config (Siemens LOGO! PLC + heat pump)
│   └── warmtepomp_helpers.yaml  ← input_select, input_number, automations
└── lovelace/
    └── warmtepomp.yaml          ← Dashboard
```

### Important notes

**Numbers and Selects don't appear** when sensors already use the same register. Solution: use `input_number` and `input_select` helpers with automations that write to Modbus.

**Scan intervals:** Minimum 60 seconds for the EW11A. Faster polling causes dropped connections. Voltage and current can be set to 15–30s for more responsive power calculation.

**Climate entity:** The `hvac_mode_register` configuration is required for heat/cool/auto modes:
```yaml
hvac_mode_register:
  address: 1012
  values:
    state_cool: 0
    state_heat: 1
    state_auto: 2
  write_registers: true
```

**Calculated power template:**
```yaml
- name: "Heat Pump Calculated Power"
  state: >
    {% set v = states('sensor.warmtepomp_spanning') | float(0) %}
    {% set a = states('sensor.warmtepomp_stroom') | float(0) %}
    {{ (v * a) | round(0) if v > 0 and a > 0 else 0 }}
  unit_of_measurement: "W"
  device_class: power
  state_class: measurement
```

---

## Python test scripts

See the `python-scripts/` folder for all scripts.

| Script | Purpose |
|--------|---------|
| `check_all.py` | Read all known registers in one go |
| `wp_control.py` | Interactive menu: on/off, mode, setpoints, silent mode |
| `monitor_power.py` | Live power monitor every 15 seconds |

### Usage

```bash
python check_all.py
python wp_control.py
python monitor_power.py
```

Requirements: Python 3.x, no additional packages needed (only `socket` and `time`).

---

## Dashboard

The dashboard includes:
- Climate thermostat card with heat/cool/auto/off
- Status: mode, ON/OFF, operating mode, silent mode toggle
- Setpoint sliders per mode (heating/cooling/auto)
- Mode memory (stored setpoints per mode)
- Water temperatures + ΔT
- Technical sensors (coil, superheat, suction gas, discharge gas)
- Electrical data (calculated power V×A, voltage, current, compressor frequency)
- Mechanical data (fan RPM, pressure, EEV position)
- Historical graphs (24h)
- Diagnostics (fault registers)
- Energy meter (kWh via Riemann sum integral helper)

---

## Known issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Timeouts / unavailable entities | EW11A in wrong mode | Set EW11A to Modbus TCP |
| Numbers/Selects don't appear | Conflict with sensor on same register | Use input_number/input_select + automations |
| Climate shows only auto/off | hvac_mode_register missing from config | Add hvac_mode_register block to climate config |
| Power always shows 2320W | Register 2056 returns a fixed value | Calculate via V×A template sensor |
| Entity IDs with `_2` `_3` suffix | Duplicate unique_ids from multiple YAML iterations | Delete old unavailable entities via Settings → Entities |
| EW11A drops connection | Too many simultaneous TCP connections | Increase scan_interval, add `message_wait_milliseconds: 150` |

---

## Compatible brands

The VBIV is a product of **VB Klimaattechniek** (Netherlands), acquired by **Pollet Pool Group (PPG)** in 2021. The pump uses the **PC1004 mainboard** with a standard Modbus RTU protocol over RS485 via the CN13 connector.

The same registers and protocol are used by other brands sharing the same mainboard or controller. Based on community experience, the following brands are likely (at least partially) compatible:

| Brand | Model | Notes |
|-------|-------|-------|
| VB Klimaattechniek / PPG | **VBIV** series (9/12/17/20/24/29 kW) | ✅ Tested — this repo |
| VB Klimaattechniek / PPG | **VBPP** series | Same mainboard, likely compatible |
| Norsup | P-series (P14, P17, P24, P35X) | Community reports same Modbus protocol |
| Fairland | IPHCR45, Inverter Plus series | Same protocol, possibly different slave ID |
| Fairland | InverX series | Likely compatible |
| Various OEM | Pumps with PC1004 mainboard and AquaTemp WiFi module | Same protocol |

> ⚠️ **Note:** Registers may differ slightly depending on model and firmware version. Always run `check_all.py` to verify your specific pump.

> 💡 **Got it working on a different pump?** Open an Issue or Pull Request with your findings!

---

## References

- [ESP-Home Fairland Heatpump by rstcologne](https://github.com/rstcologne/ESP-Home-Fairland-Heatpump) — initial register mapping reference
- [Fairland IPHCR45 Modbus by spdr870](https://github.com/spdr870/fairland_iphcr45_modbus) — additional register information
- [HA Community: Aqua Temp controller thread](https://community.home-assistant.io/t/implementation-of-aqua-temp-controller/230400) — compatible pumps and community experiences
- [HA Community: Fairland heat pump to HA](https://community.home-assistant.io/t/fairland-heat-pump-to-ha/304871) — alternative integration approaches
- [Pollet Pool Group — VBIV product page](https://shop.polletpoolgroup.eu) — official manufacturer
- [zwembadwarmtepomp.nl](https://zwembadwarmtepomp.nl) — VB Klimaattechniek website
- [Home Assistant Modbus documentation](https://www.home-assistant.io/integrations/modbus/)
- [EW11A product page](https://www.waveshare.com/wiki/RS485_TO_ETH_(B))
- VBIV Installation & Instruction Manual (included with device)

---

## License

MIT License — free to use, but please credit the original author and sources.

---

## Contributing

Pull requests welcome! Do you have a different pump model? Run `check_all.py`, document your register readings, and open an issue with your findings.

**Tested on:**
- VBIV 20/3F H8 (VB Klimaattechniek / Pollet Pool Group)
- Home Assistant OS 17.3, Core 2026.5.1
- Raspberry Pi 5
- EW11A WiFi-RS485 adapter in Modbus TCP mode
