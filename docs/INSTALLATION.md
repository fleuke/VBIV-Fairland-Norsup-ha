# Step-by-step Installation Guide

## Prerequisites

- Home Assistant OS (tested on 2026.5.1)
- EW11A WiFi-RS485 adapter
- JST XH 4-pin Y-splitter cable
- Python 3.x on your PC (for test scripts)
- Network access to the EW11A

---

## Step 1: EW11A hardware wiring

1. Open the heat pump enclosure and locate connector **CN13** on the mainboard — this is the dedicated RS485 remote control port
2. Wire as follows:
   - EW11A **A** → CN13 RS485-A
   - EW11A **B** → CN13 RS485-B
   - EW11A **GND** → CN13 GND
   - EW11A **+V** → can also be sourced from CN13

> ⚠️ **Use CN13 — not CN8 (the display connector)!**
>
> We initially tried connecting the EW11A in parallel to the display port (CN8) using a Y-splitter. This did **not** work — the bus was unreliable and produced no usable data. The same pitfall is mentioned in the AquaTemp community thread. CN13 is the correct dedicated remote RS485 port.

---

## Step 2: EW11A software configuration

1. Connect to the EW11A via its web interface (default IP: 192.168.4.1 on first use)
2. Assign a fixed IP address on your network (we use 192.168.178.254)
3. Configure the serial port:
   - Baudrate: **9600**
   - Data bits: **8**
   - Parity: **None**
   - Stop bits: **1**
4. Set the Transfer Protocol based on what you are using:
   - **For Home Assistant:** → **Modbus_TCP_Protocol**
   - **For Python test scripts:** → **None** (transparent/raw mode)
5. Port: **8899**
6. Save and restart the EW11A

> ⚠️ **This is a common source of confusion.** The required mode is different depending on what you connect with:
> - Home Assistant's Modbus integration expects proper Modbus TCP framing → use **Modbus TCP mode**
> - The Python scripts send raw Modbus RTU frames over a plain TCP socket → use **None/Transparent mode**
>
> If your Python scripts work but HA gives timeouts, or the other way around, switch the EW11A mode.

---

## Step 3: Set Slave ID on the heat pump display

> ⚠️ **Critical step — do this before anything else!**

1. Press the **gear/settings icon** on the heat pump display
2. Enter password **`022`** when prompted
3. Scroll to parameter **H37**
4. Change the value from `1` (factory default) to **`50`**
5. Confirm and exit

> 💡 Note: H37 is simply a menu item name on the display — it is NOT hexadecimal. The value you enter (50) is the actual Modbus slave ID.

---

## Step 4: Test the connection with Python

1. Download `python-scripts/check_all.py`
2. Edit the IP address at the top of the script to match your EW11A
3. Run:

```bash
python check_all.py
```

You should see all registers with values. If you only see TIMEOUT:
- Check the EW11A mode (must be Modbus TCP)
- Check the IP address and port
- Check the slave ID

---

## Step 5: Home Assistant configuration

### 5a. Enable packages

Add to `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

### 5b. Copy files

```
config/
├── packages/
│   ├── zwembad.yaml                ← Modbus config (LOGO! PLC + heat pump)
│   └── warmtepomp_helpers.yaml     ← Helpers + automations
```

Copy `ha-config/zwembad_warmtepomp.yaml` as the heat pump section in your `packages/zwembad.yaml`.

Copy `ha-config/warmtepomp_helpers.yaml` to `packages/warmtepomp_helpers.yaml`.

### 5c. Restart HA

After copying: **Settings → System → Restart**

### 5d. Check entities

Go to **Developer Tools → States** and filter on "warmtepomp". You should see dozens of entities.

---

## Step 6: Set up the dashboard

1. Create a new dashboard or open an existing one
2. Click **Edit → Raw configuration editor**
3. Paste the contents of `ha-config/warmtepomp_lovelace.yaml`
4. Save

---

## Step 7: Set up the energy meter

1. Go to **Settings → Devices & Services → Helpers**
2. Click **+ Create → Riemann sum integral**
3. Configure:
   - Name: `Heat Pump Energy`
   - Input sensor: `sensor.warmtepomp_vermogen_berekend`
   - Method: Left
   - Time unit: Hours
4. Go to **Settings → Energy → Individual devices**
5. Add `sensor.heat_pump_energy`

---

## FAQ

### Why are there entities with a `_2` or `_3` suffix?

HA tracks unique_ids. If you installed multiple YAML versions with the same unique_id, HA creates new entities with a numeric suffix. Remove the old ones via **Settings → Entities → filter "warmtepomp" → sort by State → select unavailable → Delete**.

### Why don't numbers and selects appear?

Modbus `numbers` and `selects` conflict when sensors already use the same register. The solution in this project is to use `input_number` and `input_select` helpers, with automations writing to Modbus on change.

### The climate entity shows only auto/off

Add `hvac_mode_register` to the climate configuration. See `ha-config/zwembad_warmtepomp.yaml` for the correct setup.
