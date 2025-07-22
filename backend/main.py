import asyncio
import cv2
import numpy as np
from fer import FER
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import ollama

# --- App and Middleware Setup ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Globals and Constants ---
EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
EMOTION_THRESHOLD = 0.25 

cumulative_stats = {e: 0.0 for e in EMOTIONS}
latest_frame = None
latest_emotions = {e: 0.0 for e in EMOTIONS}
shutdown_event = asyncio.Event()

cap = None
detector = None

# --- Core Application Logic ---
async def capture_frames():
    """
    Continuously capture frames from webcam, detect emotions,
    and update global state.
    """
    global latest_frame, latest_emotions, cumulative_stats
    while not shutdown_event.is_set():
        if cap is None or detector is None:
            await asyncio.sleep(0.5)
            continue
        
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue

        latest_frame = frame

        try:
            results = await run_in_threadpool(detector.detect_emotions, frame)
            if results:
                latest_emotions = results[0]["emotions"]
            else:
                latest_emotions = {e: 0.0 for e in EMOTIONS}
            
            for e in EMOTIONS:
                if(latest_emotions.get(e, 0.0) > EMOTION_THRESHOLD):
                    cumulative_stats[e] += latest_emotions.get(e, 0.0)

        except Exception as e:
            print(f"Error during emotion detection: {e}")
            latest_emotions = {e: 0.0 for e in EMOTIONS}

        await asyncio.sleep(0.03)

# --- FastAPI Events ---
@app.on_event("startup")
async def on_startup():
    """Initializes resources when the application starts."""
    global cap, detector
    print("🚀 Server starting up...")
    print("   - Initializing camera...")
    cap = cv2.VideoCapture(0)
    print("   - Initializing emotion detector (this may take a moment)...")
    detector = FER(mtcnn=True)
    print("✅ Initialization complete. Starting background tasks.")
    asyncio.create_task(capture_frames())

@app.on_event("shutdown")
def on_shutdown():
    """Releases resources when the application stops."""
    print("🔌 Server shutting down...")
    shutdown_event.set()
    if cap:
        cap.release()
    print("✅ Shutdown complete.")

# --- WebSocket Endpoints (DEFINED BEFORE a catch-all route) ---
@app.websocket("/ws/video")
async def ws_video(ws: WebSocket):
    await ws.accept()
    print("🤝 WebSocket connection accepted: /ws/video")
    try:
        while True:
            if latest_frame is not None:
                ret, jpeg = cv2.imencode(".jpg", latest_frame)
                if ret:
                    await ws.send_bytes(jpeg.tobytes())
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        print("💔 WebSocket connection closed: /ws/video")

@app.websocket("/ws/emotion")
async def ws_emotion(ws: WebSocket):
    await ws.accept()
    print("🤝 WebSocket connection accepted: /ws/emotion")
    try:
        while True:
            await ws.send_json(latest_emotions)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("💔 WebSocket connection closed: /ws/emotion")

@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    print("🤝 WebSocket connection accepted: /ws/chat")
    try:
        while True:
            data = await ws.receive_json()
            user_text = data.get("text", "")
            total = sum(cumulative_stats.values()) or 1.0
            percentages = {e: round(cumulative_stats[e] / total, 3) for e in EMOTIONS}
            
            prompt_template = f"""
            User message: {user_text}\nEmotion context: {percentages}\nRespond empathetically:
            """
            # --- PROMPT ENDS HERE ---
            # Fixed Ollama chat call
            response = await run_in_threadpool(
                ollama.chat,
                model='llama2:latest',  # Specify your model here
                messages=[{
                    'role': 'user',
                    'content': prompt_template
                }]
            )
            
            # Extract AI response
            ai_text = response['message']['content']
            await ws.send_json({"response": ai_text})
    except WebSocketDisconnect:
        print("💔 WebSocket connection closed: /ws/chat")
    except Exception as e:
        print(f"Chat error: {e}")
        await ws.send_json({"response": "Sorry, I encountered an error"})

# --- Static Files Mount (DEFINED LAST) ---
# This serves your index.html, app.js, and style.css
# It acts as a catch-all and must come after specific routes like WebSockets.
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)

# --- Run the App ---
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )