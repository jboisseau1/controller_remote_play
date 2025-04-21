// app.js — PiCamera + Gamepad demo
import { PiCamera } from 'https://cdn.jsdelivr.net/npm/picamera.js/+esm';

// DOM refs
const vid        = document.getElementById('vid');
const connectBtn = document.getElementById('connect');
const testBtn = document.getElementById('test');

const logEl      = document.getElementById('log');
const axesEl     = document.getElementById('gp-axes');
const buttonsEl  = document.getElementById('gp-buttons');

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
        log(JSON.stringify({ type:'gamepad' }))

     piDC.send(0);
    }
}

// Start WebRTC & MQTT signalling
function startConnection(cfg) {
  conn = new PiCamera(cfg);
  console.log(conn)
  conn.onStream = stream => {
    vid.srcObject = stream ?? null;
    log('Video stream attached');
  };

  conn.onDatachannel = dc => {
    piDC = dc;
    console.log(dc)
    log(`Data‑channel open (label=${dc.label}, id=${dc.id})`);
  };

  conn.onConnectionState = state => {
    log(`Peer state ➜ ${state}`);
    if (state === 'connected') {
      pollExistingGamepad();
    }
    log(`New Peer state ${state}`)
  };

  conn.connect();
}

// look for a pad that was plugged in early
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
        log(JSON.stringify({ type:'gamepad', axes, buttons, timestamp: gp.timestamp }))

    //  piDC.send(JSON.stringify({ type:'gamepad', axes, buttons, timestamp: gp.timestamp }));
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
