import asyncio
import json
import cv2
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaRecorder, MediaPlayer
from aiortc.contrib.signaling import BYE

class CameraStreamTrack(VideoStreamTrack):
    """
    A video track that captures frames from OpenCV and yields them to WebRTC.
    """
    def __init__(self, camera_index=0):
        super().__init__()
        self.cap = cv2.VideoCapture(camera_index)

    async def recv(self):
        # Grab an OpenCV frame
        # If your robot uses something like a PiCamera, you'll adapt this code
        ret, frame = self.cap.read()
        if not ret:
            # If no frame, send a blank frame or raise an exception
            await asyncio.sleep(0.1)
            return None

        # Convert frame to RGB (aiortc expects frames in a consistent format)
        # If needed, import VideoFrame from av, then wrap the numpy array
        from av import VideoFrame
        frame_av = VideoFrame.from_ndarray(frame, format="bgr24")
        frame_av.pts = None
    
        await asyncio.sleep(1 / 30)  # Simulate ~30fps
        return frame_av

async def robot_main(robot_id="robot_123", camera_idx=0):
    # Step 1: connect to the signaling server
    uri = "ws://192.168.1.196:8765"
    async with websockets.connect(uri) as ws:
        # Register as a robot
        register_msg = {
            "type": "register_robot",
            "robot_id": robot_id
        }
        await ws.send(json.dumps(register_msg))

        # Wait for confirmation
        response = await ws.recv()
        print("Signaling server response:", response)

        # Prepare a single RTCPeerConnection
        pc = RTCPeerConnection()

        # Create a local track from the camera
        # options={"framerate": "30", "video_size": "640x480"}
        # player = MediaPlayer("0:none", format="avfoundation", options=options) # MacOS camera feed
        # player = MediaPlayer("/dev/video0", format="v4l2", options=options) # Pi Cam feed
        local_video = CameraStreamTrack(camera_index=camera_idx)
        pc.addTrack(local_video)

        # Create a DataChannel for receiving commands
        @pc.on("datachannel")
        def on_datachannel(channel):
            print("Data channel created by remote peer:", channel.label)

            @channel.on("message")
            def on_message(message):
                # Handle commands from user
                print(f"Received command: {message}")
                # You can parse the message (e.g. JSON) and drive motors, etc.
                # e.g. if message == 'MOVE_FORWARD': robot.go_forward()

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is not None:
                ice_msg = {
                    "type": "ice_candidate",
                    "target_id": user_id,  # We'll know user_id from the incoming offer
                    "target_role": "user",
                    "candidate": candidate.to_sdp(),
                    "sdpMid": candidate.sdp_mid,
                    "sdpMLineIndex": candidate.sdp_mline_index
                }
                await ws.send(json.dumps(ice_msg))

        user_id = None

        # Step 2: handle messages from the signaling server
        while True:
            msg_str = await ws.recv()
            msg = json.loads(msg_str)
            if msg["type"] == "offer":
                # The user is initiating a connection
                user_id = msg["user_id"]
                offer_sdp = msg["sdp"]
                offer_type = msg["sdp_type"]

                # Set remote description
                offer = RTCSessionDescription(sdp=offer_sdp, type=offer_type)
                await pc.setRemoteDescription(offer)

                # Create answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)

                # Send answer back to user
                answer_msg = {
                    "type": "answer",
                    "user_id": user_id,
                    "sdp": pc.localDescription.sdp,
                    "sdp_type": pc.localDescription.type
                }
                await ws.send(json.dumps(answer_msg))

            elif msg["type"] == "ice_candidate":
                # The user is sending us an ICE candidate
                from aiortc import RTCIceCandidate
                candidate_sdp = msg["candidate"]
                sdpMid = msg["sdpMid"]
                sdpMLineIndex = msg["sdpMLineIndex"]

                from aiortc.sdp import candidate_from_sdp
                candidate = candidate_from_sdp(candidate_sdp)
                candidate.sdpMid = sdpMid
                candidate.sdpMLineIndex = sdpMLineIndex
                await pc.addIceCandidate(candidate)


            else:
                print("Unknown message:", msg)

async def main():
    await robot_main()


if __name__ == "__main__":
    asyncio.run(main())
