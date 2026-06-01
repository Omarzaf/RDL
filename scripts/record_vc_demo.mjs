import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";

const chromeBin = process.env.CHROME_BIN || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const rootDir = path.resolve(decodeURIComponent(new URL("..", import.meta.url).pathname));
const outDir = path.join(rootDir, "demo_artifacts", "rdl_vc_demo_frames");
const url = process.env.RDL_DEMO_URL || "http://127.0.0.1:8765/V3_Epistemic/output/reliable_influence_map.html";
const width = Number(process.env.RDL_DEMO_WIDTH || 1280);
const height = Number(process.env.RDL_DEMO_HEIGHT || 720);
const port = 9400 + Math.floor(Math.random() * 400);
const profileDir = `/private/tmp/rdl-demo-chrome-${Date.now()}`;

await fs.rm(outDir, { recursive: true, force: true });
await fs.mkdir(outDir, { recursive: true });

const chrome = spawn(chromeBin, [
  "--headless=new",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profileDir}`,
  `--window-size=${width},${height}`,
  "--hide-scrollbars",
  "--disable-background-networking",
  "--disable-sync",
  "--disable-extensions",
  "--enable-webgl",
  "--ignore-gpu-blocklist",
  "--use-gl=angle",
  "--use-angle=metal",
  "about:blank",
], { stdio: ["ignore", "pipe", "pipe"] });

chrome.stderr.on("data", (chunk) => {
  const text = String(chunk);
  if (!text.includes("DevTools listening")) process.stderr.write(text);
});

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJson(endpoint, options) {
  const response = await fetch(endpoint, options);
  if (!response.ok) throw new Error(`${response.status} ${endpoint}`);
  return response.json();
}

async function waitForChrome() {
  for (let i = 0; i < 80; i += 1) {
    try {
      return await fetchJson(`http://127.0.0.1:${port}/json/version`);
    } catch {
      await wait(250);
    }
  }
  throw new Error("Chrome did not expose a debugger endpoint.");
}

class CDP {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.events = new Map();
  }

  async open() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
    this.ws.addEventListener("message", (event) => this.onMessage(event));
  }

  onMessage(event) {
    const message = JSON.parse(event.data);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result || {});
      return;
    }
    const waiters = this.events.get(message.method);
    if (waiters?.length) waiters.splice(0).forEach((resolve) => resolve(message.params || {}));
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  waitEvent(method, timeoutMs = 15000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), timeoutMs);
      if (!this.events.has(method)) this.events.set(method, []);
      this.events.get(method).push((params) => {
        clearTimeout(timer);
        resolve(params);
      });
    });
  }

  close() {
    this.ws.close();
  }
}

async function main() {
  await waitForChrome();
  const target = await fetchJson(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  const cdp = new CDP(target.webSocketDebuggerUrl);
  await cdp.open();
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Input.setIgnoreInputEvents", { ignore: false });
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await cdp.waitEvent("Page.loadEventFired", 20000).catch(() => {});
  await waitForExpression(cdp, "document.querySelector('#loading')?.style.display === 'none'", 45000);

  let frameIndex = 0;
  const captions = [];

  async function evaluate(expression) {
    const result = await cdp.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "Runtime exception");
    return result.result?.value;
  }

  async function click(selector) {
    await evaluate(`document.querySelector(${JSON.stringify(selector)})?.click()`);
    await wait(700);
  }

  async function setSearch(value) {
    await evaluate(`
      (() => {
        const input = document.querySelector('#search');
        input.value = ${JSON.stringify(value)};
        input.dispatchEvent(new Event('input', { bubbles: true }));
      })()
    `);
    await wait(800);
  }

  async function capture(caption, count = 8, delay = 170) {
    for (let i = 0; i < count; i += 1) {
      const shot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        captureBeyondViewport: false,
      });
      const file = path.join(outDir, `frame_${String(frameIndex).padStart(4, "0")}.png`);
      await fs.writeFile(file, Buffer.from(shot.data, "base64"));
      captions.push({ file, caption });
      frameIndex += 1;
      await wait(delay);
    }
  }

  await evaluate("localStorage.setItem('rdl-theme', 'light')");
  await evaluate("document.body.classList.contains('theme-dark') && document.querySelector('#theme-toggle').click()");
  await wait(700);
  await capture("RDL maps the DC lobbying evidence graph: 42,084 searchable entities with a high-signal 2D scene first.", 10);

  await click("#theme-toggle");
  await capture("Dark mode keeps the same evidence contract while making the map presentation-ready for briefing rooms.", 10);

  await click("#ui-analyst");
  await capture("Analyst mode exposes controls for years, entity types, confidence, relationships, gap leads, and provenance.", 10);

  await click("#view-3d");
  await capture("3D mode turns the issue-space map into a time stack, separating year context from the 2D analytical layout.", 10);

  await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 610, y: 420 });
  await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: 610, y: 420, button: "left", clickCount: 1 });
  await cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 780, y: 360, button: "left", buttons: 1 });
  await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: 780, y: 360, button: "left", clickCount: 1 });
  await wait(700);
  await capture("The WebGL scene is interactive: rotate, pan, zoom, and inspect dense relationship structure without leaving the page.", 10);

  await click("[data-year='2025']");
  await capture("Year filtering makes partial 2025 explicit instead of treating it as a complete historical year.", 8);

  await setSearch("CHAMBER OF COMMERCE OF THE U.S.A.");
  await capture("Search jumps to visible entities and opens source-backed metrics: prominence, confidence, gap lead, and revolving score.", 10);

  await setSearch("KANEKA PHARMA AMERICA, LLC");
  await capture("The full search index reaches entities outside the initial rendered subset, preserving performance without hiding coverage.", 10);

  await click("#view-2d");
  await setSearch("");
  await capture("The product stays static-file deployable: split payloads, local vendor assets, and reproducible pipeline manifests.", 10);

  await fs.writeFile(path.join(outDir, "captions.json"), JSON.stringify(captions, null, 2));
  await fs.writeFile(path.join(outDir, "recording_manifest.json"), JSON.stringify({ url, width, height, frames: frameIndex }, null, 2));
  cdp.close();
  chrome.kill();
  await fs.rm(profileDir, { recursive: true, force: true });
  console.log(JSON.stringify({ outDir, frames: frameIndex }, null, 2));
}

async function waitForExpression(cdp, expression, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const result = await cdp.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.result?.value) return;
    await wait(400);
  }
  throw new Error(`Timed out waiting for expression: ${expression}`);
}

main().catch(async (error) => {
  chrome.kill();
  await fs.rm(profileDir, { recursive: true, force: true }).catch(() => {});
  console.error(error);
  process.exit(1);
});
