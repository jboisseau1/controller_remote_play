/**********************
 * CONFIG + GLOBALS
 **********************/
const SIGNALING_SERVER_URL = "ws://localhost:8765"; // Adjust to your server
const USER_ID = "user_123";                  // Arbitrary unique user ID
const ROBOT_ID = "robot_123";                      // Must match your robot's ID
const RTC_CONFIG = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
};

let ws;                 // WebSocket to signaling server
let pc;                 // RTCPeerConnection
let dataChannel;        // DataChannel for sending control commands
let activeGamepadIndex; // Which gamepad index we're using

/**********************
 * INIT WEBSOCKET
 **********************/
async function initWebSocket() {
  ws = new WebSocket(SIGNALING_SERVER_URL);

  ws.onopen = () => {
    console.log("[WS] Connected to signaling server.");
    // Register as user
    const registerMsg = { type: "register_user", user_id: USER_ID };
    ws.send(JSON.stringify(registerMsg));
  };

  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    console.log("[WS] Received:", msg);

    switch (msg.type) {
      case "user_registered":
        console.log("[Signaling] Registered as user:", msg.user_id);
        break;

      case "answer":
        // Robot responded with an SDP answer
        console.log("[Signaling] Got answer from robot");
        await pc.setRemoteDescription({
          type: msg.sdp_type,
          sdp: msg.sdp
        });
        break;

      case "ice_candidate":
        // Robot is sending ICE candidates
        if (msg.candidate) {
          const candidate = new RTCIceCandidate({
            candidate: msg.candidate,
            sdpMid: msg.sdpMid,
            sdpMLineIndex: msg.sdpMLineIndex
          });
          await pc.addIceCandidate(candidate);
        }
        break;

      default:
        console.warn("[WS] Unknown message type:", msg.type);
    }
  };

  ws.onerror = (err) => console.error("[WS] Error:", err);
  ws.onclose = () => console.log("[WS] Connection closed.");
}

/**********************
 * CREATE PEER CONNECTION
 **********************/
async function createPeerConnection() {
  pc = new RTCPeerConnection(RTC_CONFIG);

  // Create a data channel for sending gamepad inputs
  dataChannel = pc.createDataChannel("robotControl");
  dataChannel.onopen = () => {
    console.log("[DataChannel] Opened.");
  };
  dataChannel.onmessage = (event) => {
    console.log("[DataChannel] Robot -> User:", event.data);
  };

  // When the robot sends us ICE candidates, we add them in onmessage above
  // Here we forward our ICE candidates to the robot
  pc.onicecandidate = (event) => {
    if (event.candidate) {
      const candidateMsg = {
        type: "ice_candidate",
        target_id: ROBOT_ID,
        target_role: "robot",
        candidate: event.candidate.candidate,
        sdpMid: event.candidate.sdpMid,
        sdpMLineIndex: event.candidate.sdpMLineIndex
      };
      ws.send(JSON.stringify(candidateMsg));
    }
  };

  // Handle the remote track (robot video)
  pc.ontrack = (event) => {
    console.log("[PeerConnection] ontrack => kind:", event.track.kind);
    if (event.track.kind === "video") {
      const videoElem = document.getElementById("robotVideo");
      if (videoElem) {
        videoElem.srcObject = event.streams[0];
      }
    }
  };

  // Add a transceiver to receive the robot's video
  pc.addTransceiver("video", { direction: "recvonly" });
}

/**********************
 * CONNECT TO ROBOT
 **********************/
async function connectToRobot() {
  await createPeerConnection();

  // Create an offer and send to the robot
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  const offerMsg = {
    type: "offer",
    robot_id: ROBOT_ID,
    user_id: USER_ID,
    sdp: pc.localDescription.sdp,
    sdp_type: pc.localDescription.type
  };
  ws.send(JSON.stringify(offerMsg));
  console.log("[Signaling] Sent offer to robot");
}

/**********************
 * GAMEPAD LOGIC
 **********************/
// Poll gamepad inputs and send them over the data channel
function pollGamepads() {
  const gamepads = navigator.getGamepads();
  // If we don't have a chosen index, pick the first connected one
  if (activeGamepadIndex == null) {
    for (let i = 0; i < gamepads.length; i++) {
      if (gamepads[i]) {
        activeGamepadIndex = i;
        console.log("Using gamepad index", i, "=>", gamepads[i].id);
        break;
      }
    }
  }

  if (activeGamepadIndex == null) {
    // No gamepad found
    document.getElementById("status").textContent = "No gamepad connected";
    return;
  }

  const gp = gamepads[activeGamepadIndex];
  if (!gp) {
    // The previously active gamepad disconnected
    activeGamepadIndex = null;
    return;
  }

  // Build a JSON object with axes & buttons
  const axes = gp.axes.map((val) => val.toFixed(2));
  const buttons = gp.buttons.map((btn) => ({
    pressed: btn.pressed,
    value: btn.value.toFixed(2)
  }));

  const controllerState = {
    timestamp: Date.now(),
    axes,
    buttons
  };

  // Send it over the data channel if it's open
  if (dataChannel && dataChannel.readyState === "open") {
    dataChannel.send(JSON.stringify(controllerState));
  }

  // Update the status div
  const statusElem = document.getElementById("status");
  statusElem.textContent = `Gamepad: ${gp.id}
    | Axes: ${axes.join(", ")}
    | Buttons: ${buttons.map((b, i) => `B${i}:${b.pressed}`).join(" ")}`;
}

// Continuously poll for gamepad data ~60 fps
function updateLoop() {
  pollGamepads();
  requestAnimationFrame(updateLoop);
}

// Listen for connect/disconnect events
window.addEventListener("gamepadconnected", (e) => {
  console.log("[Gamepad] connected:", e.gamepad.index, e.gamepad.id);
});
window.addEventListener("gamepaddisconnected", (e) => {
  console.log("[Gamepad] disconnected:", e.gamepad.index, e.gamepad.id);
  if (e.gamepad.index === activeGamepadIndex) {
    activeGamepadIndex = null;
  }
});

/**********************
 * ON LOAD
 **********************/
window.onload = async () => {
  await initWebSocket();

  // Start the gamepad polling loop
  updateLoop();

  // Hook up the Connect button
  document
    .getElementById("connectButton")
    .addEventListener("click", connectToRobot);
};
