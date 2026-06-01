#!/usr/bin/env node
import fs from "node:fs";
import fsp from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";

const REPO_ROOT = process.cwd();
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FRAMES_DIR = process.argv[2] || "/private/tmp/v3_product_demo_frames";
const OUTPUT = process.argv[3] || path.join(REPO_ROOT, "demo_artifacts", "v3_product_demo", "v3_epistemic_product_demo.webm");
const FPS = Number(process.argv[4] || 24);
const WIDTH = Number(process.argv[5] || 1920);
const HEIGHT = Number(process.argv[6] || 1080);
const BITRATE = Number(process.argv[7] || 9_000_000);

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function html(frameCount) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>V3 Demo Encoder</title>
  <style>
    body { margin: 0; background: #081018; color: white; font: 16px system-ui, sans-serif; }
    canvas { width: ${WIDTH}px; height: ${HEIGHT}px; display: block; }
    #status { position: fixed; left: 16px; bottom: 16px; padding: 8px 12px; background: rgba(0,0,0,.7); border-radius: 8px; }
  </style>
</head>
<body>
  <canvas id="canvas" width="${WIDTH}" height="${HEIGHT}"></canvas>
  <div id="status">Preparing encoder...</div>
  <script>
    const FRAME_COUNT = ${frameCount};
    const FPS = ${FPS};
    const WIDTH = ${WIDTH};
    const HEIGHT = ${HEIGHT};
    const BITRATE = ${BITRATE};
    const status = document.getElementById("status");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d", { alpha: false });

    function sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function loadImage(index) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error("Could not load frame " + index));
        image.src = "/frames/frame_" + String(index).padStart(5, "0") + ".jpg";
      });
    }

    function chooseMimeType() {
      const candidates = [
        "video/webm;codecs=vp9",
        "video/webm;codecs=vp8",
        "video/webm"
      ];
      return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || "";
    }

    async function run() {
      const first = await loadImage(0);
      ctx.drawImage(first, 0, 0, WIDTH, HEIGHT);
      const mimeType = chooseMimeType();
      if (!mimeType) throw new Error("No WebM MediaRecorder codec is available");
      const stream = canvas.captureStream(FPS);
      const recorder = new MediaRecorder(stream, {
        mimeType,
        videoBitsPerSecond: BITRATE
      });
      const chunks = [];
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size) chunks.push(event.data);
      };
      const stopped = new Promise((resolve) => {
        recorder.onstop = resolve;
      });
      recorder.start(1000);
      const start = performance.now();
      for (let index = 0; index < FRAME_COUNT; index += 1) {
        const image = index === 0 ? first : await loadImage(index);
        ctx.drawImage(image, 0, 0, WIDTH, HEIGHT);
        if (index % FPS === 0) {
          status.textContent = "Encoding " + Math.round((index / FRAME_COUNT) * 100) + "%";
        }
        const targetTime = start + ((index + 1) * 1000 / FPS);
        const wait = targetTime - performance.now();
        if (wait > 0) await sleep(wait);
      }
      recorder.stop();
      await stopped;
      stream.getTracks().forEach((track) => track.stop());
      status.textContent = "Uploading video...";
      const blob = new Blob(chunks, { type: recorder.mimeType || mimeType });
      const response = await fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": blob.type },
        body: blob
      });
      if (!response.ok) throw new Error("Upload failed: " + response.status);
      status.textContent = "Done";
    }

    run().catch(async (error) => {
      status.textContent = error.message;
      await fetch("/failed", {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: error.stack || error.message
      }).catch(() => {});
    });
  </script>
</body>
</html>`;
}

async function main() {
  const frames = (await fsp.readdir(FRAMES_DIR))
    .filter((name) => /^frame_\d{5}\.jpg$/.test(name))
    .sort();
  if (!frames.length) throw new Error(`No rendered frames found in ${FRAMES_DIR}`);
  await fsp.mkdir(path.dirname(OUTPUT), { recursive: true });

  let resolveUpload;
  let rejectUpload;
  const uploadPromise = new Promise((resolve, reject) => {
    resolveUpload = resolve;
    rejectUpload = reject;
  });

  const server = http.createServer((req, res) => {
    const url = new URL(req.url || "/", "http://127.0.0.1");
    if (req.method === "GET" && url.pathname === "/encode.html") {
      const body = html(frames.length);
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Content-Length": Buffer.byteLength(body) });
      res.end(body);
      return;
    }
    if (req.method === "GET" && url.pathname.startsWith("/frames/")) {
      const basename = path.basename(url.pathname);
      if (!frames.includes(basename)) {
        res.writeHead(404);
        res.end("missing frame");
        return;
      }
      res.writeHead(200, { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=3600" });
      fs.createReadStream(path.join(FRAMES_DIR, basename)).pipe(res);
      return;
    }
    if (req.method === "POST" && url.pathname === "/upload") {
      const file = fs.createWriteStream(OUTPUT);
      req.pipe(file);
      req.on("end", () => {
        file.end();
        res.writeHead(200, { "Content-Type": "text/plain" });
        res.end("ok");
        resolveUpload();
      });
      req.on("error", rejectUpload);
      file.on("error", rejectUpload);
      return;
    }
    if (req.method === "POST" && url.pathname === "/failed") {
      let body = "";
      req.setEncoding("utf8");
      req.on("data", (chunk) => { body += chunk; });
      req.on("end", () => {
        res.writeHead(200);
        res.end("noted");
        rejectUpload(new Error(body || "browser encoder failed"));
      });
      return;
    }
    res.writeHead(404);
    res.end("not found");
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const profileDir = path.join("/private/tmp", `v3-webm-encoder-profile-${Date.now()}`);
  const chrome = spawn(CHROME, [
    "--headless=new",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-default-apps",
    "--autoplay-policy=no-user-gesture-required",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${profileDir}`,
    `--window-size=${WIDTH},${HEIGHT}`,
    `http://127.0.0.1:${port}/encode.html`
  ], { stdio: ["ignore", "ignore", "pipe"] });

  let chromeLog = "";
  chrome.stderr.on("data", (chunk) => {
    chromeLog += chunk.toString("utf8");
    if (chromeLog.length > 12000) chromeLog = chromeLog.slice(-12000);
  });

  const timeout = delay(Math.max(180000, (frames.length / FPS + 80) * 1000)).then(() => {
    throw new Error("Timed out waiting for browser WebM encoder");
  });

  try {
    await Promise.race([uploadPromise, timeout]);
    const stat = await fsp.stat(OUTPUT);
    console.log(`encoded ${frames.length} frames to ${OUTPUT}`);
    console.log(`size ${(stat.size / (1024 * 1024)).toFixed(1)} MB`);
  } catch (error) {
    console.error(chromeLog);
    throw error;
  } finally {
    chrome.kill("SIGTERM");
    await delay(1000);
    if (!chrome.killed) chrome.kill("SIGKILL");
    server.closeAllConnections?.();
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
