import json
import websocket
import threading
import time
import ssl

CORTEX_URL = "wss://localhost:6868"

ANDROID_WS_URL = "ws://192.168.1.100:8080"  
TILT_THRESHOLD = 30 

CLIENT_ID = "U9DXXWkTQVrRzpLMiGTyxb3abKyrRmby2uac2mP9"
CLIENT_SECRET = "YJA6uP62fs08DsJjm4jivnVsis4aO2rvfdysebDfdppIiQ3nzJc7VY6RCQC9OgA5wXETiEgh7aASoWex6g1yRlLevBMvPB3FCqfzj9Fl3UyxvH8JNvgLBxDl6UI2uEAI"

def request_access(ws):
    """Requests access to the Emotiv Cortex API."""
    print("[DEBUG] Requesting access...")
    access_request = {
        "jsonrpc": "2.0",
        "method": "requestAccess",
        "params": {
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET
        },
        "id": 0
    }
    ws.send(json.dumps(access_request))
    response = json.loads(ws.recv())
    print("[DEBUG] Access request response:", response)

def authenticate(ws):
    """Authenticates and gets Cortex token."""
    print("[DEBUG] Sending authentication request...")
    auth_request = {
        "jsonrpc": "2.0",
        "method": "authorize",
        "params": {
            "clientId": CLIENT_ID,
            "clientSecret": CLIENT_SECRET
        },
        "id": 1
    }
    ws.send(json.dumps(auth_request))
    response = json.loads(ws.recv())
    print("[DEBUG] Authentication response:", response)
    return response.get("result", {}).get("cortexToken")

def query_headsets(ws):
    """Queries the connected headsets."""
    print("[DEBUG] Querying connected headsets...")
    headset_request = {
        "jsonrpc": "2.0",
        "method": "queryHeadsets",
        "params": {},
        "id": 2
    }
    ws.send(json.dumps(headset_request))
    response = json.loads(ws.recv())
    print("[DEBUG] Headset query response:", response)

    if "result" in response:
        return response["result"]
    else:
        print("[ERROR] Failed to query headsets.")
        return None

def create_session(ws, token, headset_id):
    """Creates a session with the Emotiv headset."""
    print("[DEBUG] Creating session...")
    session_request = {
        "jsonrpc": "2.0",
        "method": "createSession",
        "params": {
            "cortexToken": token,
            "headset": headset_id,
            "status": "active"
        },
        "id": 3
    }
    ws.send(json.dumps(session_request))
    response = json.loads(ws.recv())
    print("[DEBUG] Session creation response:", response)
    return response.get("result", {}).get("id")

def subscribe_gyro(ws, token, session_id):
    """Subscribes to gyroscope data stream."""
    print("[DEBUG] Subscribing to gyro data...")
    subscribe_request = {
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "cortexToken": token,
            "session": session_id,
            "streams": ["mot"]
        },
        "id": 4
    }
    ws.send(json.dumps(subscribe_request))
    response = json.loads(ws.recv())
    print("[DEBUG] Subscription response:", response)

def on_message(ws, message):
    """Handles incoming messages from Cortex API."""
    print("[DEBUG] Received message:", message)
    data = json.loads(message)
    if "mot" in data:  # Check if motion data is received
        gyro_x, gyro_y = data["mot"][3], data["mot"][4]  # Extract gyro data
        print(f"Gyro Data - X: {gyro_x}, Y: {gyro_y}")

        if abs(gyro_x) > TILT_THRESHOLD or abs(gyro_y) < 0.4:
            print("Head Tilt Detected! Sending to Android...")
            send_tilt_event()

def send_tilt_event():
    """Sends tilt event to Android via WebSocket."""
    try:
        print("[DEBUG] Sending tilt event to Android...")
        android_ws = websocket.create_connection(ANDROID_WS_URL)
        android_ws.send(json.dumps({"event": "tilt_detected"}))
        android_ws.close()
    except Exception as e:
        print("Error sending to Android:", e)

def connect_to_cortex():
    """Establishes connection to the Emotiv Cortex API and sets up session."""
    print("[DEBUG] Connecting to Cortex API...")
    ws = websocket.create_connection(CORTEX_URL, sslopt={"cert_reqs": ssl.CERT_NONE})
    token = authenticate(ws)
    if not token:
        print("[ERROR] Failed to get authentication token.")
        return

    headsets = query_headsets(ws)
    if not headsets:
        print("[ERROR] No headset found. Cannot proceed.")
        return

    headset_id = headsets[0]["id"]
    session_id = create_session(ws, token, headset_id)
    if not session_id:
        print("[ERROR] Failed to create session.")
        return

    subscribe_gyro(ws, token, session_id)

    print("[DEBUG] Listening for gyro data...")
    while True:
        message = ws.recv()
        on_message(ws, message)

def start():
    """Starts the WebSocket connection in a thread."""
    thread = threading.Thread(target=connect_to_cortex)
    thread.start()

if __name__ == "__main__":
    start()
