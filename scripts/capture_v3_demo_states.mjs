#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs/promises";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import { spawn } from "node:child_process";

const REPO_ROOT = process.cwd();
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const MAP_URL = "http://localhost:8765/V3_Epistemic/output/reliable_influence_map.html";
const OUT_DIR = path.join(REPO_ROOT, "demo_artifacts", "v3_product_demo");
const RAW_DIR = path.join(OUT_DIR, "raw_states");
const WIDTH = 1920;
const HEIGHT = 1080;

const STATES = [
  {
    slug: "overview",
    title: "DC Lobbying Evidence Map",
    body: "A validated evidence map with visible counts, quality flags, and full graph search.",
    duration: 4.5,
    focus: [960, 560],
    zoom: [1.0, 1.035],
    spotlight: [650, 24, 1220, 82]
  },
  {
    slug: "briefing_to_analyst",
    title: "Briefing and analyst modes",
    body: "Switch from a briefing-ready view into the control surface without leaving the map.",
    duration: 5.0,
    focus: [540, 540],
    zoom: [1.03, 1.13],
    spotlight: [1288, 56, 1518, 90]
  },
  {
    slug: "issue_profile_embedding",
    title: "2D issue/profile embedding",
    body: "Scan entities, relationship density, and evidence-weighted prominence in one view.",
    duration: 5.0,
    focus: [960, 565],
    zoom: [1.0, 1.06],
    spotlight: [650, 230, 1370, 850]
  },
  {
    slug: "three_d_time",
    title: "3D time slices",
    body: "All-years mode becomes vertical evidence slices with revolving-door flow arcs.",
    duration: 5.0,
    focus: [930, 585],
    zoom: [1.0, 1.08],
    spotlight: [1390, 56, 1518, 90]
  },
  {
    slug: "single_year",
    title: "Single-year filtering",
    body: "Jump from the all-years context to one reporting year while the rail stays visible.",
    duration: 4.5,
    focus: [730, 535],
    zoom: [1.05, 1.12],
    spotlight: [650, 1030, 1270, 1074]
  },
  {
    slug: "prominence_filters",
    title: "Prominence and entity filters",
    body: "Tighten the scene with minimum prominence and entity-type filters.",
    duration: 5.0,
    focus: [420, 530],
    zoom: [1.08, 1.18],
    spotlight: [18, 272, 292, 558]
  },
  {
    slug: "search_insight",
    title: "Search with source-backed insight",
    body: "Find an actor and open metrics, confidence, flags, source files, and interpretation.",
    duration: 5.5,
    focus: [1370, 560],
    zoom: [1.0, 1.11],
    spotlight: [1232, 20, 1770, 54]
  },
  {
    slug: "relationship_detail",
    title: "Relationship inspection",
    body: "Inspect relationship weight, confidence, raw value, duplicate count, and evidence source.",
    duration: 5.0,
    focus: [1390, 570],
    zoom: [1.02, 1.12],
    spotlight: [1468, 100, 1908, 720]
  },
  {
    slug: "color_lenses",
    title: "Analytical color lenses",
    body: "Compare confidence, policy category, and model-derived gap lead score.",
    duration: 5.0,
    focus: [1540, 62],
    zoom: [1.04, 1.14],
    spotlight: [1772, 22, 1900, 54]
  },
  {
    slug: "layers_and_labels",
    title: "Layer controls",
    body: "Reveal the gap plane, top relationships, flow arcs, identifiers, and anchor labels.",
    duration: 5.0,
    focus: [500, 650],
    zoom: [1.04, 1.16],
    spotlight: [18, 534, 292, 782]
  },
  {
    slug: "dark_presentation",
    title: "Dark presentation mode",
    body: "Switch to a high-contrast briefing mode for projection and stakeholder review.",
    duration: 5.0,
    focus: [960, 560],
    zoom: [1.0, 1.055],
    spotlight: [1738, 56, 1814, 90]
  },
  {
    slug: "caveats_and_reset",
    title: "Caveats and reset",
    body: "Data notes stay one click away, and reset returns the map to a clean shareable state.",
    duration: 5.5,
    focus: [1040, 570],
    zoom: [1.04, 1.0],
    spotlight: [1600, 952, 1908, 1010]
  }
];

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requestJson(port, endpoint, method = "GET") {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { hostname: "127.0.0.1", port, path: endpoint, method },
      (res) => {
        let data = "";
        res.setEncoding("utf8");
        res.on("data", (chunk) => { data += chunk; });
        res.on("end", () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(`HTTP ${res.statusCode} for ${endpoint}: ${data.slice(0, 200)}`));
            return;
          }
          try {
            resolve(JSON.parse(data));
          } catch (error) {
            reject(error);
          }
        });
      }
    );
    req.on("error", reject);
    req.end();
  });
}

async function waitForCdp(port, timeoutMs = 25000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await requestJson(port, "/json/version");
      return;
    } catch {
      await delay(250);
    }
  }
  throw new Error(`Chrome DevTools did not open on port ${port}`);
}

class WebSocketConnection {
  constructor(wsUrl) {
    const parsed = new URL(wsUrl);
    this.host = parsed.hostname;
    this.port = Number(parsed.port);
    this.path = parsed.pathname + parsed.search;
    this.socket = null;
    this.buffer = Buffer.alloc(0);
    this.pending = new Map();
    this.eventListeners = new Map();
    this.nextId = 1;
  }

  async connect() {
    this.socket = net.createConnection({ host: this.host, port: this.port });
    await new Promise((resolve, reject) => {
      this.socket.once("connect", resolve);
      this.socket.once("error", reject);
    });

    const key = crypto.randomBytes(16).toString("base64");
    const headers = [
      `GET ${this.path} HTTP/1.1`,
      `Host: ${this.host}:${this.port}`,
      "Upgrade: websocket",
      "Connection: Upgrade",
      `Sec-WebSocket-Key: ${key}`,
      "Sec-WebSocket-Version: 13",
      "\r\n"
    ].join("\r\n");
    this.socket.write(headers);

    let handshake = Buffer.alloc(0);
    await new Promise((resolve, reject) => {
      const onData = (chunk) => {
        handshake = Buffer.concat([handshake, chunk]);
        const end = handshake.indexOf("\r\n\r\n");
        if (end === -1) return;
        this.socket.off("data", onData);
        const head = handshake.slice(0, end).toString("utf8");
        if (!head.includes(" 101 ")) {
          reject(new Error(`WebSocket upgrade failed: ${head}`));
          return;
        }
        this.buffer = handshake.slice(end + 4);
        resolve();
      };
      this.socket.on("data", onData);
      this.socket.once("error", reject);
    });

    this.socket.on("data", (chunk) => {
      this.buffer = Buffer.concat([this.buffer, chunk]);
      this.readFrames();
    });
    this.socket.on("close", () => {
      for (const { reject } of this.pending.values()) reject(new Error("CDP socket closed"));
      this.pending.clear();
    });
    this.readFrames();
  }

  sendFrame(payload, opcode = 1) {
    const data = Buffer.isBuffer(payload) ? payload : Buffer.from(String(payload));
    const mask = crypto.randomBytes(4);
    let header;
    if (data.length < 126) {
      header = Buffer.alloc(2);
      header[1] = 0x80 | data.length;
    } else if (data.length < 65536) {
      header = Buffer.alloc(4);
      header[1] = 0x80 | 126;
      header.writeUInt16BE(data.length, 2);
    } else {
      header = Buffer.alloc(10);
      header[1] = 0x80 | 127;
      header.writeBigUInt64BE(BigInt(data.length), 2);
    }
    header[0] = 0x80 | opcode;
    const masked = Buffer.alloc(data.length);
    for (let i = 0; i < data.length; i += 1) masked[i] = data[i] ^ mask[i % 4];
    this.socket.write(Buffer.concat([header, mask, masked]));
  }

  readFrames() {
    while (this.buffer.length >= 2) {
      const b0 = this.buffer[0];
      const b1 = this.buffer[1];
      const opcode = b0 & 0x0f;
      const masked = Boolean(b1 & 0x80);
      let length = b1 & 0x7f;
      let offset = 2;
      if (length === 126) {
        if (this.buffer.length < offset + 2) return;
        length = this.buffer.readUInt16BE(offset);
        offset += 2;
      } else if (length === 127) {
        if (this.buffer.length < offset + 8) return;
        length = Number(this.buffer.readBigUInt64BE(offset));
        offset += 8;
      }
      const maskOffset = offset;
      if (masked) offset += 4;
      if (this.buffer.length < offset + length) return;
      let payload = this.buffer.slice(offset, offset + length);
      if (masked) {
        const mask = this.buffer.slice(maskOffset, maskOffset + 4);
        payload = Buffer.from(payload.map((byte, index) => byte ^ mask[index % 4]));
      }
      this.buffer = this.buffer.slice(offset + length);

      if (opcode === 1) this.handleText(payload.toString("utf8"));
      if (opcode === 8) this.socket.end();
      if (opcode === 9) this.sendFrame(payload, 10);
    }
  }

  handleText(text) {
    const message = JSON.parse(text);
    if (message.id && this.pending.has(message.id)) {
      const pending = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(message.error.message || JSON.stringify(message.error)));
      else pending.resolve(message.result);
      return;
    }
    if (message.method && this.eventListeners.has(message.method)) {
      for (const listener of this.eventListeners.get(message.method)) listener(message.params || {});
    }
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    this.sendFrame(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    try {
      this.sendFrame(Buffer.alloc(0), 8);
      this.socket.end();
    } catch {}
  }
}

async function evaluate(cdp, expression, awaitPromise = true) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise,
    returnByValue: true,
    userGesture: true,
    timeout: 30000
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || "Runtime.evaluate failed");
  }
  return result.result?.value;
}

const demoHelperExpression = String.raw`
(async () => {
  const waitFrames = (count = 4) => new Promise((resolve) => {
    let remaining = count;
    function step() {
      remaining -= 1;
      if (remaining <= 0) window.setTimeout(resolve, 180);
      else window.requestAnimationFrame(step);
    }
    window.requestAnimationFrame(step);
  });

  const setCheckbox = (id, checked) => {
    const el = document.getElementById(id);
    if (el) el.checked = checked;
  };

  const refreshTypes = () => {
    enabledTypes = new Set(Array.from(document.querySelectorAll("[data-type]:checked")).map((el) => el.dataset.type));
  };

  const setLens = (lens) => {
    colorMode = lens;
    uiState.activeLens = lens;
    const select = document.getElementById("color-mode");
    if (select) select.value = lens;
    syncUI();
    rebuildNodes();
  };

  const setMinProminence = (value) => {
    minInfluence = value;
    const input = document.getElementById("influence");
    const label = document.getElementById("influence-label");
    if (input) input.value = String(value);
    if (label) label.textContent = value.toFixed(2);
    rebuildNodes();
  };

  const showLabels = (enabled) => {
    setCheckbox("show-identifiers", enabled);
    setCheckbox("show-labels", enabled);
    rebuildNodes();
  };

  const setCamera = (radius, theta, phi, target = [0, 0, 0]) => {
    cameraControl.radius = radius;
    cameraControl.theta = theta;
    cameraControl.phi = phi;
    cameraControl.target.set(target[0], target[1], target[2]);
    updateCameraFromControl();
  };

  const base = async () => {
    setThemeMode("light");
    uiState.uiMode = "briefing";
    uiState.panelState.controlsOpen = false;
    uiState.panelState.detailsOpen = false;
    uiState.panelState.legendOpen = false;
    selectedEntityId = null;
    selectedRelationshipKey = null;
    hoveredRelationshipKey = null;
    const search = document.getElementById("search");
    if (search) search.value = "";
    document.getElementById("tooltip").style.display = "none";
    projectionMode = "2d";
    viewMode = "all";
    selectedYear = YEARS.includes(2024) ? 2024 : YEARS[YEARS.length - 1];
    setCheckbox("show-gaps", true);
    setCheckbox("show-edges", true);
    setCheckbox("show-arcs", true);
    setCheckbox("show-identifiers", false);
    setCheckbox("show-labels", false);
    document.querySelectorAll("[data-type]").forEach((input) => {
      input.checked = input.dataset.type !== "reference_node";
    });
    refreshTypes();
    minInfluence = 0;
    const influence = document.getElementById("influence");
    const influenceLabel = document.getElementById("influence-label");
    if (influence) influence.value = "0";
    if (influenceLabel) influenceLabel.textContent = "0.00";
    colorMode = "type";
    uiState.activeLens = "type";
    buildAxes();
    syncUI();
    rebuildNodes();
    resetCameraView();
    updateStats();
    await waitFrames();
  };

  window.__v3DemoState = async (slug) => {
    await base();
    if (slug === "overview") {
      setPanelState("legendOpen", false);
    }

    if (slug === "briefing_to_analyst") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
    }

    if (slug === "issue_profile_embedding") {
      setPanelState("legendOpen", true);
      setLens("type");
      setCamera(730, 0, 0.08, [0, 0, 0]);
    }

    if (slug === "three_d_time") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
      setProjectionMode("3d");
      showLabels(true);
      setCamera(1030, 0.72, 1.14, [0, -10, 0]);
    }

    if (slug === "single_year") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
      setProjectionMode("3d");
      setSelectedYear(YEARS.includes(2024) ? 2024 : YEARS[YEARS.length - 1], true);
      setCamera(950, 0.52, 1.06, [0, -18, 0]);
    }

    if (slug === "prominence_filters") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
      setProjectionMode("3d");
      setSelectedYear(YEARS.includes(2024) ? 2024 : YEARS[YEARS.length - 1], true);
      setMinProminence(0.46);
      setCamera(900, 0.48, 1.03, [0, -18, 0]);
    }

    if (slug === "search_insight") {
      const entity = payload.entities
        .filter((candidate) => candidate.entity_type !== "reference_node")
        .sort((a, b) => Number(b.metrics?.influence_score || 0) - Number(a.metrics?.influence_score || 0))[0];
      if (entity) {
        document.getElementById("search").value = entity.name;
        handleSearchInput();
        setDetails(entity);
      }
      setPanelState("detailsOpen", true);
      setCamera(690, 0, 0.08, [0, 0, 0]);
    }

    if (slug === "relationship_detail") {
      const edge = payload.edges.find((candidate) => candidate.source_name && candidate.target_name) || payload.edges[0];
      if (edge) setRelationshipDetails(edge);
      setPanelState("detailsOpen", true);
      setCamera(690, 0, 0.08, [0, 0, 0]);
    }

    if (slug === "color_lenses") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
      setPanelState("legendOpen", true);
      setLens("confidence");
    }

    if (slug === "layers_and_labels") {
      setUiMode("analyst");
      setPanelState("controlsOpen", true);
      setProjectionMode("3d");
      showLabels(true);
      setCheckbox("show-gaps", true);
      setCheckbox("show-edges", true);
      setCheckbox("show-arcs", true);
      rebuildNodes();
      setCamera(980, 0.76, 1.13, [0, -8, 0]);
    }

    if (slug === "dark_presentation") {
      setThemeMode("dark");
      setProjectionMode("3d");
      setPanelState("legendOpen", true);
      setLens("category");
      setCamera(1000, 0.74, 1.12, [0, -10, 0]);
    }

    if (slug === "caveats_and_reset") {
      setThemeMode("dark");
      setPanelState("legendOpen", false);
      const notes = document.getElementById("data-notes");
      if (notes?.classList.contains("collapsed")) document.getElementById("toggle-notes").click();
      resetCameraView();
    }

    syncUI();
    updateStats();
    await waitFrames(7);
    return {
      slug,
      title: document.title,
      text: document.body.innerText.replace(/\s+/g, " ").slice(0, 200)
    };
  };
  return true;
})()
`;

async function main() {
  await fs.mkdir(RAW_DIR, { recursive: true });

  const port = 9300 + Math.floor(Math.random() * 700);
  const profileDir = path.join("/private/tmp", `v3-demo-chrome-profile-${Date.now()}`);
  const chromeArgs = [
    "--headless=new",
    "--remote-debugging-address=127.0.0.1",
    `--remote-debugging-port=${port}`,
    "--enable-webgl",
    "--ignore-gpu-blocklist",
    "--enable-unsafe-swiftshader",
    "--use-gl=angle",
    "--use-angle=metal",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-default-apps",
    "--metrics-recording-only",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${profileDir}`,
    `--window-size=${WIDTH},${HEIGHT}`,
    "about:blank"
  ];

  const chrome = spawn(CHROME, chromeArgs, { stdio: ["ignore", "ignore", "pipe"] });
  let chromeLog = "";
  chrome.stderr.on("data", (chunk) => {
    chromeLog += chunk.toString("utf8");
    if (chromeLog.length > 12000) chromeLog = chromeLog.slice(-12000);
  });

  let cdp;
  try {
    await waitForCdp(port);
    const targets = await requestJson(port, "/json/list");
    const pageTarget = targets.find((target) => target.type === "page");
    if (!pageTarget?.webSocketDebuggerUrl) throw new Error("No page target from Chrome DevTools");

    cdp = new WebSocketConnection(pageTarget.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: WIDTH,
      height: HEIGHT,
      deviceScaleFactor: 1,
      mobile: false
    });
    await cdp.send("Page.navigate", { url: MAP_URL });
    await evaluate(cdp, `
      new Promise((resolve, reject) => {
        const started = Date.now();
        function check() {
          try {
            const loading = document.getElementById("loading");
            const ready = typeof renderer !== "undefined" && renderer && typeof payload !== "undefined" && payload && loading && loading.style.display === "none";
            if (ready) {
              resolve({ entities: payload.entities.length, edges: payload.edges.length });
              return;
            }
            if (Date.now() - started > 40000) {
              reject(new Error("Map did not finish loading"));
              return;
            }
          } catch {}
          setTimeout(check, 250);
        }
        check();
      })
    `);
    await evaluate(cdp, demoHelperExpression);

    for (let index = 0; index < STATES.length; index += 1) {
      const state = STATES[index];
      await evaluate(cdp, `window.__v3DemoState(${JSON.stringify(state.slug)})`);
      const screenshot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        fromSurface: true,
        optimizeForSpeed: false
      });
      const filename = `${String(index + 1).padStart(2, "0")}_${state.slug}.png`;
      await fs.writeFile(path.join(RAW_DIR, filename), Buffer.from(screenshot.data, "base64"));
      state.image = `raw_states/${filename}`;
      console.log(`captured ${filename}`);
    }

    await fs.writeFile(path.join(OUT_DIR, "states.json"), JSON.stringify({
      width: WIDTH,
      height: HEIGHT,
      fps: 24,
      duration_seconds: STATES.reduce((sum, state) => sum + state.duration, 0),
      states: STATES
    }, null, 2));
    console.log(`wrote ${path.join(OUT_DIR, "states.json")}`);
  } catch (error) {
    console.error(chromeLog);
    throw error;
  } finally {
    cdp?.close();
    chrome.kill("SIGTERM");
    await delay(700);
    if (!chrome.killed) chrome.kill("SIGKILL");
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
