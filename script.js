// Adjust these to match your environment
const SIGNALING_SERVER_URL = "ws://localhost:8765";
const USER_ID = "user_123";
const ROBOT_ID = "robot_123"; // Must match the robot's ID in robot_client.py

// Minimal STUN config for NAT traversal (TURN is recommended for production)
const RTC_CONFIG = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
};

let ws;
let pc;
let dataChannel;

/**
 * Initialize the WebSocket connection to the Python signaling server
 * and register as a user.
 */
async function initWebSocket() {
  ws = new WebSocket(SIGNALING_SERVER_URL);

  ws.onopen = () => {
    console.log("[WS] Connected to signaling server.");
    // Register as a user once connected
    const registerMsg = {
      type: "register_user",
      user_id: USER_ID
    };
    ws.send(JSON.stringify(registerMsg));
  };

  ws.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    console.log("[WS] Message from server:", msg);

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
        // Robot is sending ICE candidates back
        const candidate = new RTCIceCandidate({
          candidate: msg.candidate,
          sdpMid: msg.sdpMid,
          sdpMLineIndex: msg.sdpMLineIndex
        });
        await pc.addIceCandidate(candidate);
        break;

      default:
        console.warn("[WS] Unknown message type:", msg.type);
    }
  };

  ws.onerror = (err) => {
    console.error("[WS] Error:", err);
  };

  ws.onclose = () => {
    console.log("[WS] Connection closed.");
  };
}

/**
 * Create the RTCPeerConnection, configure tracks/transceivers, and
 * set up event handlers (ICE, data channel, remote track).
 */
async function createPeerConnection() {
  pc = new RTCPeerConnection(RTC_CONFIG);

  // Create a data channel to send commands
  dataChannel = pc.createDataChannel("robotControl");
  dataChannel.onopen = () => {
    console.log("[DataChannel] Opened.");
    // Example: automatically send a hello
    // dataChannel.send("Hello Robot!");
  };
  dataChannel.onmessage = (event) => {
    console.log("[DataChannel] Robot -> User message:", event.data);
  };

  // Handle local ICE candidates (we forward them to the robot)
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

  // When the robot's video arrives, attach it to <video>
  pc.ontrack = (event) => {
    console.log("[PeerConnection] ontrack =>", event.streams);
    console.log(event.track)
    if (event.track.kind === "video") {
      const videoElement = document.getElementById("robotVideo");
      if (videoElement) {
        videoElement.srcObject = event.streams[0];
      }
    }
  };

  // Because we only want to receive video from the robot,
  // we add a video transceiver in "recvonly" mode:
  pc.addTransceiver("video", { direction: "recvonly" });

  // If we wanted to share our own camera, we'd do it here, e.g.:
  // const localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
  // for (const track of localStream.getTracks()) {
  //   pc.addTrack(track, localStream);
  // }
}

/**
 * Send an SDP offer to the robot.
 */
async function connectToRobot() {
  await createPeerConnection();

  // Create offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  // Send our offer SDP to the signaling server
  const offerMsg = {
    type: "offer",
    robot_id: ROBOT_ID,
    user_id: USER_ID,
    sdp: pc.localDescription.sdp,
    sdp_type: pc.localDescription.type
  };
  console.log(offerMsg)
  ws.send(JSON.stringify(offerMsg));
  console.log("[Signaling] Offer sent to robot");
}

/**
 * Sends a test command (MOVE_FORWARD) over the DataChannel.
 */
function sendMoveCommand() {
  if (dataChannel && dataChannel.readyState === "open") {
    dataChannel.send("MOVE_FORWARD");
    console.log("[DataChannel] Sent MOVE_FORWARD");
  } else {
    console.warn("[DataChannel] Not open yet");
  }
}

// ---------------------------
// Attach to buttons on page
// ---------------------------
window.onload = () => {
  initWebSocket();

  document
    .getElementById("connectButton")
    .addEventListener("click", connectToRobot);

  document
    .getElementById("sendCommandButton")
    .addEventListener("click", sendMoveCommand);
};
