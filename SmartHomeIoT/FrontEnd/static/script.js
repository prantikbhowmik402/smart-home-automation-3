let curtainStates = { living: false, bedroom: false, kitchen: false };

// ----------------------------------------
// Activity Log
// ----------------------------------------
function loadLog() {
  fetch('/get_log')
    .then(res => res.json())
    .then(entries => {
      const box = document.getElementById('activity-log');
      if (!box) return;
      if (entries.length === 0) {
        box.innerHTML = '<p style="color:var(--label-color); font-size:13px; text-align:center; padding:20px 0;">No activity yet. Start using the dashboard!</p>';
        return;
      }
      box.innerHTML = entries.map(e => `
        <div style="display:flex; align-items:center; gap:10px; padding:7px 10px; border-radius:8px; background:var(--input-bg); border:1px solid var(--card-border); font-size:13px;">
          <span style="font-size:16px;">${e.icon}</span>
          <span style="color:var(--body-color); flex:1;">${e.message}</span>
          <span style="color:var(--label-color); white-space:nowrap;">${e.time}</span>
        </div>`).join('');
    });
}

function clearLog() {
  fetch('/clear_log', { method: 'POST' }).then(() => loadLog());
}

// ----------------------------------------
// Toggle Light
// ----------------------------------------
function toggleLight(room = 'living') {
  fetch("/toggle_light", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room })
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-light-status`);
      if (el) el.textContent = `Light is ${data.status.toUpperCase()}`;
      loadLog();
    });
}

// ----------------------------------------
// Fan Speed
// ----------------------------------------
function setFanSpeed(speed, room = 'living') {
  fetch("/set_fan_speed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed: parseInt(speed), room }),
  })
    .then(res => res.json())
    .then(() => {
      const el = document.getElementById(`${room}-fan-status`);
      if (el) el.textContent = `Fan speed: ${speed}`;
      loadLog();
    });
}

// ----------------------------------------
// Temperature
// ----------------------------------------
function checkTemperature(room = 'living') {
  const temp = document.getElementById(`${room}-tempInput`).value;
  fetch("/check_temperature", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temperature: parseFloat(temp), room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-temp-message`);
      if (el) el.textContent = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Gas Leak
// ----------------------------------------
function detectGas() {
  const leak = Math.random() < 0.5;
  fetch("/detect_gas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ leak }),
  })
    .then(res => res.json())
    .then(() => {
      document.getElementById("gas-status").innerText = leak ? "⚠️ Gas Leak Detected!" : "All clear";
      loadLog();
    });
}

// ----------------------------------------
// Door Lock
// ----------------------------------------
function unlockDoor() {
  const password = document.getElementById("doorPassword").value;
  fetch("/unlock_door", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("lock-status").textContent =
        data.status === "success" ? "✅ Door Unlocked" : "❌ Incorrect Password";
      loadLog();
    });
}

// ----------------------------------------
// Plant Watering
// ----------------------------------------
function checkSoil(room = 'kitchen') {
  const dry = Math.random() < 0.5;
  const statusId = room === 'balcony' ? 'balcony-plant-status' : 'plant-status';
  fetch("/check_soil", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dry }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(statusId);
      if (el) el.innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Curtains
// ----------------------------------------
function toggleCurtain(room = 'living') {
  curtainStates[room] = !curtainStates[room];
  fetch("/toggle_curtain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ open: curtainStates[room], room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-curtain-status`);
      if (el) el.textContent = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Smart Bell
// ----------------------------------------
function ringBell() {
  fetch("/ring_bell", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("bell-status").innerText = data.message;
      loadLog();
      setTimeout(() => {
        document.getElementById("bell-status").innerText = "No visitor";
      }, 3000);
    });
}

// ----------------------------------------
// Auto Door
// ----------------------------------------
function approachDoor() {
  fetch("/approach_door", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("auto-door-status").innerText = data.message;
      loadLog();
      setTimeout(() => {
        document.getElementById("auto-door-status").innerText = "No one nearby";
      }, 4000);
    });
}

// ----------------------------------------
// Intruder
// ----------------------------------------
function detectIntruder() {
  const intruder = Math.random() < 0.3;
  fetch("/detect_intruder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intruder }),
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("intruder-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Dimmer
// ----------------------------------------
function updateDimmer(value, room = 'living') {
  const el = document.getElementById(`${room}-dimmer-status`);
  if (el) el.textContent = `Brightness: ${value}%`;
  fetch("/set_dimmer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brightness: parseInt(value), room }),
  }).then(res => res.json()).then(() => loadLog());
}

// ----------------------------------------
// Motion Light
// ----------------------------------------
function detectMotion(room = 'living') {
  fetch("/motion_light", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motion: true, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-motion-status`);
      if (el) el.textContent = `Motion detected! Light ${data.status}`;
      loadLog();
      setTimeout(() => { if (el) el.textContent = "Light is OFF"; }, 3000);
    });
}

// ----------------------------------------
// AC Toggle
// ----------------------------------------
function toggleAC(room = 'bedroom') {
  const btn = document.getElementById(`${room}-ac-btn`);
  const status = document.getElementById(`${room}-ac-status`);
  const isOn = status && status.textContent.includes('ON');
  const newState = !isOn;
  fetch("/toggle_ac", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newState, room }),
  })
    .then(res => res.json())
    .then(() => {
      if (btn) btn.textContent = newState ? '❄️ Turn AC OFF' : '❄️ Turn AC ON';
      if (status) status.textContent = `AC is ${newState ? 'ON' : 'OFF'}`;
      loadLog();
    });
}

// ----------------------------------------
// Inverter Toggle (single button)
// ----------------------------------------
function toggleInverter(room = 'bedroom') {
  const currentStatus = document.getElementById(`${room}-inverter-status`).textContent.includes('ON');
  const newStatus = !currentStatus;
  fetch("/inverter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newStatus, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-inverter-status`);
      if (el) el.textContent = data.message;
      const btn = document.getElementById(`${room}-inverter-btn`);
      if (btn) btn.textContent = newStatus ? '⚡ Turn Inverter OFF' : '⚡ Turn Inverter ON';
      loadLog();
    });
}

// ----------------------------------------
// Schedule (with device dropdown)
// ----------------------------------------
function setSchedule(room = 'living') {
  const deviceEl = document.getElementById(`${room}-scheduleDevice`);
  const device = deviceEl ? deviceEl.value : 'light';
  const deviceLabel = deviceEl ? deviceEl.options[deviceEl.selectedIndex].text : '💡 Light';
  const onTime  = document.getElementById(`${room}-onTime`).value;
  const offTime = document.getElementById(`${room}-offTime`).value;
  if (!onTime || !offTime) {
    const el = document.getElementById(`${room}-schedule-status`);
    if (el) el.textContent = "Please select both ON and OFF times!";
    return;
  }
  fetch("/set_schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ on: onTime, off: offTime, room, device }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-schedule-status`);
      if (el) el.textContent = `✅ ${data.message}`;
      loadLog();
      loadScheduleList(room);
    });
}

function loadScheduleList(room) {
  fetch("/get_schedules")
    .then(res => res.json())
    .then(all => {
      const mine = all.filter(s => s.room === room);
      const listEl = document.getElementById(`${room}-schedule-list`);
      if (!listEl) return;
      if (mine.length === 0) { listEl.innerHTML = ''; return; }
      listEl.innerHTML = '<div style="margin-top:6px; font-weight:600; color:var(--card-title-color);">Active schedules:</div>' +
        mine.map(s => `
          <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid var(--card-border);">
            <span>${s.device} → ON ${s.on_time} / OFF ${s.off_time}</span>
            <button onclick="deleteSchedule('${s.room}','${s.device}')" style="font-size:11px; padding:2px 8px; margin:0;">❌</button>
          </div>`).join('');
    });
}

function deleteSchedule(room, device) {
  fetch("/delete_schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room, device }),
  }).then(() => loadScheduleList(room));
}

// ----------------------------------------
// Day/Night Light
// ----------------------------------------
function checkDaylight(isDark, room = 'living') {
  fetch("/daylight", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dark: isDark, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-daylight-status`);
      if (el) el.textContent = `Light ${data.status}`;
      loadLog();
    });
}

// ----------------------------------------
// Room Occupancy
// ----------------------------------------
function roomOccupied(status, room = 'living') {
  fetch("/room_occupancy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ occupied: status, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-room-status`);
      if (el) el.textContent = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Inverter
// ----------------------------------------
function setInverter(status, room = 'living') {
  fetch("/inverter", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-inverter-status`);
      if (el) el.textContent = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Inverter Smart Power Control
// ----------------------------------------
function checkInverterStatus(room = 'living') {
  const battery = parseInt(document.getElementById(`${room}-batteryLevel`).value);
  fetch("/check_inverter_status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ battery, room }),
  })
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById(`${room}-inverterStatus`);
      if (el) el.textContent = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Gas Leak
// ----------------------------------------
function detectGas() {
  const leak = Math.random() < 0.5;
  fetch("/detect_gas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ leak }),
  })
    .then(res => res.json())
    .then(() => {
      document.getElementById("gas-status").innerText = leak ? "⚠️ Gas Leak Detected!" : "All clear";
      loadLog();
    });
}

// ----------------------------------------
// Smoke
// ----------------------------------------
function detectSmoke() {
  const detected = Math.random() < 0.5;
  fetch("/detect_smoke", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ smoke: detected }),
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("smoke-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Voice Feedback
// ----------------------------------------
function speakFeedback(text) {
  fetch("/voice_feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  }).then(res => res.json()).then(() => loadLog());
  const msg = new SpeechSynthesisUtterance(text);
  window.speechSynthesis.speak(msg);
}

// ----------------------------------------
// Water Level
// ----------------------------------------
function checkWaterLevel(value) {
  fetch("/water_level", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level: parseInt(value) }),
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("water-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Energy Usage
// ----------------------------------------
function showEnergyUsage() {
  fetch("/energy_usage")
    .then(res => res.json())
    .then(data => {
      document.getElementById("energy-status").innerText = `Usage: ${data.usage} Watts`;
      loadLog();
    });
}

// ----------------------------------------
// Face Recognition System
// ----------------------------------------

function faceShowTask(msg, visible = true) {
  const bar   = document.getElementById('face-task-bar');
  const msgEl = document.getElementById('face-task-msg');
  if (bar)   bar.style.display = visible ? 'block' : 'none';
  if (msgEl) msgEl.textContent = msg;
}

function faceRecognize() {
  faceShowTask('📷 Camera opening... Look at the camera!');
  const resultEl = document.getElementById('face-result');
  if (resultEl) resultEl.textContent = '';
  fetch('/face/recognize', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      if (!data.success) faceShowTask('❌ ' + data.message);
    });
}

function faceRegister() {
  const name = document.getElementById('face-reg-name').value.trim();
  if (!name) { alert('Please enter a name first!'); return; }
  faceShowTask(`📸 Camera opening for "${name}"... Look at the camera and move slowly left/right.`);
  fetch('/face/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  })
    .then(res => res.json())
    .then(data => {
      if (!data.success) faceShowTask('❌ ' + data.message);
    });
}

function faceLoadUsers() {
  fetch('/face/users')
    .then(res => res.json())
    .then(data => {
      const container = document.getElementById('face-users-list');
      if (!container) return;
      if (!data.users || data.users.length === 0) {
        container.innerHTML = '<p style="font-size:13px; color:var(--label-color);">No users registered yet. Register someone above!</p>';
        return;
      }
      container.innerHTML = data.users.map(name => {
        const p = data.profiles[name] || {};
        return `
        <div style="background:var(--input-bg); border:1px solid var(--card-border); border-radius:12px; padding:14px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="font-size:15px; font-weight:600; color:var(--card-title-color);">👤 ${name}</span>
            <button onclick="faceDeleteUser('${name}')" style="font-size:11px; padding:4px 10px; margin:0; background:linear-gradient(135deg,#c62828,#b71c1c);">🗑 Delete</button>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:13px;">
            <label style="margin:0; color:var(--label-color);">💡 Light
              <select onchange="faceUpdateProfile('${name}','light',this.value==='true')" style="margin:4px 0 0; padding:6px;">
                <option value="true"  ${p.light  ? 'selected':''}>ON</option>
                <option value="false" ${!p.light ? 'selected':''}>OFF</option>
              </select>
            </label>
            <label style="margin:0; color:var(--label-color);">🌀 Fan Speed
              <select onchange="faceUpdateProfile('${name}','fan_speed',parseInt(this.value))" style="margin:4px 0 0; padding:6px;">
                ${[0,1,2,3,4,5].map(v=>`<option value="${v}" ${p.fan_speed===v?'selected':''}>${v}</option>`).join('')}
              </select>
            </label>
            <label style="margin:0; color:var(--label-color);">🔆 Dimmer %
              <input type="number" min="0" max="100" value="${p.dimmer||70}"
                onchange="faceUpdateProfile('${name}','dimmer',parseInt(this.value))"
                style="margin:4px 0 0; padding:6px;">
            </label>
            <label style="margin:0; color:var(--label-color);">🪟 Curtain
              <select onchange="faceUpdateProfile('${name}','curtain',this.value==='true')" style="margin:4px 0 0; padding:6px;">
                <option value="false" ${!p.curtain ? 'selected':''}>Closed</option>
                <option value="true"  ${p.curtain  ? 'selected':''}>Open</option>
              </select>
            </label>
            <label style="margin:0; color:var(--label-color);">❄️ AC
              <select onchange="faceUpdateProfile('${name}','ac',this.value==='true')" style="margin:4px 0 0; padding:6px;">
                <option value="false" ${!p.ac ? 'selected':''}>OFF</option>
                <option value="true"  ${p.ac  ? 'selected':''}>ON</option>
              </select>
            </label>
            <label style="margin:0; color:var(--label-color);">💬 Greeting
              <input type="text" value="${p.greeting||'Welcome home!'}"
                onchange="faceUpdateProfile('${name}','greeting',this.value)"
                style="margin:4px 0 0; padding:6px;">
            </label>
          </div>
          <label style="margin:10px 0 0; color:var(--label-color); display:block;">
            🎵 Auto-play Music
            <small style="color:var(--label-color); font-size:11px;">(song name / artist — plays when you enter)</small>
            <input type="text" value="${p.music||''}"
              placeholder="e.g. Arijit Singh hits / Shape of You / lo-fi beats"
              onchange="faceUpdateProfile('${name}','music',this.value)"
              style="margin:4px 0 0; padding:8px; width:100%; border-radius:8px;">
          </label>
        </div>`;
      }).join('');
    });
}

const _profileCache = {};
function faceUpdateProfile(name, key, value) {
  if (!_profileCache[name]) _profileCache[name] = {};
  _profileCache[name][key] = value;
  clearTimeout(_profileCache[name]._timer);
  _profileCache[name]._timer = setTimeout(() => {
    fetch('/face/users')
      .then(r => r.json())
      .then(data => {
        const current = data.profiles[name] || {};
        const updated = { ...current, ..._profileCache[name] };
        delete updated._timer;
        fetch('/face/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, prefs: updated })
        }).then(() => loadLog());
      });
  }, 800);
}

function faceDeleteUser(name) {
  if (!confirm(`Delete ${name}'s face data and profile?`)) return;
  fetch('/face/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  })
    .then(() => { faceLoadUsers(); loadLog(); });
}

// ----------------------------------------
// Music Player — HTML5 Audio
// ----------------------------------------

function _playAudio(audioUrl, title) {
  const audio    = document.getElementById('music-audio');
  const titleEl  = document.getElementById('music-title');
  const statusEl = document.getElementById('music-status-text');
  if (!audio) return;

  audio.src   = audioUrl;
  audio.style.display = 'block';
  audio.load();
  audio.play()
    .then(() => {
      if (titleEl)  titleEl.textContent  = '▶ ' + title;
      if (statusEl) statusEl.textContent = 'playing';
    })
    .catch(err => {
      if (titleEl)  titleEl.textContent  = '⚠️ ' + title + ' (click play on player)';
      if (statusEl) statusEl.textContent = 'click play above';
      console.log('Autoplay blocked:', err);
    });

  audio.onended = () => {
    if (statusEl) statusEl.textContent = 'ended';
  };
}

function musicSearchAndPlay(query) {
  const titleEl  = document.getElementById('music-title');
  const statusEl = document.getElementById('music-status-text');
  if (titleEl)  titleEl.textContent  = `🔍 Searching: ${query}...`;
  if (statusEl) statusEl.textContent = 'Loading... (5-10 sec)';

  fetch('/music/play', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  })
    .then(r => r.json())
    .then(data => {
      if (!data.success) {
        if (titleEl)  titleEl.textContent  = '❌ Not found: ' + query;
        if (statusEl) statusEl.textContent = data.message || 'Error';
        return;
      }
      _playAudio(data.audio_url, data.title);
      loadLog();
    })
    .catch(() => {
      if (titleEl)  titleEl.textContent  = '❌ Network error';
      if (statusEl) statusEl.textContent = 'Error';
    });
}

function musicPlay() {
  const query = document.getElementById('music-search-input').value.trim();
  if (!query) { alert('Please enter a song name!'); return; }
  musicSearchAndPlay(query);
}

function musicStop() {
  const audio    = document.getElementById('music-audio');
  const titleEl  = document.getElementById('music-title');
  const statusEl = document.getElementById('music-status-text');
  if (audio) { audio.pause(); audio.src = ''; audio.style.display = 'none'; }
  if (titleEl)  titleEl.textContent  = 'No song playing';
  if (statusEl) statusEl.textContent = 'Stopped';
  loadLog();
}

function musicVolume(val) {
  const audio = document.getElementById('music-audio');
  if (audio) audio.volume = parseInt(val) / 100;
}

// ----------------------------------------
// Fire Alert
// ----------------------------------------
function fireAlert() {
  fetch("/fire_alert", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("fire-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Rain Detection
// ----------------------------------------
function detectRain() {
  fetch("/detect_rain", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("rain-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Pet Feeder
// ----------------------------------------
function feedPet() {
  fetch("/feed_pet", { method: "POST" })
    .then(res => res.json())
    .then(data => {
      document.getElementById("pet-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Pet Feeder Automation
// ----------------------------------------
function setPetFeederAutomation() {
  const feedTime = document.getElementById("feedTime").value;
  const graceDelay = parseInt(document.getElementById("graceDelay").value);
  if (!feedTime || isNaN(graceDelay)) {
    document.getElementById("pet-feeder-status").innerText = "❗ Please enter both feeding time and grace delay.";
    return;
  }
  fetch("/set_pet_feeder_automation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ time: feedTime, delay: graceDelay }),
  })
    .then(res => res.json())
    .then(data => {
      document.getElementById("pet-feeder-status").innerText = data.message;
      loadLog();
    });
}

// ----------------------------------------
// Search / Filter Cards
// ----------------------------------------
function filterCards() {
  const input = document.getElementById("searchInput").value.toLowerCase();
  const cards = document.querySelectorAll(".card");
  cards.forEach(card => {
    card.style.display = card.innerText.toLowerCase().includes(input) ? "block" : "none";
  });
}

// ----------------------------------------
// Voice Commands
// ----------------------------------------
let recognition = null;
let voiceActive = false;

// Speak response out loud
function voiceSpeak(text) {
  const msg = new SpeechSynthesisUtterance(text);
  msg.lang = "en-US";
  msg.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(msg);
  const statusEl = document.getElementById("voice-status");
  if (statusEl) statusEl.textContent = "🔊 " + text;
}

// Process the spoken command
function processVoiceCommand(transcript) {
  const cmd = transcript.toLowerCase().trim();
  const statusEl = document.getElementById("voice-status");
  if (statusEl) statusEl.textContent = `🎤 "${transcript}"`;

  // --- Light ---
  if (cmd.includes("turn on light") || cmd.includes("light on") || cmd.includes("lights on")) {
    toggleLight();
    voiceSpeak("Light turned on");

  } else if (cmd.includes("turn off light") || cmd.includes("light off") || cmd.includes("lights off")) {
    toggleLight();
    voiceSpeak("Light turned off");

  } else if (cmd.includes("toggle light")) {
    toggleLight();
    voiceSpeak("Light toggled");

  // --- Fan ---
  } else if (cmd.includes("fan on") || cmd.includes("turn on fan")) {
    const room = localStorage.getItem('activeRoom') || 'living';
    setFanSpeed(3, room);
    voiceSpeak("Fan turned on at speed 3");

  } else if (cmd.includes("fan off") || cmd.includes("turn off fan")) {
    const room = localStorage.getItem('activeRoom') || 'living';
    setFanSpeed(0, room);
    voiceSpeak("Fan turned off");

  } else if (cmd.match(/fan speed (\d)/)) {
    const speed = parseInt(cmd.match(/fan speed (\d)/)[1]);
    const room = localStorage.getItem('activeRoom') || 'living';
    setFanSpeed(speed, room);
    voiceSpeak(`Fan speed set to ${speed}`);

  // --- Curtains ---
  } else if (cmd.includes("open curtain") || cmd.includes("curtain open")) {
    const room = localStorage.getItem('activeRoom') || 'living';
    curtainStates[room] = true;
    fetch("/toggle_curtain", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ open: true, room }) })
      .then(r => r.json()).then(() => loadLog());
    voiceSpeak("Curtains opened");

  } else if (cmd.includes("close curtain") || cmd.includes("curtain close")) {
    const room = localStorage.getItem('activeRoom') || 'living';
    curtainStates[room] = false;
    fetch("/toggle_curtain", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ open: false, room }) })
      .then(r => r.json()).then(() => loadLog());
    voiceSpeak("Curtains closed");

  // --- Door ---
  } else if (cmd.includes("unlock door") || cmd.includes("open door")) {
    document.getElementById("doorPassword").value = "1234";
    unlockDoor();
    voiceSpeak("Attempting to unlock door");

  // --- Bell ---
  } else if (cmd.includes("ring bell") || cmd.includes("doorbell")) {
    ringBell();
    voiceSpeak("Ringing the doorbell");

  // --- Lights Dimmer ---
  } else if (cmd.match(/brightness (\d+)/)) {
    const val = parseInt(cmd.match(/brightness (\d+)/)[1]);
    updateDimmer(val);
    voiceSpeak(`Brightness set to ${val} percent`);

  // --- Inverter ---
  } else if (cmd.includes("inverter on")) {
    setInverter(true);
    voiceSpeak("Inverter turned on");

  } else if (cmd.includes("inverter off")) {
    setInverter(false);
    voiceSpeak("Inverter turned off");

  // --- Energy ---
  } else if (cmd.includes("energy") || cmd.includes("power usage")) {
    showEnergyUsage();
    voiceSpeak("Checking energy usage");

  // --- Pet ---
  } else if (cmd.includes("feed pet") || cmd.includes("feed dog") || cmd.includes("feed cat")) {
    feedPet();
    voiceSpeak("Feeding the pet now");

  // --- Unknown ---
  } else {
    voiceSpeak("Sorry, I did not understand that command");
  }
}

function startVoice() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert("Voice commands not supported in this browser. Please use Chrome.");
    return;
  }

  if (voiceActive) {
    stopVoice();
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    voiceActive = true;
    const btn = document.getElementById("voiceBtn");
    if (btn) { btn.textContent = "🔴 Listening..."; btn.style.background = "linear-gradient(135deg, #c62828, #b71c1c)"; }
    const statusEl = document.getElementById("voice-status");
    if (statusEl) statusEl.textContent = "🎤 Listening... speak now";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    processVoiceCommand(transcript);
  };

  recognition.onerror = (event) => {
    const statusEl = document.getElementById("voice-status");
    if (statusEl) statusEl.textContent = "❌ Error: " + event.error;
    stopVoice();
  };

  recognition.onend = () => {
    stopVoice();
  };

  recognition.start();
}

function stopVoice() {
  voiceActive = false;
  if (recognition) { try { recognition.stop(); } catch(e) {} }
  const btn = document.getElementById("voiceBtn");
  if (btn) { btn.textContent = "🎤 Start Voice"; btn.style.background = ""; }
}