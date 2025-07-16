import asyncio
import signal
import cv2
import numpy as np
from fer import FER
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from anyio import run_in_threadpool
import ollama

app = FastAPI()

# Mount frontend static files
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend"
)

# Constants and Globals
EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
cumulative_stats = {e: 0.0 for e in EMOTIONS}
latest_frame = None
latest_emotions = {e: 0.0 for e in EMOTIONS}
shutdown_event = asyncio.Event()

# Initialize camera and emotion detector
cap = cv2.VideoCapture(0)
detector = FER(mtcnn=True)

async def capture_frames():
    """
    Continuously capture frames from webcam, detect emotions,
    update latest_frame/latest_emotions and cumulative_stats.
    """
    global latest_frame, latest_emotions, cumulative_stats
    while not shutdown_event.is_set():
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue

        latest_frame = frame

        # Run FER detection in thread pool
        results = await run_in_threadpool(detector.detect_emotions, frame)

        if results:
            emotions = results[0]["emotions"]
        else:
            emotions = {e: 0.0 for e in EMOTIONS}

        latest_emotions = emotions
        for e in EMOTIONS:
            cumulative_stats[e] += emotions.get(e, 0.0)

        # ~30 FPS
        await asyncio.sleep(0.03)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(capture_frames())

@app.on_event("shutdown")
def on_shutdown():
    shutdown_event.set()
    cap.release()

@app.websocket("/ws/video")
async def ws_video(ws: WebSocket):
    """
    Streams JPEG-encoded frames over WebSocket.
    """
    await ws.accept()
    try:
        while True:
            if latest_frame is not None:
                # Encode as JPEG
                ret, jpeg = cv2.imencode(".jpg", latest_frame)
                if ret:
                    await ws.send_bytes(jpeg.tobytes())
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/emotion")
async def ws_emotion(ws: WebSocket):
    """
    Streams the latest emotion confidences as JSON.
    """
    await ws.accept()
    try:
        while True:
            await ws.send_json(latest_emotions)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/chat")
"""
async def ws_chat(ws: WebSocket):
    ""
    Accepts chat JSON {text:str}, computes normalized
    emotion percentages from cumulative_stats, calls ollama.chat,
    and returns the AI-modified text.
    ""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            user_text = data.get("text", "")

            # Compute normalized emotion percentages
            total = sum(cumulative_stats.values()) or 1.0
            percentages = {
                e: round(cumulative_stats[e] / total, 3) for e in EMOTIONS
            }

            # Call ollama.chat in thread pool
            def call_ollama():
                # assume ollama.chat returns a dict with 'text'
                return ollama.chat(user_text, percentages)

            response = await run_in_threadpool(call_ollama)

            # Extract text from response
            if isinstance(response, dict) and "text" in response:
                ai_text = response["text"]
            else:
                ai_text = str(response)

            await ws.send_json({"response": ai_text})

    except WebSocketDisconnect:
        pass
"""
async def ws_chat(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data     = await ws.receive_json()
            user_txt = data.get("text", "")

            # normalize
            total = sum(cumulative_stats.values()) or 1.0
            percentages = { e: round(cumulative_stats[e] / total, 3)
                            for e in EMOTIONS }

            # build a prompt that tells the model what to do with your emotions
            system_prompt = (
                "You are an empathetic assistant. "
                "Adjust your tone and wording according to these emotion levels:\n"
                + "\n".join(f"{e}: {percentages[e]*100:.1f}%" for e in EMOTIONS)
            )

            def call_ollama():
                # pass in model & multi-role prompt
                return ollama.chat(
                    model="llama2",                # or your preferred model
                    prompt=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_txt}
                    ]
                )

            # run blocking call off the event loop
            ai_response = await run_in_threadpool(call_ollama)

            # if SDK returns a dict/object, extract the text; else treat as str
            if isinstance(ai_response, dict) and "text" in ai_response:
                out = ai_response["text"]
            else:
                out = str(ai_response)

            await ws.send_json({"response": out})

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
