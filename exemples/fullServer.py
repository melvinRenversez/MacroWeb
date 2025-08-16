#!/usr/bin/env python3
"""
DCS Macro Deck — single-file Flask server + touch UI

How it works
- Run this script on your gaming PC.
- Open the shown URL from your tablet (same Wi‑Fi/LAN).
- Tap buttons -> the PC simulates key presses for DCS (or any app in focus).

Notes
- Many games (including DCS) may require the script to run with admin rights for
  global key injection to be accepted.
- Default keybinds here are EXAMPLES — adjust to your own DCS bindings.
- Network is LAN only by default (binds 0.0.0.0). Add a simple token to avoid
  accidental taps from others on your LAN.

Dependencies
  pip install flask pynput
  (Optional fallback) pip install keyboard

Tested on Windows; also works on Linux/macOS for apps that accept synthetic keys.
"""

from __future__ import annotations

import os
import sys
import time
import threading
from dataclasses import dataclass
from typing import List, Dict, Optional

from flask import Flask, request, jsonify, render_template_string, abort

# ======================
# Input backends
# ======================
BACKEND = None

try:
    from pynput.keyboard import Key, Controller

    class PynputBackend:
        name = "pynput"

        def __init__(self) -> None:
            self.kb = Controller()
            self.special = {
                "ctrl": Key.ctrl,
                "shift": Key.shift,
                "alt": Key.alt,
                "altgr": Key.alt_gr if hasattr(Key, "alt_gr") else Key.alt,
                "cmd": Key.cmd if hasattr(Key, "cmd") else Key.cmd,
                "win": Key.cmd if hasattr(Key, "cmd") else Key.cmd,
                "enter": Key.enter,
                "tab": Key.tab,
                "space": Key.space,
                "esc": Key.esc,
                "escape": Key.esc,
                "backspace": Key.backspace,
                "delete": Key.delete,
                "home": Key.home,
                "end": Key.end,
                "pageup": Key.page_up,
                "pagedown": Key.page_down,
                "up": Key.up,
                "down": Key.down,
                "left": Key.left,
                "right": Key.right,
                "f1": Key.f1,
                "f2": Key.f2,
                "f3": Key.f3,
                "f4": Key.f4,
                "f5": Key.f5,
                "f6": Key.f6,
                "f7": Key.f7,
                "f8": Key.f8,
                "f9": Key.f9,
                "f10": Key.f10,
                "f11": Key.f11,
                "f12": Key.f12,
            }

        def _to_key(self, token: str):
            t = token.strip().lower()
            return self.special.get(t, t)

        def press_combo(self, combo: str):
            parts = [self._to_key(p) for p in combo.split("+") if p]
            # Hold modifiers then tap last key
            to_press = parts
            pressed = []
            try:
                for p in to_press:
                    self.kb.press(p)
                    pressed.append(p)
                time.sleep(0.01)
            finally:
                # release in reverse order
                for p in reversed(pressed):
                    try:
                        self.kb.release(p)
                    except Exception:
                        pass

    BACKEND = PynputBackend()
except Exception as e:
    BACKEND = None

# Optional fallback: keyboard library (Windows)
if BACKEND is None:
    try:
        import keyboard as kbd

        class KeyboardBackend:
            name = "keyboard"

            def press_combo(self, combo: str):
                kbd.press_and_release(combo)

        BACKEND = KeyboardBackend()
    except Exception:
        BACKEND = None

if BACKEND is None:
    print(
        "\nERROR: No input backend available. Install one of these:\n  pip install pynput\n  (or) pip install keyboard\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ======================
# Config
# ======================

# Change this! Use something simple to type on your tablet.
SECRET_TOKEN = os.environ.get("DECK_TOKEN", "change-me")

HOST = os.environ.get("DECK_HOST", "0.0.0.0")
PORT = int(os.environ.get("DECK_PORT", "5000"))

# === Define your buttons and macros here ===
# Each button can either send a single combo, or trigger a named macro sequence.
# Adjust combos to match your own DCS bindings.
BUTTONS: List[Dict] = [
    {"id": "gear", "label": "Gear Toggle", "combo": "w"},
    {"id": "flaps", "label": "Flaps Cycle", "combo": "f"},
    {"id": "brake", "label": "Wheel Brake", "combo": "w"},
    {"id": "light", "label": "Lights", "combo": "l"},
    {"id": "weapon", "label": "Release Weapon", "combo": "space"},
    {"id": "view1", "label": "F1 Cockpit", "combo": "f1"},
    {"id": "view2", "label": "F2 External", "combo": "f2"},
    {"id": "comm", "label": "Comm Menu", "combo": '"'},  # Example (quote)
    {"id": "start", "label": "Cold Start (Demo)", "macro": "cold_start_demo"},
]

# Macros are sequences of (combo, delay_in_seconds)
MACROS: Dict[str, List[Dict]] = {
    # Demo macro — replace with your own aircraft cold-start sequence.
    "cold_start_demo": [
        {"combo": "rctrl+home", "delay": 0.2},  # Example: engine start
        {"combo": "lctrl+home", "delay": 0.5},
        {"combo": "lshift+l", "delay": 0.2},  # lights
        {"combo": "lctrl+l", "delay": 0.2},
        {"combo": "f", "delay": 0.2},  # flaps cycle
        {"combo": "f", "delay": 0.2},
    ]
}

# ======================
# Flask app
# ======================
app = Flask(__name__)


def require_token():
    token = request.headers.get("X-Token") or request.args.get("token")
    if SECRET_TOKEN and token != SECRET_TOKEN:
        abort(401)


def press_combo(combo: str):
    BACKEND.press_combo(combo)


def run_macro(macro_name: str):
    seq = MACROS.get(macro_name, [])
    for step in seq:
        press_combo(step["combo"])
        time.sleep(float(step.get("delay", 0)))


@app.route("/")
def index():
    return render_template_string(
        INDEX_HTML,
        buttons=BUTTONS,
        token=SECRET_TOKEN,
        backend=getattr(BACKEND, "name", "unknown"),
    )


@app.post("/api/press")
def api_press():
    require_token()
    data = request.get_json(force=True, silent=True) or {}
    btn_id = data.get("id")
    combo = data.get("combo")
    macro = data.get("macro")

    if btn_id:
        # find button definition
        found = next((b for b in BUTTONS if b["id"] == btn_id), None)
        if not found:
            return jsonify({"ok": False, "error": "unknown button"}), 404
        combo = found.get("combo")
        macro = found.get("macro")

    if combo:
        press_combo(combo)
        return jsonify({"ok": True, "type": "combo", "combo": combo})

    if macro:
        threading.Thread(target=run_macro, args=(macro,), daemon=True).start()
        return jsonify({"ok": True, "type": "macro", "macro": macro})

    return jsonify({"ok": False, "error": "no combo or macro"}), 400


# ======================
# HTML UI (inline template)
# ======================
INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
  <title>DCS Macro Deck</title>
  <style>
    :root { --gap: 14px; --radius: 16px; --pad: 18px; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Noto Sans", Arial, sans-serif; margin:0; background:#0b0f14; color:#e8eef6; }
    .wrap { padding: var(--pad); max-width: 1100px; margin: 0 auto; }
    header { display:flex; align-items:center; justify-content:space-between; margin-bottom: var(--gap); }
    h1 { font-size: 20px; margin:0; font-weight:600; letter-spacing: .3px; }
    .status { font-size: 12px; opacity:.8; }
    .grid { display:grid; grid-template-columns: repeat(3, 1fr); gap: var(--gap); }
    @media (min-width: 700px){ .grid { grid-template-columns: repeat(4, 1fr);} }
    @media (min-width: 1000px){ .grid { grid-template-columns: repeat(6, 1fr);} }

    button.tile { border:0; border-radius: var(--radius); padding: 18px 14px; background: #111826; color: #e8eef6; 
      font-size: 18px; font-weight:600; box-shadow: 0 2px 0 rgba(255,255,255,.08) inset, 0 10px 20px rgba(0,0,0,.35);
      min-height: 84px; touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
    button.tile:active { transform: translateY(1px); filter: brightness(1.1); }
    .small { font-size:12px; opacity:.8; display:block; margin-top:6px; }

    .row { display:flex; gap: 10px; align-items:center; margin-top: var(--gap); }
    input[type="password"], input[type="text"] { background:#0f1522; color:#e8eef6; border:1px solid #1f2a3a; border-radius: 10px; padding:10px 12px; width: 200px; }
    .ok { color:#7cff9e; }
    .err { color:#ff8a8a; }
    .footer { margin-top: 18px; font-size: 12px; opacity:.7; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>DCS Macro Deck</h1>
      <div class="status">Backend: <strong>{{ backend }}</strong></div>
    </header>

    <div class="row">
      <input id="token" type="password" placeholder="Token" value="{{ token }}" />
      <span id="msg" class="ok"></span>
    </div>

    <div class="grid" id="grid">
      {% for b in buttons %}
        <button class="tile" onclick="send('{{ b.id }}')">
          {{ b.label }}
          {% if b.combo %}<span class="small">{{ b.combo }}</span>{% endif %}
          {% if b.macro %}<span class="small">macro: {{ b.macro }}</span>{% endif %}
        </button>
      {% endfor %}
    </div>

    <div class="footer">Tip: edit button combos in <code>BUTTONS</code> (server file) to match your DCS bindings.</div>
  </div>

  <script>
    async function send(id){
      const token = document.getElementById('token').value.trim();
      const msg = document.getElementById('msg');
      msg.textContent = '';
      try{
        const res = await fetch('/api/press',{
          method:'POST',
          headers:{'Content-Type':'application/json','X-Token': token},
          body: JSON.stringify({id})
        });
        const data = await res.json();
        if(!res.ok || !data.ok){ throw new Error(data.error || ('HTTP '+res.status)); }
        msg.textContent = data.type === 'macro' ? ('✓ Macro '+data.macro) : ('✓ '+data.combo);
        msg.className = 'ok';
      }catch(err){
        msg.textContent = 'Erreur: '+err.message;
        msg.className = 'err';
      }
    }
  </script>
</body>
</html>
"""

# ======================
# Main
# ======================
if __name__ == "__main__":
    print(f"DCS Macro Deck — backend: {getattr(BACKEND, 'name', '?')}")
    print(
        "\nIMPORTANT:\n- Set DECK_TOKEN env var or edit SECRET_TOKEN in the script.\n- Run as Administrator if DCS ignores inputs.\n"
    )
    print(f"Open from your tablet:   http://<PC-LAN-IP>:{PORT}/?token={SECRET_TOKEN}")
    print(f"(This PC) local test:    http://127.0.0.1:{PORT}/?token={SECRET_TOKEN}\n")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)


