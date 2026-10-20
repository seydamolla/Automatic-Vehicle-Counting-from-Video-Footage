const input = document.querySelector('#videos');
const fileList = document.querySelector('#file-list');
const video = document.querySelector('#preview-video');
const empty = document.querySelector('#preview-empty');
const stage = document.querySelector('#stage');
const canvas = document.querySelector('#line-canvas');
const ctx = canvas.getContext('2d');
const runButton = document.querySelector('#run');
const statusBox = document.querySelector('#status');
const progress = document.querySelector('#progress');
const confidence = document.querySelector('#confidence');
const confidenceValue = document.querySelector('#confidence-value');
const resultsSection = document.querySelector('#results-section');
const resultsBox = document.querySelector('#results');

let objectUrl = null;
let line = { x1: 0.1, y1: 0.65, x2: 0.9, y2: 0.65 };
let dragging = null;

function resizeCanvas() {
  const rect = stage.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(rect.width * scale);
  canvas.height = Math.round(rect.height * scale);
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  drawLine();
}

function drawLine() {
  const width = stage.clientWidth;
  const height = stage.clientHeight;
  ctx.clearRect(0, 0, width, height);
  const a = { x: line.x1 * width, y: line.y1 * height };
  const b = { x: line.x2 * width, y: line.y2 * height };
  ctx.lineWidth = 4;
  ctx.strokeStyle = '#ffd24a';
  ctx.shadowColor = 'rgba(0,0,0,.55)';
  ctx.shadowBlur = 5;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
  ctx.shadowBlur = 0;
  [a, b].forEach((point) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 9, 0, Math.PI * 2);
    ctx.fillStyle = '#ffd24a';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#0b3855';
    ctx.stroke();
  });
}

function pointerPosition(event) {
  const rect = canvas.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top, width: rect.width, height: rect.height };
}

canvas.addEventListener('pointerdown', (event) => {
  const point = pointerPosition(event);
  const endpoints = [
    ['start', line.x1 * point.width, line.y1 * point.height],
    ['end', line.x2 * point.width, line.y2 * point.height],
  ];
  dragging = endpoints.sort((a, b) => Math.hypot(point.x - a[1], point.y - a[2]) - Math.hypot(point.x - b[1], point.y - b[2]))[0][0];
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener('pointermove', (event) => {
  if (!dragging) return;
  const point = pointerPosition(event);
  const x = Math.min(1, Math.max(0, point.x / point.width));
  const y = Math.min(1, Math.max(0, point.y / point.height));
  if (dragging === 'start') { line.x1 = x; line.y1 = y; } else { line.x2 = x; line.y2 = y; }
  drawLine();
});

canvas.addEventListener('pointerup', () => { dragging = null; });
window.addEventListener('resize', resizeCanvas);
confidence.addEventListener('input', () => { confidenceValue.value = confidence.value; });

input.addEventListener('change', () => {
  const files = [...input.files].slice(0, 5);
  fileList.innerHTML = files.map((file) => `<li><span>${escapeHtml(file.name)}</span><small>${formatSize(file.size)}</small></li>`).join('');
  if (!files.length) return;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(files[0]);
  video.src = objectUrl;
  video.style.display = 'block';
  empty.style.display = 'none';
  video.addEventListener('loadedmetadata', resizeCanvas, { once: true });
});

runButton.addEventListener('click', async () => {
  const files = [...input.files].slice(0, 5);
  if (!files.length) return setStatus('Önce en az bir video seçin.', true);
  const form = new FormData();
  files.forEach((file) => form.append('files', file));
  const fields = {
    line_x1: line.x1,
    line_y1: line.y1,
    line_x2: line.x2,
    line_y2: line.y2,
    confidence: confidence.value,
    model_name: document.querySelector('#model').value,
  };
  Object.entries(fields).forEach(([key, value]) => form.append(key, value));
  runButton.disabled = true;
  progress.hidden = false;
  resultsSection.hidden = true;
  setStatus(`${files.length} video işleniyor. Bu pencereyi kapatmayın.`);
  try {
    const response = await fetch('/api/process', { method: 'POST', body: form });
    const payload = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload.detail)
        ? payload.detail.map((item) => item.msg).join(' · ')
        : payload.detail;
      throw new Error(detail || 'İşlem tamamlanamadı.');
    }
    renderResults(payload.results);
    setStatus('Sayım tamamlandı. Video ve CSV çıktıları hazır.');
  } catch (error) {
    setStatus(error.message || 'Beklenmeyen bir hata oluştu.', true);
  } finally {
    runButton.disabled = false;
    progress.hidden = true;
  }
});

function renderResults(results) {
  resultsBox.innerHTML = results.map((item) => `
    <article class="result">
      <video src="${item.annotated_url}" controls preload="metadata"></video>
      <div class="result__body">
        <h3>${escapeHtml(item.source_name)}</h3>
        <div class="metrics">
          <div class="metric"><b>${item.positive_count}</b><span>Pozitif yön</span></div>
          <div class="metric"><b>${item.negative_count}</b><span>Negatif yön</span></div>
          <div class="metric"><b>${item.total_count}</b><span>Toplam</span></div>
        </div>
        <p class="result__meta">${item.processed_frames} kare · ${item.processing_fps} işlem FPS</p>
        <div class="actions"><a href="${item.annotated_url}" download>İşaretli videoyu indir</a><a href="${item.csv_url}" download>CSV indir</a></div>
      </div>
    </article>`).join('');
  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setStatus(message, isError = false) { statusBox.textContent = message; statusBox.classList.toggle('error', isError); }
function formatSize(bytes) { return bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1048576).toFixed(1)} MB`; }
function escapeHtml(value) { const node = document.createElement('div'); node.textContent = value; return node.innerHTML; }

resizeCanvas();
