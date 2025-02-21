import asyncio
import json
import websockets

# Store robot connections keyed by a unique robot_id
ROBOTS = {}
# Store user connections similarly if you want many users
USERS = {}

async def handler(websocket):
    """
    Very simple logic:
    1. Client sends a JSON message to register as either "robot" or "user" with an ID.
    2. If "robot", store it in ROBOTS.
    3. If "user", store it in USERS.
    4. Forward subsequent messages (SDP and ICE) to the appropriate counterpart.
    """
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "register_robot":
                robot_id = data["robot_id"]
                ROBOTS[robot_id] = websocket
                print(f"Robot {robot_id} registered.")
                await websocket.send(json.dumps({"type": "robot_registered", "robot_id": robot_id}))

            elif data["type"] == "register_user":
                user_id = data["user_id"]
                USERS[user_id] = websocket
                print(f"User {user_id} registered.")
                await websocket.send(json.dumps({"type": "user_registered", "user_id": user_id}))

            elif data["type"] == "offer":
                # user -> robot
                robot_id = data["robot_id"]
                if robot_id in ROBOTS:
                    await ROBOTS[robot_id].send(message)
                    print("sending offer from user to robot")

            elif data["type"] == "answer":
                # robot -> user
                user_id = data["user_id"]
                if user_id in USERS:
                    await USERS[user_id].send(message)
                    print("sending user response from robot")

            elif data["type"] == "ice_candidate":
                # Forward ICE candidates
                target_id = data["target_id"]  # either robot_id or user_id
                target_role = data["target_role"]  # "robot" or "user"
                if target_role == "robot" and target_id in ROBOTS:
                    await ROBOTS[target_id].send(message)
                elif target_role == "user" and target_id in USERS:
                    await USERS[target_id].send(message)
                print('forwarding ICE to ', target_role)

    except websockets.exceptions.ConnectionClosed:
        print("Connection closed.")
    finally:
        # Cleanup logic if needed
        pass

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Signaling server running on ws://0.0.0.0:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
