// app.js — PiCamera + Gamepad demo
import { PiCamera } from 'https://cdn.jsdelivr.net/npm/picamera.js/+esm';

// DOM refs
const vid        = document.getElementById('vid');
const connectBtn = document.getElementById('connect');
const testBtn = document.getElementById('test');

const logEl      = document.getElementById('log');
const axesEl     = document.getElementById('gp-axes');
const buttonsEl  = document.getElementById('gp-buttons');
const RC_COMM_CHANNEL = 6

let conn;        // PiCamera instance
let piDC;        // default data‑channel
let gpInterval;  // gamepad poll timer

const log = m => {
  logEl.textContent += m + '\n';
  logEl.scrollTop = logEl.scrollHeight;
};

// Connect button
connectBtn.onclick = async () => {
  connectBtn.disabled = true;
  const cfg = await fetch('/config.json').then(r => r.json());
  startConnection(cfg);
};
// send data channel test message
testBtn.onclick = async () => {
    if (piDC?.readyState === 'open') {
        let gpState = generateRTCmessage(6, JSON.stringify({ type:'gamepad', axes:[], buttons:[], timestamp: 12345 }))
        piDC.send(gpState)
    }
}

// Start WebRTC & MQTT signalling
function startConnection(cfg) {
  conn = new PiCamera(cfg);
  conn.onStream = stream => {
    vid.srcObject = stream ?? null;
    log('Video stream attached');
  };

  conn.onDatachannel = dc => {
    piDC = dc;
    log(`Data‑channel open (label=${dc.label}, id=${dc.id})`);
  };

  conn.onMetadata = metadata => {
    log(`Telemitry data feed up`)
    console.log(metadata)
  }

  conn.onConnectionState = state => {
    log(`Peer state ➜ ${state}`);
    if (state === 'connected') {
      pollExistingGamepad();
    }
    log(`New Peer state ${state}`)
  };

  conn.connect();
}

function pollExistingGamepad() {
  const gps = navigator.getGamepads();
  for (let i = 0; i < gps.length; i++) {
    if (gps[i]) {
      log(`Found existing gamepad: ${gps[i].id}`);
      startGamepadPolling(i);
      break;
    }
  }
}

function generateRTCmessage(type, message){
    let payload = {}
    payload.type = type;
    payload.message = typeof message === 'string' ? message : String(message)
    return JSON.stringify(payload)
}

// Listen for plug/unplug
window.addEventListener('gamepadconnected', e => {
  log(`Gamepad connected: ${e.gamepad.id}`);
  startGamepadPolling(e.gamepad.index);
});

window.addEventListener('gamepaddisconnected', e => {
  log(`Gamepad disconnected: ${e.gamepad.id}`);
  stopGamepadPolling();
});

// Poll & send + update status UI
function startGamepadPolling(index) {
  stopGamepadPolling();
  gpInterval = setInterval(() => {
    const gp = navigator.getGamepads()[index];
    if (!gp) return;

    // format
    const axes    = gp.axes.map(a => Number(a.toFixed(2)));
    const buttons = gp.buttons.map(b => b.pressed);

    // update UI
    axesEl.textContent    = axes.join(', ');
    buttonsEl.textContent = buttons.map(v => (v ? '●' : '○')).join(' ');

    // send to Pi
    if (piDC?.readyState === 'open') {
        let gpState = generateRTCmessage(RC_COMM_CHANNEL, JSON.stringify({ type:'gamepad', axes, buttons, timestamp: gp.timestamp }))
        // log(gpState)
        piDC.send(gpState)
    
    }
  }, 100);
}

function stopGamepadPolling() {
  if (gpInterval) {
    clearInterval(gpInterval);
    gpInterval = null;
    axesEl.textContent    = '-';
    buttonsEl.textContent = '-';
  }
}
