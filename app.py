import json
import os
import threading
import time

import bcrypt
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

# Flask app pointing to correct template/static folder
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "mysecret"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------- Music Engine ----------
try:
    from music_engine import play as music_play, pause_resume, stop as music_stop, set_volume, get_status as music_status
    MUSIC_AVAILABLE = True
except ImportError:
    MUSIC_AVAILABLE = False

# ---------- Gesture Control ----------
gesture_thread = None
gesture_running = False
gesture_status = "stopped"   # "stopped" | "running" | "error"
gesture_last_action = ""

def gesture_loop():
    global gesture_running, gesture_status, gesture_last_action

    try:
        import cv2
        import mediapipe as mp

        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles

        hands_detector = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            gesture_status = "error"
            gesture_last_action = "Camera not found"
            gesture_running = False
            return

        gesture_status = "running"
        prev_state = "neutral"
        last_action_time = 0
        COOLDOWN = 1.0

        def get_hand_state(landmarks):
            fingers_closed = 0
            tips = [8, 12, 16, 20]
            pips  = [6, 10, 14, 18]
            for i in range(4):
                if landmarks[tips[i]].y > landmarks[pips[i]].y:
                    fingers_closed += 1
            thumb_tip_y   = landmarks[4].y
            index_base_y  = landmarks[5].y
            pinky_base_y  = landmarks[17].y
            if fingers_closed >= 4:
                if thumb_tip_y < index_base_y - 0.05:
                    return "thumbs_up"
                elif thumb_tip_y > pinky_base_y + 0.05:
                    return "thumbs_down"
                else:
                    return "fist"
            elif fingers_closed == 0:
                return "open"
            return "neutral"

        while gesture_running:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands_detector.process(rgb_frame)

            current_state = "neutral"
            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())
                    current_state = get_hand_state(hand_landmarks.landmark)

            if (time.time() - last_action_time > COOLDOWN and
                    prev_state == "neutral" and current_state != "neutral"):

                if current_state == "open":
                    rooms["living"]["light"] = not rooms["living"]["light"]
                    state = rooms["living"]["light"]
                    gesture_last_action = f"💡 Light {'ON' if state else 'OFF'}"
                    log_action("💡", f"[Gesture][Living] Light {'ON' if state else 'OFF'}")
                    persist()
                    emit_update()
                    last_action_time = time.time()

                elif current_state == "fist":
                    rooms["living"]["fan_speed"] = 0 if rooms["living"]["fan_speed"] > 0 else 3
                    spd = rooms["living"]["fan_speed"]
                    gesture_last_action = f"🌀 Fan {'ON (speed 3)' if spd else 'OFF'}"
                    log_action("🌀", f"[Gesture][Living] Fan {'ON (speed 3)' if spd else 'OFF'}")
                    persist()
                    emit_update()
                    last_action_time = time.time()

                elif current_state == "thumbs_up":
                    new_speed = min(5, rooms["living"]["fan_speed"] + 1)
                    if new_speed != rooms["living"]["fan_speed"]:
                        rooms["living"]["fan_speed"] = new_speed
                        gesture_last_action = f"⬆️ Fan speed → {new_speed}"
                        log_action("⬆️", f"[Gesture][Living] Fan speed → {new_speed}")
                        persist()
                        emit_update()
                    else:
                        gesture_last_action = "⚠️ Max speed reached"
                        log_action("⚠️", "[Gesture] Max fan speed reached")
                    last_action_time = time.time()

                elif current_state == "thumbs_down":
                    new_speed = max(0, rooms["living"]["fan_speed"] - 1)
                    if new_speed != rooms["living"]["fan_speed"]:
                        rooms["living"]["fan_speed"] = new_speed
                        gesture_last_action = f"⬇️ Fan speed → {new_speed}"
                        log_action("⬇️", f"[Gesture][Living] Fan speed → {new_speed}")
                        persist()
                        emit_update()
                    else:
                        gesture_last_action = "⚠️ Fan already OFF"
                        log_action("⚠️", "[Gesture] Fan already OFF")
                    last_action_time = time.time()

            prev_state = "neutral" if not result.multi_hand_landmarks else current_state

            color = (0, 255, 0) if current_state == "neutral" else (0, 165, 255)
            cv2.putText(frame, f"Gesture: {current_state.upper()}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, f"Fan Speed: {rooms['living']['fan_speed']}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

    except Exception as e:
        gesture_last_action = f"Error: {str(e)}"
        gesture_status = "error"

    gesture_running = False
    gesture_status = "stopped"


@app.route("/start_gesture", methods=["POST"])
def start_gesture():
    global gesture_thread, gesture_running, gesture_status, gesture_last_action
    if gesture_running:
        return jsonify({"success": False, "message": "Gesture control already running."})
    gesture_running = True
    gesture_status = "running"
    gesture_last_action = "Starting..."
    gesture_thread = threading.Thread(target=gesture_loop, daemon=True)
    gesture_thread.start()
    return jsonify({"success": True, "message": "Gesture control started."})


@app.route("/stop_gesture", methods=["POST"])
def stop_gesture():
    global gesture_running, gesture_status, gesture_last_action
    if not gesture_running:
        return jsonify({"success": False, "message": "Gesture control is not running."})
    gesture_running = False
    gesture_status = "stopped"
    gesture_last_action = "Stopped by user."
    return jsonify({"success": True, "message": "Gesture control stopped."})


@app.route("/gesture_status", methods=["GET"])
def get_gesture_status():
    return jsonify({
        "status": gesture_status,
        "last_action": gesture_last_action
    })


@app.route("/get_state", methods=["GET"])
def get_state():
    return jsonify(rooms)

# ---------- PWA Routes ----------
@app.route("/static/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/static/service-worker.js")
def service_worker():
    response = send_from_directory("static", "service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login_page"))  # 🔐 Not logged in → go to login page
    return render_template("index.html", username=session["user"])  # ✅ Logged in → show home


# ✅ Login Page (if needed)
@app.route("/loginpage")
def login_page():
    return render_template("login.html")

# ---------- User DB ----------
USER_FILE = "users.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as file:
        return json.load(file)

def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent=2)

# ---------- Device State Persist ----------
STATE_FILE = "state.json"

ROOMS = ["living", "bedroom", "kitchen", "balcony"]

DEFAULT_STATE = {
    "living": {
        "light": False, "fan_speed": 0, "curtain": False,
        "dimmer": 50, "inverter": False, "ac": False
    },
    "bedroom": {
        "light": False, "fan_speed": 0, "curtain": False,
        "dimmer": 50, "inverter": False, "ac": False
    },
    "kitchen": {
        "light": False, "fan_speed": 0, "curtain": False,
        "dimmer": 50, "inverter": False, "ac": False
    },
    "balcony": {
        "light": False, "fan_speed": 0, "curtain": False,
        "dimmer": 50, "inverter": False, "ac": False
    }
}

def load_state():
    if not os.path.exists(STATE_FILE):
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE.copy()
    with open(STATE_FILE, "r") as f:
        data = json.load(f)
    # purana single-room state.json ho toh migrate karo
    if "living" not in data:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE.copy()
    # ac key missing ho toh add karo
    changed = False
    for room in DEFAULT_STATE:
        if room not in data:
            data[room] = DEFAULT_STATE[room].copy()
            changed = True
        elif "ac" not in data[room]:
            data[room]["ac"] = False
            changed = True
    if changed:
        save_state(data)
    return data

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# Load state at startup
rooms = load_state()

def persist():
    save_state(rooms)

def emit_update():
    socketio.emit("state_update", rooms)

def get_room(r):
    return rooms.get(r, rooms["living"])

# ---------- Activity Log ----------
activity_log = []   # max 50 entries in memory
MAX_LOG = 50

# ---------- Schedule Storage ----------
schedules = []  # [{room, device, on_time, off_time}]

def schedule_checker():
    """Background thread — har 5 sec mein scheduled actions check karo"""
    # key = (room, device, time_str, "on"/"off") → date jab fire hua
    fired = {}
    while True:
        try:
            from datetime import datetime
            dt  = datetime.now()
            now = dt.strftime("%H:%M")
            today = dt.strftime("%Y-%m-%d")

            for sch in schedules:
                room     = sch.get("room", "living")
                device   = sch.get("device", "light")
                on_time  = sch.get("on_time", "")
                off_time = sch.get("off_time", "")

                on_key  = (room, device, on_time,  "on")
                off_key = (room, device, off_time, "off")

                # ON — sirf fire karo agar aaj fire nahi hua
                if on_time and now == on_time and fired.get(on_key) != today:
                    fired[on_key] = today
                    if device == "light":     rooms[room]["light"] = True
                    elif device == "fan":     rooms[room]["fan_speed"] = 3
                    elif device == "curtain": rooms[room]["curtain"] = True
                    persist(); emit_update()
                    log_action("⏰", f"[{room.title()}] Schedule: {device.title()} ON ✅")

                # OFF — sirf fire karo agar aaj fire nahi hua
                if off_time and now == off_time and fired.get(off_key) != today:
                    fired[off_key] = today
                    if device == "light":     rooms[room]["light"] = False
                    elif device == "fan":     rooms[room]["fan_speed"] = 0
                    elif device == "curtain": rooms[room]["curtain"] = False
                    persist(); emit_update()
                    log_action("⏰", f"[{room.title()}] Schedule: {device.title()} OFF ✅")

        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(5)

# Start scheduler background thread
_scheduler = threading.Thread(target=schedule_checker, daemon=True)
_scheduler.start()

def log_action(icon, message):
    from datetime import datetime
    entry = {
        "time": datetime.now().strftime("%I:%M:%S %p"),
        "icon": icon,
        "message": message
    }
    activity_log.insert(0, entry)
    if len(activity_log) > MAX_LOG:
        activity_log.pop()
    # WebSocket se log update broadcast karo
    socketio.emit("log_update", activity_log)

@app.route("/get_log", methods=["GET"])
def get_log():
    return jsonify(activity_log)

@app.route("/clear_log", methods=["POST"])
def clear_log():
    activity_log.clear()
    return jsonify({"success": True})

# ---------- Smart Home Endpoints ----------

@app.route("/get_schedules", methods=["GET"])
def get_schedules():
    return jsonify(schedules)

@app.route("/delete_schedule", methods=["POST"])
def delete_schedule():
    data = request.get_json() or {}
    room   = data.get("room")
    device = data.get("device")
    schedules[:] = [s for s in schedules
                    if not (s["room"] == room and s["device"] == device)]
    return jsonify({"success": True})

@app.route("/toggle_ac", methods=["POST"])
def toggle_ac():
    data = request.get_json() or {}
    room = data.get("room", "bedroom")
    status = data.get("status", False)
    if room in rooms:
        rooms[room]["ac"] = status
        persist()
        emit_update()
    log_action("❄️", f"[{room.title()}] AC turned {'ON' if status else 'OFF'}")
    return jsonify({"message": f"AC {'ON' if status else 'OFF'}"})

@app.route("/toggle_light", methods=["POST"])
def toggle_light():
    data = request.get_json() or {}
    room = data.get("room", "living")
    rooms[room]["light"] = not rooms[room]["light"]
    state = rooms[room]["light"]
    persist()
    emit_update()
    log_action("💡", f"[{room.title()}] Light turned {'ON' if state else 'OFF'}")
    return jsonify({"status": "on" if state else "off"})

@app.route("/set_fan_speed", methods=["POST"])
def set_fan_speed():
    data = request.get_json() or {}
    room = data.get("room", "living")
    speed = data.get("speed", 0)
    rooms[room]["fan_speed"] = speed
    persist()
    emit_update()
    log_action("🌀", f"[{room.title()}] Fan speed set to {speed}")
    return jsonify({"message": f"Fan speed set to {speed}"})

@app.route("/toggle_curtain", methods=["POST"])
def toggle_curtain():
    data = request.get_json() or {}
    room = data.get("room", "living")
    open_state = data.get("open", False)
    rooms[room]["curtain"] = open_state
    persist()
    emit_update()
    log_action("🪟", f"[{room.title()}] Curtains {'Opened' if open_state else 'Closed'}")
    return jsonify({"message": "Curtains are Open" if open_state else "Curtains are Closed"})

@app.route("/set_dimmer", methods=["POST"])
def set_dimmer():
    data = request.get_json() or {}
    room = data.get("room", "living")
    brightness = data.get("brightness", 50)
    rooms[room]["dimmer"] = brightness
    persist()
    emit_update()
    log_action("🔆", f"[{room.title()}] Brightness set to {brightness}%")
    return jsonify({"message": f"Brightness: {brightness}%"})

@app.route("/inverter", methods=["POST"])
def inverter():
    data = request.get_json() or {}
    room = data.get("room", "living")
    status = data.get("status", False)
    rooms[room]["inverter"] = status
    persist()
    emit_update()
    log_action("⚡", f"[{room.title()}] Inverter {'ON' if status else 'OFF'}")
    return jsonify({"message": "Inverter ON – Low Power Mode" if status else "Inverter OFF – Full Power"})

@app.route("/check_temperature", methods=["POST"])
def check_temperature():
    data = request.get_json() or {}
    room = data.get("room", "living")
    temp = data.get("temperature", 0)
    status = "normal"
    if temp < 18: status = "Too Cold"
    elif temp > 30: status = "Too Hot"
    log_action("🌡️", f"[{room.title()}] Temperature: {temp}°C — {status}")
    return jsonify({"message": f"Room is {status}"})

@app.route("/detect_gas", methods=["POST"])
def detect_gas():
    data = request.get_json() or {}
    gas_leak = data.get("leak", False)
    log_action("⚠️" if gas_leak else "✅", f"[Kitchen] Gas: {'Leak Detected!' if gas_leak else 'All clear'}")
    return jsonify({"status": "Leak Detected" if gas_leak else "Safe"})

@app.route("/unlock_door", methods=["POST"])
def unlock_door():
    data = request.get_json() or {}
    if data.get("password") == "1234":
        log_action("🔓", "Door unlocked successfully")
        return jsonify({"status": "success", "message": "Door Unlocked"})
    log_action("🔒", "Door unlock failed — wrong password")
    return jsonify({"status": "fail", "message": "Incorrect Password"})

@app.route("/check_soil", methods=["POST"])
def check_soil():
    dry = (request.get_json() or {}).get("dry", False)
    log_action("🌿", f"Soil: {'Watering started' if dry else 'No watering needed'}")
    return jsonify({"message": "Watering plants..." if dry else "No need to water."})

@app.route("/ring_bell", methods=["POST"])
def ring_bell():
    log_action("🔔", "Doorbell pressed — visitor at door")
    return jsonify({"message": "🔔 Someone pressed the bell!"})

@app.route("/approach_door", methods=["POST"])
def approach_door():
    log_action("🚪", "Auto door opened — someone approached")
    return jsonify({"message": "🚪 Door opened automatically!"})

@app.route("/detect_intruder", methods=["POST"])
def detect_intruder():
    intruder = (request.get_json() or {}).get("intruder", False)
    log_action("🚨" if intruder else "✅", f"Intruder: {'DETECTED!' if intruder else 'All safe'}")
    return jsonify({"message": "⚠️ Intruder Detected!" if intruder else "All safe"})

@app.route("/motion_light", methods=["POST"])
def motion_light():
    data = request.get_json() or {}
    room = data.get("room", "living")
    motion = data.get("motion", False)
    log_action("👁️", f"[{room.title()}] Motion light: {'ON' if motion else 'OFF'}")
    return jsonify({"status": "ON" if motion else "OFF"})

@app.route("/detect_smoke", methods=["POST"])
def detect_smoke():
    detected = (request.get_json() or {}).get("smoke", False)
    log_action("🔥" if detected else "✅", f"[Kitchen] Smoke: {'DETECTED!' if detected else 'No smoke'}")
    return jsonify({"message": "🔥 Smoke detected!" if detected else "No smoke detected"})

@app.route("/set_schedule", methods=["POST"])
def set_schedule():
    data = request.get_json() or {}
    room     = data.get("room", "living")
    on_time  = data.get("on", "")
    off_time = data.get("off", "")
    device   = data.get("device", "light")

    if not on_time and not off_time:
        return jsonify({"message": "No times provided"})

    # Purani same room+device schedule hata do
    schedules[:] = [s for s in schedules
                    if not (s["room"] == room and s["device"] == device)]
    # Naya schedule add karo
    schedules.append({
        "room": room,
        "device": device,
        "on_time": on_time,
        "off_time": off_time
    })
    log_action("⏰", f"[{room.title()}] {device.title()} schedule saved: ON {on_time}, OFF {off_time}")
    return jsonify({"message": f"{device.title()}: ON at {on_time}, OFF at {off_time}"})

@app.route("/daylight", methods=["POST"])
def daylight():
    data = request.get_json() or {}
    room = data.get("room", "living")
    dark = data.get("dark", False)
    log_action("🌙", f"[{room.title()}] Day/Night: {'ON' if dark else 'OFF'}")
    return jsonify({"status": "ON" if dark else "OFF"})

@app.route("/room_occupancy", methods=["POST"])
def room_occupancy():
    data = request.get_json() or {}
    room = data.get("room", "living")
    occupied = data.get("occupied", False)
    log_action("🏠", f"[{room.title()}] {'Occupied' if occupied else 'Empty'}")
    return jsonify({"message": "Room is occupied" if occupied else "Room is empty"})

@app.route("/voice_feedback", methods=["POST"])
def voice_feedback():
    text = (request.get_json() or {}).get("text", "")
    log_action("🔊", f"Voice: '{text}'")
    return jsonify({"message": f"Speaking: {text}"})

@app.route("/water_level", methods=["POST"])
def water_level():
    level = (request.get_json() or {}).get("level", 0)
    log_action("💧", f"Water level: {level}%{' — Pump OFF' if level >= 90 else ''}")
    return jsonify({"message": f"Water Level: {level}%{' (Auto OFF Pump)' if level >= 90 else ''}"})

@app.route("/energy_usage", methods=["GET"])
def energy_usage():
    import random
    usage = round(random.uniform(100, 500), 2)
    log_action("📊", f"Energy usage checked: {usage}W")
    return jsonify({"usage": usage})

@app.route("/facial_recognition", methods=["POST"])
def facial_recognition():
    return jsonify({"status": "Use /face/recognize for real face recognition"})

# ══════════════════════════════════════════════════════
# FACE RECOGNITION SYSTEM
# ══════════════════════════════════════════════════════
try:
    from face_engine import (capture_faces, train_model, recognize_face,
                             load_profiles, save_profile, list_registered_users,
                             delete_user, DEFAULT_PREFS)
    FACE_ENGINE_AVAILABLE = True
except ImportError:
    FACE_ENGINE_AVAILABLE = False

face_task_status = {"status": "idle", "message": ""}

@app.route("/face/users", methods=["GET"])
def face_users():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"error": "Face engine not available"})
    users    = list_registered_users()
    raw_profs = load_profiles()
    # Merge each profile with DEFAULT_PREFS so missing keys show up
    merged = {}
    for u in users:
        base = DEFAULT_PREFS.copy()
        base.update(raw_profs.get(u, {}))
        merged[u] = base
    return jsonify({"users": users, "profiles": merged})

@app.route("/face/register", methods=["POST"])
def face_register():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"success": False, "message": "Face engine not available"})
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "Name required"})
    face_task_status["status"] = "registering"
    face_task_status["message"] = f"Registering {name}..."

    def do_register():
        ok, msg = capture_faces(name, num_samples=30)
        if ok:
            ok2, msg2 = train_model()
            face_task_status["status"] = "done"
            face_task_status["message"] = f"{msg} | {msg2}"
            log_action("👤", f"Face registered: {name}")
        else:
            face_task_status["status"] = "error"
            face_task_status["message"] = msg
        socketio.emit("face_task", face_task_status)

    threading.Thread(target=do_register, daemon=True).start()
    return jsonify({"success": True, "message": f"Registration started for {name}. Camera will open."})

@app.route("/face/recognize", methods=["POST"])
def face_recognize():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"success": False, "message": "Face engine not available"})
    face_task_status["status"] = "recognizing"
    face_task_status["message"] = "Scanning face..."

    def do_recognize():
        face_result = recognize_face(confidence_threshold=60)
        face_task_status["status"] = "done"
        face_task_status["message"] = face_result.get("message", "")
        socketio.emit("face_task", face_task_status)

        if face_result["success"]:
            name    = face_result["name"]
            profile = face_result["profile"]
            conf    = face_result.get("confidence", 0)

            # Apply room settings
            rooms["living"]["light"]     = profile.get("light", True)
            rooms["living"]["fan_speed"] = profile.get("fan_speed", 2)
            rooms["living"]["dimmer"]    = profile.get("dimmer", 70)
            rooms["living"]["curtain"]   = profile.get("curtain", False)
            rooms["living"]["ac"]        = profile.get("ac", False)
            persist()
            emit_update()

            # Auto-play music ONLY if palm was open
            music_query = profile.get("music", "")
            play_music  = face_result.get("play_music", False)
            if music_query and play_music and MUSIC_AVAILABLE:
                music_play(music_query)
                log_action("🎵", f"[{name}] 🖐 Palm open → Auto-playing: {music_query}")
                socketio.emit("music_update", music_status())
            elif music_query and not play_music:
                log_action("🤫", f"[{name}] Fist detected — skipping music")

            log_action("✅", f"[Face] {name} recognized ({conf}%) — room adjusted")
            socketio.emit("face_recognized", {
                "name":       name,
                "confidence": conf,
                "profile":    profile,
                "play_music": play_music,
                "message":    face_result.get("message", "")
            })
        else:
            log_action("❌", "[Face] Not recognized")
            socketio.emit("face_recognized", {
                "name": "Unknown", "confidence": 0,
                "message": face_result.get("message", "Not recognized")
            })

    threading.Thread(target=do_recognize, daemon=True).start()
    return jsonify({"success": True, "message": "Recognition started. Camera will open."})

@app.route("/face/train", methods=["POST"])
def face_train():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"success": False, "message": "Face engine not available"})
    ok, msg = train_model()
    if ok:
        log_action("🧠", f"Face model trained: {msg}")
    return jsonify({"success": ok, "message": msg})

@app.route("/face/profile", methods=["GET", "POST"])
def face_profile():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"error": "Face engine not available"})
    if request.method == "GET":
        name = request.args.get("name", "")
        return jsonify(load_profiles().get(name, DEFAULT_PREFS.copy()))
    data  = request.get_json() or {}
    name  = data.get("name", "")
    prefs = data.get("prefs", {})
    if not name:
        return jsonify({"success": False, "message": "Name required"})
    save_profile(name, prefs)
    log_action("✏️", f"Profile updated for {name}")
    return jsonify({"success": True, "message": f"Profile saved for {name}"})

@app.route("/face/delete", methods=["POST"])
def face_delete():
    if not FACE_ENGINE_AVAILABLE:
        return jsonify({"success": False, "message": "Face engine not available"})
    data = request.get_json() or {}
    name = data.get("name", "")
    if not name:
        return jsonify({"success": False, "message": "Name required"})
    delete_user(name)
    log_action("🗑️", f"Face data deleted for {name}")
    return jsonify({"success": True, "message": f"{name} deleted"})

@app.route("/face/status", methods=["GET"])
def face_status_route():
    return jsonify(face_task_status)

@app.route("/fire_alert", methods=["POST"])
def fire_alert():
    log_action("🔥", "[Kitchen] FIRE ALERT — Buzzer ON!")
    return jsonify({"message": "🔥 Fire detected! Buzzer ON!"})

@app.route("/detect_rain", methods=["POST"])
def detect_rain():
    log_action("🌧️", "Rain detected — window closed")
    return jsonify({"message": "🌧️ Rain detected! Window Closed."})

@app.route("/feed_pet", methods=["POST"])
def feed_pet():
    from datetime import datetime
    t = datetime.now().strftime("%I:%M:%S %p")
    log_action("🐶", f"Pet fed at {t}")
    return jsonify({"message": f"🐶 Pet fed at {t}"})

@app.route("/check_inverter_status", methods=["POST"])
def check_inverter_status():
    data = request.get_json() or {}
    room = data.get("room", "living")
    battery = data.get("battery", 0)
    if battery > 50:
        msg = "✅ All appliances will operate on inverter power."
    elif 10 < battery <= 50:
        msg = "⚠️ Only essential appliances will be powered (Fan, Light, Router)."
    else:
        msg = "🔴 Low battery! Only Wi-Fi, 1–2 Lights & Charging Point will remain ON."
    log_action("🔋", f"[{room.title()}] Battery {battery}%")
    return jsonify({"message": msg})

@app.route("/set_pet_feeder_automation", methods=["POST"])
def set_pet_feeder_automation():
    data = request.get_json() or {}
    t = data.get("time")
    delay = data.get("delay")
    log_action("🐾", f"Pet feeder scheduled at {t}, delay {delay} min")
    return jsonify({"message": f"Scheduled feeding at {t}, auto-feed after {delay} min if missed."})

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    users = load_users()
    if email in users:
        return jsonify({"success": False, "message": "Email already registered."})
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    users[email] = {"password": hashed, "name": name}
    save_users(users)
    return jsonify({"success": True, "message": "Signup successful!"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    users = load_users()

    if email in users and bcrypt.checkpw(password.encode("utf-8"), users[email]["password"].encode("utf-8")):
        session["user"] = users[email]["name"]
        return jsonify({"success": True, "message": f"Welcome {users[email]['name']}!"})
    else:
        return jsonify({"success": False, "message": "Invalid email or password."})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/loginpage")


# ══════════════════════════════════════════════════════
# MUSIC ROUTES — music_engine.py use karta hai
# ══════════════════════════════════════════════════════

@app.route("/music/play", methods=["POST"])
def music_play_route():
    if not MUSIC_AVAILABLE:
        return jsonify({"success": False, "message": "Music engine not available"})
    data  = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "message": "Query required"})
    result = music_play(query)
    log_action("🎵", f"Playing: {query}")
    socketio.emit("music_update", music_status())
    return jsonify(result)

@app.route("/music/pause", methods=["POST"])
def music_pause_route():
    if not MUSIC_AVAILABLE:
        return jsonify({"success": False})
    result = pause_resume()
    socketio.emit("music_update", music_status())
    return jsonify(result)

@app.route("/music/stop", methods=["POST"])
def music_stop_route():
    if not MUSIC_AVAILABLE:
        return jsonify({"success": False})
    result = music_stop()
    log_action("⏹️", "Music stopped")
    socketio.emit("music_update", music_status())
    return jsonify(result)

@app.route("/music/volume", methods=["POST"])
def music_volume_route():
    if not MUSIC_AVAILABLE:
        return jsonify({"success": False})
    data = request.get_json() or {}
    vol  = data.get("volume", 0.7)
    return jsonify(set_volume(vol))

@app.route("/music/status", methods=["GET"])
def music_status_route():
    if not MUSIC_AVAILABLE:
        return jsonify({"status": "unavailable", "title": ""})
    return jsonify(music_status())


if __name__ == "__main__":
    try:
        from pyngrok import ngrok
        public_url = ngrok.connect(5000)
        print("\n" + "="*50)
        print(f"  🌐 HTTPS URL: {public_url}")
        print(f"  📱 Phone pe yeh URL kholo voice ke liye!")
        print("="*50 + "\n")
    except Exception as e:
        print(f"  ⚠️  Ngrok nahi chala: {e}")

    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)


# Path cd "d:\SHA All about\VS_CODE\SmartHomeIoT\FrontEnd"
# python app.py



# import json
# import os

# from flask import Flask, request, jsonify, render_template, redirect, url_for, session
# from flask_cors import CORS

# # Flask app pointing to correct template/static folder
# app = Flask(__name__, template_folder="templates", static_folder="static")
# app.secret_key = "mysecret"   # Secret key for session management
# CORS(app)

# # Home route - serves index.html
# @app.route("/")
# def home():
#     if "user" not in session:
#         return redirect(url_for("login_page"))  # Not logged in → go to login page
#     return render_template("index.html", username=session["user"])  # Logged in → show home


# # Login Page
# @app.route("/loginpage")
# def login_page():
#     return render_template("login.html")

# # ---------- User DB Management ----------
# USER_FILE = "users.json"

# def load_users():
#     if not os.path.exists(USER_FILE):
#         return {}
#     with open(USER_FILE, "r") as file:
#         return json.load(file)

# def save_users(users):
#     with open(USER_FILE, "w") as file:
#         json.dump(users, file, indent=2)

# # ---------- Smart Home State & Endpoints ----------
# light_status = "off"
# fan_speed = 0  # New variable: 0 (Off) to 3 (High)
# temperature_val = None

# # Toggle Light
# @app.route("/toggle_light", methods=["POST"])
# def toggle_light():
#     global light_status
#     if light_status == "off":
#         light_status = "on"
#     else:
#         light_status = "off"
#     return jsonify({"status": light_status, "message": f"Light is {light_status.upper()}"})

# # Set Fan Speed
# @app.route("/set_fan_speed", methods=["POST"])
# def set_fan_speed_endpoint():
#     global fan_speed  # Use the global variable
#     data = request.get_json()
#     new_speed = data.get("speed")
    
#     # Logic: If speed is provided, set it, otherwise return current speed.
#     if new_speed is not None:
#         # Ensure speed is between 0 and 3
#         fan_speed = max(0, min(3, new_speed))
#         return jsonify({"message": f"Fan speed set to {fan_speed}", "speed": fan_speed})
#     else:
#         return jsonify({"message": f"Current fan speed is {fan_speed}", "speed": fan_speed})

# # Check Temperature
# @app.route("/check_temperature", methods=["POST"])
# def check_temperature():
#     global temperature_val
#     data = request.get_json()
#     temp = data.get("temperature")
    
#     # Simple threshold logic for demonstration
#     if temp is not None:
#         temperature_val = temp
#         if temp > 30:
#             message = "⚠️ It's getting hot. Consider turning on the AC or fan."
#         elif temp < 15:
#             message = "🥶 It's quite cold. Consider a heater."
#         else:
#             message = "The room temperature is comfortable."
#         return jsonify({"message": message})
#     return jsonify({"message": "Please provide a temperature value."})

# # Get Room Status (returns all tracked state)
# @app.route("/get_room_status", methods=["GET"])
# def get_room_status():
#     return jsonify({
#         "light": light_status,
#         "fan_speed": fan_speed,
#         "temperature": temperature_val if temperature_val is not None else "N/A"
#     })

# # Check Inverter Status
# @app.route("/check_inverter_status", methods=["POST"])
# def check_inverter_status():
#     data = request.get_json()
#     battery = data.get("battery")
#     if battery is None:
#         return jsonify({"message": "Battery level is required."})

#     battery = int(battery)
    
#     if battery > 80:
#         message = "🟢 Battery is fully charged and ready."
#     elif battery > 20:
#         message = "🟡 Battery level is adequate. Keep charging."
#     else:
#         message = "🔴 Warning! Battery is low, charge immediately."
#     return jsonify({"message": message})

# # Set Pet Feeder Automation
# @app.route("/set_pet_feeder_automation", methods=["POST"])
# def set_pet_feeder_automation():
#     data = request.get_json()
#     feed_time = data.get("time")
#     delay = data.get("delay")
#     return jsonify({"message": f"Scheduled feeding at {feed_time}, auto-feed after {delay} min if missed."})

# # ---------- Authentication Endpoints ----------
# @app.route("/signup", methods=["POST"])
# def signup():
#     data = request.get_json()
#     email = data.get("email")
#     password = data.get("password")
#     name = data.get("name")
#     users = load_users()
#     if email in users:
#         return jsonify({"success": False, "message": "Email already registered."})
#     users[email] = {"password": password, "name": name}
#     save_users(users)
#     return jsonify({"success": True, "message": "Signup successful! Please log in."})

# @app.route("/login", methods=["POST"])
# def login():
#     data = request.get_json()
#     email = data.get("email")
#     password = data.get("password")
#     users = load_users()

#     if email in users and users[email]["password"] == password:
#         # Set session variable for user authentication
#         session["user"] = users[email]["name"]
#         return jsonify({"success": True, "message": f"Welcome {users[email]['name']}!"})
#     else:
#         return jsonify({"success": False, "message": "Invalid email or password."})

# @app.route("/logout")
# def logout():
#     session.pop("user", None)  # Remove user from session
#     return redirect(url_for("login_page"))

# if __name__ == "__main__":
#     app.run(debug=True)