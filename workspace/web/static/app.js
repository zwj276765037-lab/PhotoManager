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
const sampleButton = document.querySelector("#sample-button");
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
let objectUrl = null;
let pollTimer = null;
let activeJobId = null;

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
  selectedFile = null;
  fileInput.value = "";
  fileSummary.hidden = true;
  submitButton.disabled = true;
  livePhotoHelp.hidden = true;
  jobStatus.hidden = true;
  resetPreview();
}

function showStaticImagePreview(file) {
  selectedFile = null;
  submitButton.disabled = true;
  fileName.textContent = file.name;
  fileMeta.textContent = `${file.type || "静态照片"} · ${formatBytes(file.size)} · 已本机预览`;
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
  imagePreview.onload = () => {
    imagePreview.hidden = false;
    previewFallback.hidden = true;
  };
  imagePreview.onerror = () => {
    imagePreview.hidden = true;
    previewFallback.hidden = false;
  };
  imagePreview.src = objectUrl;

  previewState.textContent = "静态预览";
  stageIndex.textContent = "PHOTO / STATIC";
  stageTitle.textContent = file.name.replace(/\.[^.]+$/, "").slice(0, 24);
  jobStatus.hidden = false;
  statusTitle.textContent = "照片预览已就绪";
  statusDetail.textContent = "当前是静态文件；请将 Live Photo 存储为视频后再生成动态封面";
  statusPercent.textContent = "需转视频";
  progressBar.style.width = "0";
  progressBar.style.background = "var(--blue)";
  setBusy(false);
}

function setSelectedFile(file) {
  const allowed = [".gif", ".mp4", ".mov", ".m4v", ".webm"];
  const staticImages = [".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp"];
  const lowerName = file.name.toLowerCase();
  const isStaticImage = staticImages.some((extension) => lowerName.endsWith(extension))
    || (file.type.startsWith("image/") && file.type !== "image/gif");
  if (isStaticImage) {
    showStaticImagePreview(file);
    return;
  }
  if (!allowed.some((extension) => lowerName.endsWith(extension))) {
    showFailure("请选择 GIF、MP4、MOV、M4V 或 WebM 文件");
    return;
  }
  if (file.size > 100 * 1024 * 1024) {
    showFailure("文件超过 100 MB，请先裁短或压缩");
    return;
  }

  selectedFile = file;
  livePhotoHelp.hidden = true;
  fileName.textContent = file.name;
  fileMeta.textContent = `${file.type || "未知媒体类型"} · ${formatBytes(file.size)}`;
  fileSummary.hidden = false;
  submitButton.disabled = false;

  revokeObjectUrl();
  objectUrl = URL.createObjectURL(file);
  samplePreview.pause();
  samplePreview.hidden = true;
  const isGif = lowerName.endsWith(".gif") || file.type === "image/gif";
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
  previewState.textContent = "待生成";
  stageIndex.textContent = isGif ? "GIF / INPUT" : "VIDEO / INPUT";
  stageTitle.textContent = file.name.replace(/\.[^.]+$/, "").slice(0, 24);
}

function currentOptions() {
  return {
    variant: document.querySelector("#variant").value,
    output_format: new FormData(form).get("output_format"),
    quality: new FormData(form).get("quality"),
  };
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy || !selectedFile;
  sampleButton.disabled = isBusy;
  fileInput.disabled = isBusy;
  document.querySelector("#variant").disabled = isBusy;
  form.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.disabled = isBusy;
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
    meta.textContent = `${output.name.split(".").pop().toUpperCase()} · ${formatBytes(output.bytes)}`;
    const download = document.createElement("a");
    download.className = "download-button";
    download.href = output.download_url;
    download.textContent = "保存到本机";
    copy.append(title, meta, download);
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
  payload.append("output_format", options.output_format);
  payload.append("quality", options.quality);
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
