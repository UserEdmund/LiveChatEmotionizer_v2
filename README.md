# Live Chat Emotionizer_V2

A real-time emotion detection and chat application powered by **FastAPI**, **OpenCV**, **FER + MTCNN**, and an AI chat model.

---

## 📦 Prerequisites

- Python 3.8+
- Webcam connected
- ollama CLI / SDK configured with your AI model

---

## 🔧 Installation

**Clone the repo:**

```bash
git clone https://https://github.com/UserEdmund/LiveChatEmotionizer_v2.git
cd LiveChatEmotionizer_v2
```
**Install dependencies:**
```bash
pip install -r requirements.txt
```

## 🚀 Running the Application

**Start the FastAPI server:**
```bash
uvicorn backend.main:app --reload
```

**Open your browser and go to:**
```markdown
http://localhost:8000
```
📸 Allow webcam access if prompted 📊 See live video, emotion chart, and start chatting!
