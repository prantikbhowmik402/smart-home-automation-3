"""
face_engine.py — Smart Home Face Recognition Engine
Uses OpenCV LBPH Face Recognizer (no dlib needed)
"""

import cv2
import os
import json
import numpy as np

# ── Paths ──────────────────────────────────────────────
BASE_DIR      = os.path.join(os.path.dirname(__file__), "face_data")
DATASET_DIR   = os.path.join(BASE_DIR, "dataset")
MODEL_PATH    = os.path.join(BASE_DIR, "model.yml")
PROFILES_PATH = os.path.join(BASE_DIR, "profiles.json")

os.makedirs(DATASET_DIR, exist_ok=True)

# ── Face detector ───────────────────────────────────────
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade  = cv2.CascadeClassifier(_CASCADE_PATH)

# ── Default profile preferences ────────────────────────
DEFAULT_PREFS = {
    "light":     True,
    "fan_speed": 2,
    "dimmer":    70,
    "curtain":   False,
    "ac":        False,
    "inverter":  False,
    "music":     "",
    "greeting":  "Welcome home!"
}

# ══════════════════════════════════════════════════════
# PROFILES
# ══════════════════════════════════════════════════════

def load_profiles():
    if not os.path.exists(PROFILES_PATH):
        return {}
    with open(PROFILES_PATH) as f:
        return json.load(f)

def save_profiles(profiles):
    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)

def get_profile(name):
    profiles = load_profiles()
    saved    = profiles.get(name, {})
    merged   = DEFAULT_PREFS.copy()
    merged.update(saved)
    return merged

def save_profile(name, prefs):
    profiles = load_profiles()
    profiles[name] = prefs
    save_profiles(profiles)

def list_registered_users():
    if not os.path.exists(DATASET_DIR):
        return []
    return [d for d in os.listdir(DATASET_DIR)
            if os.path.isdir(os.path.join(DATASET_DIR, d))]

# ══════════════════════════════════════════════════════
# REGISTRATION
# ══════════════════════════════════════════════════════

def capture_faces(name, num_samples=50):
    user_dir = os.path.join(DATASET_DIR, name)
    os.makedirs(user_dir, exist_ok=True)

    # Purane images delete karo — fresh start
    for f in os.listdir(user_dir):
        os.remove(os.path.join(user_dir, f))

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Camera not found"

    count = 0

    while count < num_samples:
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_eq  = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
        )

        for (x, y, w, h) in faces:
            face_crop = gray[y:y+h, x:x+w]
            face_eq   = cv2.equalizeHist(face_crop)
            face_img  = cv2.resize(face_eq, (200, 200))

            # Original
            cv2.imwrite(os.path.join(user_dir, f"{count+1}.jpg"), face_img)
            count += 1

            # Brighter variant
            if count < num_samples:
                bright = cv2.convertScaleAbs(face_img, alpha=1.2, beta=15)
                cv2.imwrite(os.path.join(user_dir, f"{count+1}.jpg"), bright)
                count += 1

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Capturing: {count}/{num_samples}",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.putText(frame, "Move head slowly left/right",
                        (10, frame.shape[0]-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        if len(faces) == 0:
            cv2.putText(frame, "No face — come closer / more light",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

        cv2.imshow(f"Registering: {name}", frame)
        cv2.waitKey(80)

    cap.release()
    cv2.destroyAllWindows()

    if count < 10:
        return False, f"Only {count} samples. Need 10+. Try better lighting."

    if name not in load_profiles():
        save_profile(name, DEFAULT_PREFS.copy())

    return True, f"Captured {count} samples for {name}"


# ══════════════════════════════════════════════════════
# TRAINING
# ══════════════════════════════════════════════════════

def train_model():
    users = list_registered_users()
    if not users:
        return False, "No registered users found"

    faces     = []
    labels    = []
    label_map = {}

    for idx, name in enumerate(users):
        label_map[idx] = name
        user_dir = os.path.join(DATASET_DIR, name)
        for img_file in os.listdir(user_dir):
            img_path = os.path.join(user_dir, img_file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img = cv2.resize(img, (200, 200))
                faces.append(img)
                labels.append(idx)

    if len(faces) < 2:
        return False, "Need at least 2 face images total to train"

    # LBPH with tuned params
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=2, neighbors=8, grid_x=8, grid_y=8
    )
    recognizer.train(faces, np.array(labels))
    recognizer.save(MODEL_PATH)

    label_map_path = os.path.join(BASE_DIR, "label_map.json")
    with open(label_map_path, "w") as f:
        json.dump(label_map, f)

    return True, f"Model trained on {len(users)} user(s): {', '.join(users)}"


# ══════════════════════════════════════════════════════
# PALM DETECTION HELPER
# ══════════════════════════════════════════════════════

def _is_palm_open(landmarks):
    """
    Better palm detection — multiple methods combined.
    Returns True if hand is open.
    """
    lm = landmarks  # shorthand

    # Method 1: Finger tip vs MCP (base joint) — more reliable than PIP
    # Tips:  4(thumb), 8(index), 12(middle), 16(ring), 20(pinky)
    # MCPs:  2(thumb), 5(index), 9(middle), 13(ring), 17(pinky)
    tips = [8, 12, 16, 20]
    mcps = [5,  9, 13, 17]

    wrist_y = lm[0].y

    extended_count = 0
    for tip, mcp in zip(tips, mcps):
        # Tip should be above MCP (smaller y = higher on screen)
        if lm[tip].y < lm[mcp].y:
            extended_count += 1

    # Method 2: Spread fingers — distance between index and pinky tips
    # Open palm = fingers spread apart
    index_tip  = lm[8]
    pinky_tip  = lm[20]
    spread = abs(index_tip.x - pinky_tip.x)

    # Method 3: Hand size vs tip distance
    # Wrist to middle finger tip distance
    wrist  = lm[0]
    middle = lm[12]
    hand_size = ((wrist.x - middle.x)**2 + (wrist.y - middle.y)**2) ** 0.5

    # Open palm conditions — any 2 of 3 methods
    cond1 = extended_count >= 3          # 3+ fingers extended
    cond2 = spread > 0.15                # fingers spread wide
    cond3 = hand_size > 0.25             # hand stretched out

    return (cond1 and cond2) or (cond1 and cond3) or extended_count >= 4


# ══════════════════════════════════════════════════════
# RECOGNITION
# ══════════════════════════════════════════════════════

def recognize_face(confidence_threshold=40):
    """
    Opens webcam — recognizes face AND checks palm.
    Returns dict: success, name, confidence, profile, play_music, message
    """
    if not os.path.exists(MODEL_PATH):
        return {"success": False, "name": "Unknown", "confidence": 0,
                "play_music": False, "message": "Model not trained yet. Please register first."}

    label_map_path = os.path.join(BASE_DIR, "label_map.json")
    if not os.path.exists(label_map_path):
        return {"success": False, "name": "Unknown", "confidence": 0,
                "play_music": False, "message": "Label map missing — please re-register"}

    with open(label_map_path) as f:
        label_map = {int(k): v for k, v in json.load(f).items()}

    # Load recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=2, neighbors=8, grid_x=8, grid_y=8
    )
    recognizer.read(MODEL_PATH)

    # MediaPipe for palm
    try:
        import mediapipe as mp
        mp_hands  = mp.solutions.hands
        hands_det = mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )
        USE_MP = True
    except ImportError:
        USE_MP    = False
        hands_det = None

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return {"success": False, "name": "Unknown", "confidence": 0,
                "play_music": False, "message": "Camera not found"}

    result       = {"success": False, "name": "Unknown",
                    "confidence": 0, "play_music": False}
    attempts     = 0
    max_attempts = 80
    palm_frames  = 0

    while attempts < max_attempts:
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_eq  = cv2.equalizeHist(gray)
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ── Face detection ─────────────────────────────
        faces = face_cascade.detectMultiScale(
            gray_eq, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80)
        )

        for (x, y, w, h) in faces:
            face_crop = gray[y:y+h, x:x+w]
            face_eq   = cv2.equalizeHist(face_crop)
            face_img  = cv2.resize(face_eq, (200, 200))

            lid, conf = recognizer.predict(face_img)
            match_pct = max(0, 100 - conf)
            name      = label_map.get(lid, "Unknown")

            color = (0, 255, 0) if match_pct >= confidence_threshold else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, f"{name} ({match_pct:.0f}%)",
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            if match_pct >= confidence_threshold and not result["success"]:
                result.update({
                    "success":    True,
                    "name":       name,
                    "confidence": round(match_pct, 1),
                    "profile":    get_profile(name),
                    "message":    f"Welcome, {name}! ({match_pct:.0f}% match)"
                })

        # ── Palm detection ─────────────────────────────
        palm_open_now = False
        if USE_MP:
            hr = hands_det.process(rgb)
            if hr.multi_hand_landmarks:
                for hl in hr.multi_hand_landmarks:
                    if _is_palm_open(hl.landmark):
                        palm_frames  += 1
                        palm_open_now = True

        # ── Overlay ────────────────────────────────────
        palm_txt   = "🖐 OPEN — Music ON"  if palm_open_now else "✊ CLOSED — No music"
        palm_color = (0, 255, 150)          if palm_open_now else (100, 100, 255)
        cv2.putText(frame, palm_txt, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, palm_color, 2)
        cv2.putText(frame, f"Palm frames: {palm_frames}",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 0), 1)
        cv2.putText(frame, "Open palm = music  |  Fist = no music",
                    (10, frame.shape[0]-12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Smart Home — Face + Palm", frame)
        cv2.waitKey(100)
        attempts += 1

        if result["success"] and attempts >= (max_attempts - 60):
            break

    cap.release()
    cv2.destroyAllWindows()
    if USE_MP and hands_det:
        hands_det.close()

    if result["success"]:
        result["play_music"] = palm_frames >= 3
        suffix = " 🎵 Palm open — music will play!" if result["play_music"] \
                 else " 🤫 Fist — no music."
        result["message"] += suffix
    else:
        result["message"] = "Face not recognized. Try better lighting or re-register."

    return result


# ══════════════════════════════════════════════════════
# DELETE user
# ══════════════════════════════════════════════════════

def delete_user(name):
    import shutil
    user_dir = os.path.join(DATASET_DIR, name)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    profiles = load_profiles()
    profiles.pop(name, None)
    save_profiles(profiles)
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
    label_map_path = os.path.join(BASE_DIR, "label_map.json")
    if os.path.exists(label_map_path):
        os.remove(label_map_path)
    return True