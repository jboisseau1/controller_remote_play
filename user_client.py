import asyncio
import json
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole

async def user_main(user_id="user_456", robot_id="robot_123"):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # 1. Register as user
        register_msg = {
            "type": "register_user",
            "user_id": user_id
        }
        await ws.send(json.dumps(register_msg))
        response = await ws.recv()
        print("Signaling server response:", response)

        pc = RTCPeerConnection()

        # Add a data channel to send commands
        channel = pc.createDataChannel("robotControl")
        pc.addTransceiver("video", direction="recvonly")
        
        @channel.on("open")
        def on_open():
            print("Data channel is open. Sending test command.")
            channel.send("MOVE_FORWARD")

        @pc.on("track")
        def on_track(track):
            print(f"Receiving track: {track.kind}")
            if track.kind == "video":
                # Optionally, display frames or store them
                # Here, we just drop them (MediaBlackhole) for simplicity
                recorder = MediaBlackhole()
                recorder.addTrack(track)
                recorder.start()

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is not None:
                ice_msg = {
                    "type": "ice_candidate",
                    "target_id": robot_id,
                    "target_role": "robot",
                    "candidate": candidate.to_sdp(),
                    "sdpMid": candidate.sdp_mid,
                    "sdpMLineIndex": candidate.sdp_mline_index
                }
                await ws.send(json.dumps(ice_msg))

        # Create an offer to send to the robot
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        # Send offer
        offer_msg = {
            "type": "offer",
            "robot_id": robot_id,
            "user_id": user_id,
            "sdp": pc.localDescription.sdp,
            "sdp_type": pc.localDescription.type
        }
        await ws.send(json.dumps(offer_msg))

        # Wait for answer
        while True:
            msg_str = await ws.recv()
            msg = json.loads(msg_str)
            print(msg)
            if msg["type"] == "answer":
                # Robot responded with an answer
                answer_sdp = msg["sdp"]
                answer_type = msg["sdp_type"]
                answer = RTCSessionDescription(sdp=answer_sdp, type=answer_type)
                await pc.setRemoteDescription(answer)
                print("Set remote description with answer.")
            elif msg["type"] == "ice_candidate":
                # Robot ICE candidate
                candidate_sdp = msg["candidate"]
                sdpMid = msg["sdpMid"]
                sdpMLineIndex = msg["sdpMLineIndex"]
                from aiortc import candidate_from_sdp
                candidate = candidate_from_sdp(candidate_sdp, sdpMid, sdpMLineIndex)
                pc.addIceCandidate(candidate)
            else:
                print("Unknown message:", msg)

async def main():
    await user_main()

if __name__ == "__main__":
    asyncio.run(main())
