from flask import Flask, render_template, request, jsonify
import json
from pynput.keyboard import Controller, Key

# Max 45 button


HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__)
keyboard = Controller()


SPECIAL_KEYS = {
    "Shift": Key.shift,
    "Ctrl": Key.ctrl,
    "Alt": Key.alt,
    "Tab": Key.tab,
    "Enter": Key.enter,
    "Esc": Key.esc,
    "Space": Key.space,
    "Up": Key.up,
    "Down": Key.down,
    "Left": Key.left,
    "Right": Key.right,
    "Backspace": Key.backspace,
    "Delete": Key.delete,
    "F1": Key.f1,
    "F2": Key.f2,
    "F3": Key.f3,
    "F4": Key.f4,
    "F5": Key.f5,
    "F6": Key.f6,
    "F7": Key.f7,
    "F8": Key.f8,
    "F9": Key.f9,
    "F10": Key.f10,
    "F11": Key.f11,
    "F12": Key.f12,
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/getAircraftName")
def getAircraftName():

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # print(data)

    aicraftName = list(data.keys())

    return aicraftName


@app.route("/api/getAircraftTouch", methods=["POST"])
def getAircraftTouch():

    data = request.get_json()
    aircraftName = data.get("aircraft")

    print("aircraft ISS ::: ", aircraftName)

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    aircraft = data[aircraftName]

    print(aircraft)

    return aircraft


@app.route("/api/sendCommand", methods=["POST"])
def sendCommand():

    data = request.get_json()
    cmd = data.get("cmd")  # exemple cmd = P

    print("CMD ISS ::: ", cmd)

    try:
        # Découper seulement si il y a un "+"
        parts = cmd.split("+") if "+" in cmd else [cmd]

        keys_to_press = []
        for part in parts:
            part = part.strip()
            if part in SPECIAL_KEYS:
                keys_to_press.append(SPECIAL_KEYS[part])
            else:
                keys_to_press.append(part)  # touche normale

        # Appuyer sur toutes les touches
        for k in keys_to_press:
            keyboard.press(k)

        # Relâcher dans l'ordre inverse
        for k in reversed(keys_to_press):
            keyboard.release(k)

        return jsonify({"status": "ok", "executed": cmd})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)


