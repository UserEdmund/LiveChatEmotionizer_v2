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
const emotionCtx = document.getElementById("emotion-chart").getContext("2d");
const labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"];
const backgroundColors = [
  'rgba(176, 26, 58, 0.7)', // angry
  'rgba(75, 192, 192, 0.7)', // disgust
  'rgba(255, 206, 86, 0.7)', // fear
  'rgba(230, 75, 24, 1)', // happy
  'rgba(153, 102, 255, 0.7)', // sad
  'rgba(255, 159, 64, 0.7)', // surprise
  'rgba(201, 203, 207, 0.7)' // neutral
];
const chart = new Chart(emotionCtx, {
  type: "bar",
  data: {
    labels,
    datasets: [{
      label: "Confidence",
      data: new Array(labels.length).fill(0),
      backgroundColor: backgroundColors,
      borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
      borderWidth: 1
    }]
  },
  options: {
    animation: false,
    scales: { y: { beginAtZero: true, max: 1 } },
    maintainAspectRatio: false
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
let currentEmotions = {};
const wsEmotion = new WebSocket(`ws://${location.host}/ws/emotion`);
wsEmotion.onmessage = ({ data }) => {
  currentEmotions = JSON.parse(data);
  chart.data.datasets[0].data = labels.map(l => currentEmotions[l] || 0);
  chart.update();
};

// WebSocket: chat
const wsChat = new WebSocket(`ws://${location.host}/ws/chat`);
wsChat.onmessage = ({ data }) => {
  const { response } = JSON.parse(data);
  const p = document.createElement("p");
  p.className = "text-start bg-secondary text-white rounded p-2";
  p.textContent = `AI: ${response}`;
  chatWindow.appendChild(p);
  chatWindow.scrollTop = chatWindow.scrollHeight;
};

// Function to get dominant emotion
function getDominantEmotion(emotions) {
  let maxEmotion = "";
  let maxValue = 0;
  for (const [emotion, value] of Object.entries(emotions)) {
    if (value > maxValue) {
      maxValue = value;
      maxEmotion = emotion;
    }
  }
  return maxEmotion;
}

// Send button handler
sendBtn.onclick = () => {
  const text = chatInput.value.trim();
  if (!text) return;
  const dominant = getDominantEmotion(currentEmotions);
  const p = document.createElement("p");
  // FIX: Removed the non-standard "citt" and "bg" classes. Styling is handled by style.css.
  p.className = "text-end rounded p-2";
  p.textContent = `You: ${text} (${dominant})`;
  chatWindow.appendChild(p);
  wsChat.send(JSON.stringify({ text }));
  chatInput.value = "";
  chatWindow.scrollTop = chatWindow.scrollHeight;
};

// FIX: Removed the extra closing brace that was here.