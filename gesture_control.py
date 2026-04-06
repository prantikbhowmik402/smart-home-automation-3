
# ####### (Light and Fan on off Control) ########


import cv2
import mediapipe as mp
import requests
import time

print("Starting Advanced Gesture Control...")

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Initialize MediaPipe
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
cap = cv2.VideoCapture(0)

# Variables
prev_state = "neutral"  
current_fan_speed = 0   # Track speed locally (0 to 5)
last_action_time = 0    
COOLDOWN = 1.0          # 1 second gap between commands

# --- Detection Functions ---

def get_hand_state(landmarks):
    """
    Recognizes: 'open', 'fist', 'thumbs_up', 'thumbs_down', 'neutral'
    """
    # Finger IDs: Thumb=4, Index=8, Middle=12, Ring=16, Pinky=20
    # PIP Joints (Middle joint): 6, 10, 14, 18
    
    # 1. Check if 4 fingers (Index to Pinky) are closed
    fingers_closed = 0
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    
    for i in range(4):
        if landmarks[tips[i]].y > landmarks[pips[i]].y: 
            fingers_closed += 1
            
    # 2. Check Thumb Status
    # Thumb Tip (4), IP Joint (3), MCP Joint (2)
    thumb_tip_y = landmarks[4].y
    index_base_y = landmarks[5].y  # Index MCP
    pinky_base_y = landmarks[17].y # Pinky MCP
    
    # LOGIC DECISION TREE
    
    # Agar chaaro ungliyan band hain (Likely Fist or Thumbs Up/Down)
    if fingers_closed >= 4:
        # Check Thumbs Up: Thumb tip is ABOVE Index Base (Y is smaller)
        if thumb_tip_y < index_base_y - 0.05: # Thoda threshold diya
            return "thumbs_up"
        
        # Check Thumbs Down: Thumb tip is BELOW Pinky Base (Y is larger)
        elif thumb_tip_y > pinky_base_y + 0.05:
            return "thumbs_down"
            
        # Agar thumb na upar hai na neeche, toh FIST hai
        else:
            return "fist"

    # Agar koi bhi finger band nahi hai -> Open Hand
    elif fingers_closed == 0:
        return "open"
        
    else:
        return "neutral" # Transition state

# --- Main Loop ---

if not cap.isOpened():
    print("❌ Camera not detected.")
else:
    print("✅ System Ready.")
    print("   🖐  Open Hand  -> Light Toggle")
    print("   ✊ Closed Fist -> Fan ON/OFF")
    print("   👍 Thumbs Up   -> Speed +1")
    print("   👎 Thumbs Down -> Speed -1")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb_frame)

        current_state = "neutral"

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

                landmarks = hand_landmarks.landmark
                current_state = get_hand_state(landmarks)

        # --- ACTION LOGIC (Only triggers when coming from NEUTRAL) ---
        
        if time.time() - last_action_time > COOLDOWN:
            
            # Action tabhi lo jab previous state 'neutral' tha
            if prev_state == "neutral" and current_state != "neutral":
                
                # 1. LIGHT (Open Hand)
                if current_state == "open":
                    try:
                        requests.post("http://127.0.0.1:5000/toggle_light")
                        print("✅ Light Toggled")
                        last_action_time = time.time()
                    except: pass

                # 2. FAN ON/OFF (Fist)
                elif current_state == "fist":
                    try:
                        # Agar chalu hai to band (0), band hai to ON (3)
                        new_speed = 0 if current_fan_speed > 0 else 3
                        requests.post("http://127.0.0.1:5000/set_fan_speed", json={"speed": new_speed})
                        current_fan_speed = new_speed
                        print(f"✅ Fan Toggled: {current_fan_speed}")
                        last_action_time = time.time()
                    except: pass

                # 3. SPEED UP (Thumbs Up)
                elif current_state == "thumbs_up":
                    try:
                        # Max speed 5 tak badhao
                        new_speed = min(5, current_fan_speed + 1)
                        if new_speed != current_fan_speed:
                            requests.post("http://127.0.0.1:5000/set_fan_speed", json={"speed": new_speed})
                            current_fan_speed = new_speed
                            print(f"✅ Speed Increased: {current_fan_speed}")
                        else:
                            print("⚠️ Max Speed Reached")
                        last_action_time = time.time()
                    except: pass

                # 4. SPEED DOWN (Thumbs Down)
                elif current_state == "thumbs_down":
                    try:
                        # Min speed 0 tak ghatao
                        new_speed = max(0, current_fan_speed - 1)
                        if new_speed != current_fan_speed:
                            requests.post("http://127.0.0.1:5000/set_fan_speed", json={"speed": new_speed})
                            current_fan_speed = new_speed
                            print(f"✅ Speed Decreased: {current_fan_speed}")
                        else:
                            print("⚠️ Fan is OFF")
                        last_action_time = time.time()
                    except: pass

        # Update State
        if not result.multi_hand_landmarks:
            prev_state = "neutral"
        else:
            prev_state = current_state

        # UI Overlay
        color = (0, 255, 0) if current_state == "neutral" else (0, 165, 255)
        cv2.putText(frame, f"Gesture: {current_state.upper()}", (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"Fan Speed: {current_fan_speed}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow("Gesture Control", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
















