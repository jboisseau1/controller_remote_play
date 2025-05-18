// app.js — PiCamera + Gamepad demo
import { PiCamera } from 'https://cdn.jsdelivr.net/npm/picamera.js@1.0.11/+esm';

// DOM refs
const vid        = document.getElementById('vid');
const connectButton = document.getElementById('connect');

const socket = new WebSocket('ws://localhost:3000');


let connection;        // PiCamera instance
let dataChannel;        // default data‑channel

// Connect button
connectButton.onclick = async () => {
  const cfg = await fetch('/config.json').then(r => r.json());
  startConnection(cfg);
};


// Start WebRTC & MQTT signalling
function startConnection(cfg) {
  connection = new PiCamera(cfg);
  connection.onStream = stream => {
    vid.srcObject = stream ?? null;
  };

  connection.onDatachannel = dc => {
    dataChannel = dc;
    dataChannel.onmessage = message => {
      console.log('Received message from remote:', message.data);
      socket.send(message.data); 
    };
  };

  socket.onmessage = (message) => {
      console.log('Received message from local:', message.data);
      dataChannel?.send(message.data);
  };

  connection.onConnectionState = state => {
    connectButton.disabled = state === 'connected';
  };

  connection.connect();
}
