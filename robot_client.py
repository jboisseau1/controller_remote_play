import asyncio
import json
import cv2
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaRecorder, MediaPlayer
from aiortc.contrib.signaling import BYE

import av

from picamera2 import Picamera2


class CameraStreamTrack(VideoStreamTrack):
    """
    A video track that captures frames from OpenCV and yields them to WebRTC.
    """
    def __init__(self):
        super().__init__()
        self.picam2 = Picamera2()
        # Create a video configuration.
        video_config = self.picam2.create_video_configuration(
            main={"format": "RGB888"}
        )
        self.picam2.configure(video_config)
        self.picam2.start()

    async def recv(self):
        # Get the next available timestamp for this frame.
        try:
            pts, time_base = await self.next_timestamp()

        # Capture a frame as a numpy array (in RGB format as configured).
            frame = self.picam2.capture_array()

        # Optional: Process the frame with OpenCV (e.g., flipping, drawing, etc.)
        # For example, to flip the frame horizontally:
        # frame = cv2.flip(frame, 1)

        # Wrap the numpy array into an AV VideoFrame.
            video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base    
        except Exception as e:
            print("Error:", e)

        return video_frame

    def stop(self):
        self.picam2.stop()
        super().stop()

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
        local_video = CameraStreamTrack()
        pc.addTrack(local_video)

        # Create a DataChannel for receiving commands
        @pc.on("datachannel")
        def on_datachannel(channel):
            print("Data channel created by remote peer:", channel.label)
            print(channel)
            @channel.on("message")
            def on_message(message):
                try:
                    print(msg)
                    data = json.loads(msg)
                except Exception as e:
                    print('Error', e)
                # data["axes"] => array of floats
                # data["buttons"] => array of { pressed: bool, value: float }
                # do something with these to control motors
                print("Controller state:", data)


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
    try:
        asyncio.run(main())
    except Exception as e:
        print("Error:", e)
