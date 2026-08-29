const form = document.querySelector("#render-form");
const fileInput = document.querySelector("#source-file");
const dropZone = document.querySelector("#drop-zone");
const fileSummary = document.querySelector("#file-summary");
const fileName = document.querySelector("#file-name");
const fileMeta = document.querySelector("#file-meta");
const clearFileButton = document.querySelector("#clear-file");
const livePhotoHelp = document.querySelector("#live-photo-help");
const chooseVideoAgainButton = document.querySelector("#choose-video-again");
const submitButton = document.querySelector("#submit-button");
const submitLabel = document.querySelector("#submit-label");
const sampleButton = document.querySelector("#sample-button");
const outputField = document.querySelector("#output-field");
const qualityField = document.querySelector("#quality-field");
const photoModeNote = document.querySelector("#photo-mode-note");
const samplePreview = document.querySelector("#sample-preview");
const videoPreview = document.querySelector("#video-preview");
const imagePreview = document.querySelector("#image-preview");
const previewFallback = document.querySelector("#preview-fallback");
const previewState = document.querySelector("#preview-state");
const stageIndex = document.querySelector("#stage-index");
const stageTitle = document.querySelector("#stage-title");
const jobStatus = document.querySelector("#job-status");
const statusTitle = document.querySelector("#status-title");
const statusDetail = document.querySelector("#status-detail");
const statusPercent = document.querySelector("#status-percent");
const progressBar = document.querySelector("#progress-bar");
const resultSection = document.querySelector("#result-section");
const resultGrid = document.querySelector("#result-grid");
const historyList = document.querySelector("#history-list");
const accessUrl = document.querySelector("#access-url");
const copyUrlButton = document.querySelector("#copy-url");

let selectedFile = null;
let selectedSourceType = null;
let objectUrl = null;
let pollTimer = null;
let activeJobId = null;
let selectionToken = 0;

const MAX_PHOTO_EDGE = 4096;
const JPEG_QUALITY = 0.95;

const variantNames = {
  "motion-cover": "先锋动态封面",
  "break-frame": "斜切破版",
  "time-slices": "三时态切片",
  all: "三版同时生成",
};

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function revokeObjectUrl() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
}

function updateSourceMode() {
  const isPhoto = selectedSourceType === "photo";
  submitLabel.textContent = isPhoto ? "只生成静态 JPG" : "开始生成动态封面";
  photoModeNote.hidden = !isPhoto;
  outputField.classList.toggle("is-disabled", isPhoto);
  qualityField.classList.toggle("is-disabled", isPhoto);
}

function canvasToJpeg(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("浏览器没有生成可上传的 JPEG"));
      }
    }, "image/jpeg", JPEG_QUALITY);
  });
}

async function preparePhotoFile(image, sourceFile) {
  const sourceWidth = image.naturalWidth;
  const sourceHeight = image.naturalHeight;
  if (!sourceWidth || !sourceHeight) {
    throw new Error("浏览器没有读到照片尺寸");
  }

  const scale = Math.min(1, MAX_PHOTO_EDGE / Math.max(sourceWidth, sourceHeight));
  const width = Math.max(1, Math.round(sourceWidth * scale));
  const height = Math.max(1, Math.round(sourceHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { alpha: false });
  if (!context) throw new Error("浏览器无法建立照片处理画布");

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  const jpegBlob = await canvasToJpeg(canvas);
  canvas.width = 1;
  canvas.height = 1;

  const baseName = sourceFile.name.replace(/\.[^.]+$/, "") || "photo";
  const file = new File([jpegBlob], `${baseName}.jpg`, {
    type: "image/jpeg",
    lastModified: sourceFile.lastModified || Date.now(),
  });
  return { file, width, height };
}

function resetPreview() {
  revokeObjectUrl();
  videoPreview.pause();
  videoPreview.removeAttribute("src");
  imagePreview.onload = null;
  imagePreview.onerror = null;
  imagePreview.removeAttribute("src");
  imagePreview.classList.remove("static-source");
  videoPreview.hidden = true;
  imagePreview.hidden = true;
  previewFallback.hidden = true;
  samplePreview.hidden = false;
  samplePreview.play().catch(() => {});
  previewState.textContent = "示例";
  stageIndex.textContent = "COVER / 001";
  stageTitle.textContent = "夜色上篮";
}

function clearSelectedFile() {
  selectionToken += 1;
  selectedFile = null;
  selectedSourceType = null;
  fileInput.value = "";
  fileSummary.hidden = true;
  livePhotoHelp.hidden = true;
  jobStatus.hidden = true;
  updateSourceMode();
  setBusy(false);
  resetPreview();
}

function showStaticImagePreview(file, token) {
  selectedFile = null;
  selectedSourceType = "photo";
  updateSourceMode();
  setBusy(false);
  fileName.textContent = file.name;
  fileMeta.textContent = `${file.type || "静态照片"} · ${formatBytes(file.size)} · 正在准备`;
  fileSummary.hidden = false;
  livePhotoHelp.hidden = false;

  revokeObjectUrl();
  objectUrl = URL.createObjectURL(file);
  samplePreview.pause();
  samplePreview.hidden = true;
  videoPreview.pause();
  videoPreview.hidden = true;
  imagePreview.classList.add("static-source");
  imagePreview.hidden = false;
  previewFallback.hidden = true;
  imagePreview.onload = async () => {
    if (token !== selectionToken) return;
    imagePreview.hidden = false;
    previewFallback.hidden = true;
    statusTitle.textContent = "正在准备高清照片";
    statusDetail.textContent = "在手机本机转换为兼容的 JPEG，不会上传到其他服务器";
    statusPercent.textContent = "处理中";
    progressBar.style.width = "36%";
    progressBar.style.background = "var(--blue)";
    try {
      const prepared = await preparePhotoFile(imagePreview, file);
      if (token !== selectionToken) return;
      selectedFile = prepared.file;
      fileMeta.textContent = `${file.type || "静态照片"} · ${formatBytes(file.size)} · ${prepared.width} × ${prepared.height}`;
      statusTitle.textContent = "照片已就绪";
      statusDetail.textContent = "当前文件没有动作，只能生成静态 JPG；要生成动图，请先把 Live Photo 存储为视频";
      statusPercent.textContent = "仅静态";
      progressBar.style.width = "100%";
      progressBar.style.background = "var(--acid)";
      setBusy(false);
    } catch (error) {
      if (token !== selectionToken) return;
      selectedFile = null;
      showFailure(`${error.message}，请先在照片 App 中导出为 JPG 或视频`);
    }
  };
  imagePreview.onerror = () => {
    if (token !== selectionToken) return;
    selectedFile = null;
    imagePreview.hidden = true;
    previewFallback.hidden = false;
    fileMeta.textContent = `${file.type || "静态照片"} · ${formatBytes(file.size)} · 无法解码`;
    showFailure("当前浏览器不能读取这种照片格式，请先在照片 App 中导出为 JPG 或视频");
  };
  imagePreview.src = objectUrl;

  previewState.textContent = "静态预览";
  stageIndex.textContent = "PHOTO / STATIC";
  stageTitle.textContent = file.name.replace(/\.[^.]+$/, "").slice(0, 24);
  jobStatus.hidden = false;
  statusTitle.textContent = "正在读取照片";
  statusDetail.textContent = "预览成功后即可生成静态 JPG；动态封面仍需选择视频或 GIF";
  statusPercent.textContent = "准备中";
  progressBar.style.width = "0";
  progressBar.style.background = "var(--blue)";
}

function setSelectedFile(file) {
  const allowed = [".gif", ".mp4", ".mov", ".m4v", ".webm"];
  const staticImages = [".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp"];
  const lowerName = file.name.toLowerCase();
  const token = ++selectionToken;
  selectedFile = null;
  selectedSourceType = null;
  updateSourceMode();
  submitButton.disabled = true;
  const isStaticImage = staticImages.some((extension) => lowerName.endsWith(extension))
    || (file.type.startsWith("image/") && file.type !== "image/gif");
  if (file.size > 100 * 1024 * 1024) {
    showFailure("文件超过 100 MB，请先裁短或压缩");
    return;
  }
  if (isStaticImage) {
    showStaticImagePreview(file, token);
    return;
  }
  if (!allowed.some((extension) => lowerName.endsWith(extension))) {
    showFailure("请选择 GIF、MP4、MOV、M4V 或 WebM 文件");
    return;
  }
  selectedFile = file;
  selectedSourceType = lowerName.endsWith(".gif") || file.type === "image/gif" ? "gif" : "video";
  updateSourceMode();
  livePhotoHelp.hidden = true;
  fileName.textContent = file.name;
  fileMeta.textContent = `${file.type || "未知媒体类型"} · ${formatBytes(file.size)}`;
  fileSummary.hidden = false;
  submitButton.disabled = false;

  revokeObjectUrl();
  objectUrl = URL.createObjectURL(file);
  samplePreview.pause();
  samplePreview.hidden = true;
  const isGif = selectedSourceType === "gif";
  videoPreview.pause();
  videoPreview.removeAttribute("src");
  imagePreview.removeAttribute("src");
  videoPreview.hidden = isGif;
  imagePreview.hidden = !isGif;
  imagePreview.classList.remove("static-source");
  imagePreview.onload = null;
  imagePreview.onerror = null;
  previewFallback.hidden = true;
  if (isGif) {
    imagePreview.src = objectUrl;
  } else {
    videoPreview.src = objectUrl;
    videoPreview.play().catch(() => {});
  }
  previewState.textContent = "动态待生成";
  stageIndex.textContent = isGif ? "GIF / INPUT" : "VIDEO / INPUT";
  stageTitle.textContent = file.name.replace(/\.[^.]+$/, "").slice(0, 24);
  jobStatus.hidden = false;
  statusTitle.textContent = isGif ? "GIF 动态图片已就绪" : "视频已就绪";
  statusDetail.textContent = isGif
    ? "已识别为会动的 GIF，可生成动态 GIF 或 MP4"
    : "已识别为视频，可生成真正会动的 MP4 或 GIF";
  statusPercent.textContent = "动态输入";
  progressBar.style.width = "100%";
  progressBar.style.background = "var(--acid)";
  setBusy(false);
}

function currentOptions() {
  return {
    variant: document.querySelector("#variant").value,
    output_format: form.querySelector('input[name="output_format"]:checked')?.value || "mp4",
    quality: form.querySelector('input[name="quality"]:checked')?.value || "high",
  };
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy || !selectedFile;
  sampleButton.disabled = isBusy;
  fileInput.disabled = isBusy;
  document.querySelector("#variant").disabled = isBusy;
  outputField.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.disabled = isBusy || selectedSourceType === "photo";
  });
  qualityField.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.disabled = isBusy || selectedSourceType === "photo";
  });
}

function showFailure(message) {
  jobStatus.hidden = false;
  statusTitle.textContent = "没有生成成功";
  statusDetail.textContent = message;
  statusPercent.textContent = "失败";
  progressBar.style.width = "100%";
  progressBar.style.background = "var(--signal)";
  setBusy(false);
}

function showJob(job) {
  jobStatus.hidden = false;
  statusTitle.textContent = {
    queued: "任务已进入队列",
    running: "正在本机生成",
    completed: "生成完成",
    failed: "生成失败",
  }[job.status] || "正在处理";
  statusDetail.textContent = job.error || job.phase || "等待状态更新";
  statusPercent.textContent = `${job.progress || 0}%`;
  progressBar.style.background = job.status === "failed" ? "var(--signal)" : "var(--acid)";
  progressBar.style.width = `${Math.max(0, Math.min(100, job.progress || 0))}%`;
  previewState.textContent = job.status === "completed" ? "已完成" : "生成中";

  if (job.status === "completed") {
    setBusy(false);
    renderResults(job.outputs || []);
    loadHistory();
  } else if (job.status === "failed") {
    setBusy(false);
    loadHistory();
  }
}

function makeMedia(output) {
  if (output.type === "video") {
    const video = document.createElement("video");
    video.src = output.url;
    video.poster = output.poster_url || "";
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.controls = true;
    return video;
  }
  const image = document.createElement("img");
  image.src = output.url;
  image.alt = `${output.label} ${output.type === "gif" ? "动态图片" : "静态封面"}`;
  image.loading = "lazy";
  return image;
}

function outputKind(output) {
  return {
    video: "会动 · MP4 视频",
    gif: "会动 · GIF 动态图片",
    cover: "静态 · JPG 封面",
  }[output.type] || output.type;
}

function saveInstruction(output) {
  if (output.type === "video") {
    return "iPhone：打开视频后点 Safari 分享按钮，再选“存储视频”。";
  }
  if (output.type === "gif") {
    return "iPhone：打开动图后长按或点分享，再选“存储图像”；回到“照片”确认仍会动。";
  }
  return "iPhone：打开图片后长按，再选“存储到照片”。";
}

function renderResults(outputs) {
  resultGrid.replaceChildren();
  outputs.forEach((output) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.append(makeMedia(output));

    const copy = document.createElement("div");
    copy.className = "result-copy";
    const title = document.createElement("h3");
    title.textContent = output.label;
    const meta = document.createElement("p");
    meta.className = "output-kind";
    meta.textContent = `${outputKind(output)} · ${formatBytes(output.bytes)}`;

    const actions = document.createElement("div");
    actions.className = "result-actions";
    const open = document.createElement("a");
    open.className = "open-output-button";
    open.href = output.url;
    open.target = "_blank";
    open.rel = "noopener";
    open.textContent = output.type === "video"
      ? "打开视频并保存"
      : output.type === "gif"
        ? "打开动图并保存"
        : "打开图片并保存";
    const download = document.createElement("a");
    download.className = "file-download-button";
    download.href = output.download_url;
    download.download = output.name;
    download.textContent = "下载到“文件”";
    actions.append(open, download);

    const instruction = document.createElement("p");
    instruction.className = "save-instruction";
    instruction.textContent = saveInstruction(output);
    copy.append(title, meta, actions, instruction);
    card.append(copy);
    resultGrid.append(card);
  });
  resultSection.hidden = false;
  resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = { error: `本地服务返回了无法读取的响应（${response.status}）` };
  }
  if (!response.ok) throw new Error(payload.error || `请求失败（${response.status}）`);
  return payload;
}

function uploadRequest(payload) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/jobs");
    request.responseType = "json";
    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      jobStatus.hidden = false;
      statusTitle.textContent = "正在传到这台电脑";
      statusDetail.textContent = `${formatBytes(event.loaded)} / ${formatBytes(event.total)}`;
      statusPercent.textContent = `${percent}%`;
      progressBar.style.background = "var(--blue)";
      progressBar.style.width = `${percent}%`;
    });
    request.addEventListener("load", () => {
      const response = request.response || {};
      if (request.status >= 200 && request.status < 300) {
        resolve(response);
      } else {
        reject(new Error(response.error || `上传失败（${request.status}）`));
      }
    });
    request.addEventListener("error", () => {
      reject(new Error("局域网上传中断，请确认手机和电脑仍连接同一 Wi-Fi"));
    });
    request.addEventListener("timeout", () => {
      reject(new Error("局域网上传超时，请重新选择较短素材"));
    });
    request.timeout = 10 * 60 * 1000;
    request.send(payload);
  });
}

async function pollJob(jobId) {
  clearTimeout(pollTimer);
  try {
    const job = await apiRequest(`/api/jobs/${jobId}`);
    if (jobId !== activeJobId) return;
    showJob(job);
    if (job.status === "queued" || job.status === "running") {
      pollTimer = setTimeout(() => pollJob(jobId), 1000);
    }
  } catch (error) {
    showFailure(error.message);
  }
}

function beginJob(job) {
  activeJobId = job.id;
  resultSection.hidden = true;
  setBusy(true);
  showJob(job);
  pollJob(job.id);
}

async function submitUpload(event) {
  event.preventDefault();
  if (!selectedFile) return;
  const payload = new FormData();
  const options = currentOptions();
  payload.append("file", selectedFile, selectedFile.name);
  payload.append("variant", options.variant);
  payload.append("output_format", selectedSourceType === "photo" ? "jpg" : options.output_format);
  payload.append("quality", selectedSourceType === "photo" ? "high" : options.quality);
  try {
    setBusy(true);
    const job = await uploadRequest(payload);
    beginJob(job);
  } catch (error) {
    showFailure(error.message);
  }
}

async function submitSample() {
  try {
    const options = currentOptions();
    setBusy(true);
    const job = await apiRequest("/api/jobs/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    stageIndex.textContent = "VIDEO / SAMPLE";
    stageTitle.textContent = variantNames[job.variant] || "示例生成";
    beginJob(job);
  } catch (error) {
    showFailure(error.message);
  }
}

async function loadHistory() {
  try {
    const payload = await apiRequest("/api/jobs");
    historyList.replaceChildren();
    if (!payload.jobs.length) {
      const empty = document.createElement("p");
      empty.className = "empty-history";
      empty.textContent = "还没有本地任务。上传素材或使用示例开始。";
      historyList.append(empty);
      return;
    }
    payload.jobs.forEach((job) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "history-item";
      const name = document.createElement("strong");
      name.textContent = job.original_name;
      const time = document.createElement("time");
      time.textContent = new Date(job.created_at).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
      const state = document.createElement("span");
      state.className = job.status === "completed" ? "done" : job.status === "failed" ? "failed" : "";
      state.textContent = {
        queued: "排队中",
        running: `${job.progress || 0}%`,
        completed: "已完成",
        failed: "失败",
      }[job.status] || job.status;
      button.append(name, time, state);
      button.addEventListener("click", () => {
        activeJobId = job.id;
        showJob(job);
        if (job.status === "completed") renderResults(job.outputs || []);
        if (job.status === "queued" || job.status === "running") pollJob(job.id);
      });
      historyList.append(button);
    });
  } catch (error) {
    historyList.textContent = error.message;
  }
}

async function loadAccessUrl() {
  try {
    const health = await apiRequest("/api/health");
    const lanUrl = (health.access_urls || []).find((url) => !url.includes("127.0.0.1"));
    accessUrl.textContent = lanUrl || window.location.origin;
  } catch {
    accessUrl.textContent = window.location.origin;
  }
}

copyUrlButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(accessUrl.textContent);
    copyUrlButton.textContent = "已复制";
    setTimeout(() => {
      copyUrlButton.textContent = "复制";
    }, 1600);
  } catch {
    copyUrlButton.textContent = "请长按地址";
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files?.[0]) setSelectedFile(fileInput.files[0]);
});

dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
});

dropZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) setSelectedFile(file);
});

clearFileButton.addEventListener("click", clearSelectedFile);
chooseVideoAgainButton.addEventListener("click", () => fileInput.click());
form.addEventListener("submit", submitUpload);
sampleButton.addEventListener("click", submitSample);
window.addEventListener("beforeunload", revokeObjectUrl);

loadHistory();
loadAccessUrl();
