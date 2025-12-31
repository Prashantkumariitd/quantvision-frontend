import "./style.css";

let isCalibrating = false;
let startX, startY, box;

function startCalibration() {
  if (isCalibrating) return;
  isCalibrating = true;

  const overlay = document.createElement("div");
  overlay.id = "calibration-overlay";
  overlay.style.position = "fixed";
  overlay.style.top = "0";
  overlay.style.left = "0";
  overlay.style.width = "100vw";
  overlay.style.height = "100vh";
  overlay.style.background = "rgba(0,0,0,0.35)";
  overlay.style.zIndex = "99999";
  overlay.style.cursor = "crosshair";

  document.body.appendChild(overlay);

  overlay.addEventListener("mousedown", (e) => {
    startX = e.clientX;
    startY = e.clientY;

    box = document.createElement("div");
    box.style.position = "absolute";
    box.style.border = "2px solid #10b981";
    box.style.background = "rgba(16,185,129,0.15)";
    overlay.appendChild(box);

    overlay.addEventListener("mousemove", draw);
    overlay.addEventListener("mouseup", finish);
  });
}

function draw(e) {
  const x = Math.min(e.clientX, startX);
  const y = Math.min(e.clientY, startY);
  const w = Math.abs(e.clientX - startX);
  const h = Math.abs(e.clientY - startY);

  Object.assign(box.style, {
    left: `${x}px`,
    top: `${y}px`,
    width: `${w}px`,
    height: `${h}px`
  });
}

async function finish() {
  const rect = box.getBoundingClientRect();

  const overlay = document.getElementById("calibration-overlay");
  overlay.removeEventListener("mousemove", draw);
  overlay.removeEventListener("mouseup", finish);
  overlay.remove();

  isCalibrating = false;

  await fetch("http://127.0.0.1:8000/calibrate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height
    })
  });

  alert("Calibration saved");
}

window.startCalibration = startCalibration;

import "./style.css";

document.querySelector("#app").innerHTML = `
<div class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">

  <!-- Header -->
  <header class="flex items-center justify-between px-10 py-6 border-b border-slate-700 backdrop-blur">
    <h1 class="text-3xl font-bold tracking-wide">QuantVision</h1>

    <div class="flex items-center gap-6 text-sm text-slate-300">
      <span class="hover:text-white cursor-pointer">Dashboard</span>
      <span class="hover:text-white cursor-pointer">Strategies</span>
      <span class="hover:text-white cursor-pointer">Risk</span>
      <span class="hover:text-white cursor-pointer">Execution</span>

      <button id="calibrateBtn"
        class="px-4 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition">
        Calibrate Screen
      </button>
    </div>
  </header>

  <!-- Main Grid -->
  <main class="grid grid-cols-12 gap-6 p-8">

    <!-- Strategy Panel -->
    <section class="col-span-3 bg-slate-900/70 rounded-xl p-6 shadow-xl border border-slate-700">
      <h2 class="text-lg font-semibold mb-4">Strategy Engine</h2>

      <div class="space-y-3 text-sm">
        <p>Market Regime: <span class="text-emerald-400">Bull · Low Vol</span></p>
        <p>Action: <span class="text-blue-400">BUY / LONG</span></p>
        <p>Confidence: <span class="text-yellow-400">0.92</span></p>
        <p>RSI: <span class="text-slate-300">38.0</span></p>
      </div>
    </section>

    <!-- Live Market -->
    <section class="col-span-6 bg-slate-900/70 rounded-xl p-6 shadow-xl border border-slate-700">
      <h2 class="text-lg font-semibold mb-4">Live Market Feed</h2>

      <div id="marketFeed"
        class="h-[420px] rounded-lg bg-slate-950 border border-slate-700 flex items-center justify-center text-slate-400">
        Waiting for vision ingestion...
      </div>
    </section>

    <!-- ML Panel -->
    <section class="col-span-3 bg-slate-900/70 rounded-xl p-6 shadow-xl border border-slate-700">
      <h2 class="text-lg font-semibold mb-4">ML Insight</h2>

      <div class="space-y-3 text-sm text-slate-300">
        <p>Pattern Confidence: 87%</p>
        <p>Trend Probability: 0.91</p>
        <p>Risk Score: 0.18</p>
        <p>Model Status: <span class="text-emerald-400">Active</span></p>
      </div>
    </section>

    <!-- Risk -->
    <section class="col-span-4 bg-slate-900/70 rounded-xl p-6 shadow-xl border border-slate-700">
      <h2 class="text-lg font-semibold mb-4">Risk & Portfolio</h2>

      <div class="space-y-2 text-sm text-slate-300">
        <p>Account Balance: ₹ 1,000,000</p>
        <p>Open Positions: 2</p>
        <p>Exposure: 18%</p>
        <p>Drawdown: 1.3%</p>
      </div>
    </section>

    <!-- Execution -->
    <section class="col-span-8 bg-slate-900/70 rounded-xl p-6 shadow-xl border border-slate-700">
      <h2 class="text-lg font-semibold mb-4">Execution Console</h2>

      <div class="h-[220px] bg-slate-950 rounded-lg p-4 text-xs text-slate-400 overflow-auto space-y-1">
        <p>> System online.</p>
        <p>> Awaiting trade signals...</p>
      </div>
    </section>

  </main>

</div>
`;



const ws = new WebSocket("ws://127.0.0.1:8000/ws/vision");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  document.querySelector("#market-feed").innerHTML = `
    <pre class="text-xs text-emerald-400">${JSON.stringify(data, null, 2)}</pre>
  `;

  fetch("http://127.0.0.1:8000/analyze_snapshot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(resp => {
    if (resp.signal) {
      document.querySelector("#strategy-content").innerHTML = `
        <p>Action: <b>${resp.signal.action}</b></p>
        <p>Confidence: ${resp.signal.confidence_score}</p>
        <p>Regime: ${resp.signal.market_regime}</p>
      `;
    }
  });
};
