import asyncio
import json
import cv2
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaRecorder, MediaPlayer
from aiortc.contrib.signaling import BYE

from av import VideoFrame

class PiCameraTrack(VideoStreamTrack):
    """
    A custom VideoStreamTrack that captures frames from the Raspberry Pi camera
    using the picamera library.
    """
    def __init__(self):
        super().__init__()
        # Importing here to ensure it's only used on Raspberry Pi
        import picamera
        import picamera.array
        self.camera = picamera.PiCamera()
        # Set resolution and frame rate as desired
        self.camera.resolution = (640, 480)
        self.camera.framerate = 30
        # Create an array stream for image capture
        self.raw_capture = picamera.array.PiRGBArray(self.camera, size=(640, 480))
        # Allow the camera to warm up
        time.sleep(2)

    async def recv(self):
        """
        Capture a frame from the camera and return it as an AV VideoFrame.
        The blocking capture call is offloaded to a thread to avoid blocking the event loop.
        """
        # Get the next timestamp for the frame.
        pts, time_base = await self.next_timestamp()

        # Offload the blocking capture call to the default executor.
        loop = asyncio.get_running_loop()
        frame = await loop.run_in_executor(None, self.capture_frame)

        # Create a VideoFrame from the captured numpy array.
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def capture_frame(self):
        """
        Blocking call to capture a single frame using picamera.
        """
        self.camera.capture(self.raw_capture, format="rgb", use_video_port=True)
        image = self.raw_capture.array
        # Clear the stream for the next frame.
        self.raw_capture.truncate(0)
        return image


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
        # pc.addTrack(player.video)
        # player = MediaPlayer("/dev/video0", format="v4l2", options=options) # Pi Cam feed
        video_track = PiCameraTrack()
        pc.addTrack(video_track)

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
