// Elements
const videoEl = document.getElementById("video");
const canvasEl = document.getElementById("hidden-canvas");
const ctx = canvasEl.getContext("2d");

const chatWindow = document.getElementById("chat-window");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");

// Setup video preview by capturing canvas stream
const stream = canvasEl.captureStream(30);
videoEl.srcObject = stream;

// Chart.js Bar Chart
const emotionCtx = document
  .getElementById("emotion-chart")
  .getContext("2d");
const labels = ["angry","disgust","fear","happy","sad","surprise","neutral"];
const chart = new Chart(emotionCtx, {
  type: "bar",
  data: {
    labels,
    datasets: [{
      label: "Confidence",
      data: new Array(labels.length).fill(0),
      backgroundColor: "rgba(54, 162, 235, 0.7)"
    }]
  },
  options: {
    animation: false,
    scales: { y: { beginAtZero: true, max: 1 } }
  }
});

// WebSocket: video frames
const wsVideo = new WebSocket(`ws://${location.host}/ws/video`);
wsVideo.binaryType = "arraybuffer";
wsVideo.onmessage = ({ data }) => {
  const blob = new Blob([data], { type: "image/jpeg" });
  const img = new Image();
  img.onload = () => {
    canvasEl.width = img.width;
    canvasEl.height = img.height;
    ctx.drawImage(img, 0, 0);
    URL.revokeObjectURL(img.src);
  };
  img.src = URL.createObjectURL(blob);
};

// WebSocket: emotion data
const wsEmotion = new WebSocket(`ws://${location.host}/ws/emotion`);
wsEmotion.onmessage = ({ data }) => {
  const emotions = JSON.parse(data);
  chart.data.datasets[0].data = labels.map(l => emotions[l] || 0);
  chart.update();
};

// WebSocket: chat
const wsChat = new WebSocket(`ws://${location.host}/ws/chat`);
wsChat.onmessage = ({ data }) => {
  const { response } = JSON.parse(data);
  const p = document.createElement("p");
  p.textContent = `AI: ${response}`;
  chatWindow.appendChild(p);
  chatWindow.scrollTop = chatWindow.scrollHeight;
};

sendBtn.onclick = () => {
  const text = chatInput.value.trim();
  if (!text) return;
  // display user message
  const p = document.createElement("p");
  p.textContent = `You: ${text}`;
  chatWindow.appendChild(p);
  wsChat.send(JSON.stringify({ text }));
  chatInput.value = "";
};
