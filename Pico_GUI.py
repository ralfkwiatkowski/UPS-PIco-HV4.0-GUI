from flask import Flask, render_template, request, redirect, url_for, jsonify
import smbus
import threading
import time
import logging

app = Flask(__name__)

# Flask-Logging deaktivieren
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

bus = smbus.SMBus(1)

# Funktionen zur I2C-Kommunikation

# Funktion zur Abfrage der CPU-Temperatur durch den PIco
def getCPUtemperaturePIco():
    try:
        data = bus.read_word_data(0x69, 0x1A)
        # BCD to integer conversion
        cpu_temp = ((data >> 12) & 0xF) * 1000 + ((data >> 8) & 0xF) * 100 + ((data >> 4) & 0xF) * 10 + (data & 0xF)
        return f"{cpu_temp} °C"
    except Exception as e:
        return f"Error: {str(e)}"

# Funktion zur Abfrage des Lüfterstatus
def fan_state():
    data = bus.read_byte_data(0x69, 0x21)
    return "ON" if (data & 0x01) else "OFF"

# Funktion zur Abfrage des Schwellenwertes
def getFANThreshold():
    return format(bus.read_byte_data(0x6b, 0x13), "02x")

# Funktion zur Abfrage des Powering-Modus. Netz oder Backup.
def getPoweringMode():
    data = bus.read_byte_data(0x69, 0x00)
    data = data & 0x01
    if data == 1:
        return "Cable powered"
    elif data == 0:
        return "Backup powered"
    else:
        return "Unknown"

# Funktion zur Abfrage des Batteriespannungsniveaus
def getBatteryLevel():
    data = bus.read_word_data(0x69, 0x08)
    # BCD to integer conversion
    battery_voltage = ((data >> 12) & 0xF) * 1000 + ((data >> 8) & 0xF) * 100 + ((data >> 4) & 0xF) * 10 + (data & 0xF)
    return f"{battery_voltage * 0.01} V"

# Funktion zur Abfrage des SCAP-Spannungsniveaus
def getSCAPLevel():
    try:
        data = bus.read_word_data(0x69, 0x06)
        # BCD to integer conversion
        capacitor_voltage = ((data >> 12) & 0xF) * 1000 + ((data >> 8) & 0xF) * 100 + ((data >> 4) & 0xF) * 10 + (data & 0xF)
        # Formatieren auf zwei Nachkommastellen
        return f"{capacitor_voltage * 0.01:.2f} V"
    except Exception as e:
        return f"Error: {str(e)}"
    
# Funktion zur Abfrage des Batterie Typs
def getBatteryType():
    data = bus.read_byte_data(0x6b, 0x07)
    if data == 0x4c:
        return "LiPo"
    elif data == 0x49:
        return "Li-Ion"
    elif data == 0x46:
        return "LiFePO4"
    elif data == 0x48:
        return "NiMH"
    elif data == 0x41:
        return "SAL"
    elif data == 0x43:
        return "int.SCAP 100F"
    elif data == 0x44:
        return "ext.SCAP-Bank"
    else:
        return "nicht erlaubt"
    
# Funktion zum ändern des Batterie Typs
def setBatteryType(new_value):
    try:
        new_value = new_value.lower().replace("0x", "")
        new_value_int = int(new_value, 16)
        bus.write_byte_data(0x6b, 0x07, new_value_int)
        return True
    except Exception as e:
        return False

# Funktion zum ändern des Schwellenwertes
def setFANThreshold(new_value):
    try:
        new_value = new_value.lower().replace("0x", "")
        new_value_int = int(new_value, 16)
        bus.write_byte_data(0x6b, 0x13, new_value_int)
        return True
    except Exception as e:
        return False
    
# Funktion zum ändern des Batterie Typs
def setBatteryType(new_value):
    try:
        new_value = new_value.lower().replace("0x", "")
        new_value_int = int(new_value, 16)
        bus.write_byte_data(0x6b, 0x07, new_value_int)
        return True
    except Exception as e:
        return

# Funktion zum Protokollieren der I2C-Werte. Werden an der Konsole ausgegeben
def log_i2c_values():
    while True:
        cpu_temp = getCPUtemperaturePIco()
        fan_status = fan_state()
        current_threshold = getFANThreshold()
        powering_mode = getPoweringMode()
        battery_level = getBatteryLevel()
        capacitor_level = getSCAPLevel()
        battery_type = getBatteryType()
        print(f"CPU Temperatur: {cpu_temp}, Lüfterstatus: {fan_status}, Aktueller Schwellenwert: {current_threshold}, Powering Mode: {powering_mode}, Battery Level: {battery_level}, SCAP Level: {capacitor_level}, battery type: {battery_type}")
        time.sleep(10)  # Alle 10 Sekunden protokollieren

# Routen
@app.route("/")
def index():
    data = {
        "cpu_temp": getCPUtemperaturePIco(),
        "fan_status": fan_state(),
        "current_threshold": getFANThreshold(),
        "powering_mode": getPoweringMode(),
        "battery_level": getBatteryLevel(),
        "capacitor_level": getSCAPLevel(),
        "battery_type": getBatteryType()
    }
    return render_template("Pico_Cht_rkw_10.html", **data)

@app.route("/get_data")
def get_data():
    try:
        data = {
            "cpu_temp": getCPUtemperaturePIco(),
            "fan_status": fan_state(),
            "current_threshold": getFANThreshold(),
            "powering_mode": getPoweringMode(),
            "battery_level": getBatteryLevel(),
            "capacitor_level": getSCAPLevel(),
            "battery_type": getBatteryType()
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/set_threshold", methods=["POST"])
def set_threshold():
    new_threshold = request.form.get("new_threshold")
    if setFANThreshold(new_threshold):
        return redirect(url_for("index"))
    else:
        return f"Fehler: Ungültiger Wert {new_threshold}"
    
@app.route("/set_battery_type", methods=["POST"])
def set_battery_type():
    new_battery_type = request.form.get("new_battery_type")
    if setBatteryType(new_battery_type):
        return redirect(url_for("index"))
    else:
        return f"Fehler: Ungültiger Wert {new_battery_type}"


if __name__ == "__main__":
    # Starten Sie den Thread zum Protokollieren der I2C-Werte
    log_thread = threading.Thread(target=log_i2c_values)
    log_thread.daemon = True
    log_thread.start()

    app.run(host="0.0.0.0", port=5020)
