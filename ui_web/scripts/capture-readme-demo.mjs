#!/usr/bin/env node
/**
 * Records docs/media/dba-assist-demo.gif using the local API + Vite dev server.
 * Requires: ffmpeg on PATH, Playwright browsers (npx playwright install chromium).
 * Frees ports 8000 and 5173 or uses servers that are already up.
 */
import { spawn } from "node:child_process";
import { mkdir, rm } from "node:fs/promises";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const execFileAsync = promisify(execFile);

const __dirname = dirname(fileURLToPath(import.meta.url));
const UI_WEB = join(__dirname, "..");
const ROOT = join(UI_WEB, "..");
const OUT_GIF = join(ROOT, "docs", "media", "dba-assist-demo.gif");
const CACHE_DIR = join(UI_WEB, "node_modules", ".cache");

const API = "http://127.0.0.1:8000/health";
const UI = "http://127.0.0.1:5173/";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function tryFetchOk(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        return true;
      }
    } catch {
      /* retry */
    }
    await sleep(350);
  }
  return false;
}

async function waitForServers() {
  const okApi = await tryFetchOk(API, 90000);
  if (!okApi) {
    throw new Error(`Timed out waiting for API at ${API}`);
  }
  const okUi = await tryFetchOk(UI, 90000);
  if (!okUi) {
    throw new Error(`Timed out waiting for Vite at ${UI}`);
  }
}

function startBackend() {
  const py = process.env.PYTHON || "python3";
  return spawn(py, ["-m", "mariadb_db_agents.ui_api.main"], {
    cwd: ROOT,
    stdio: "ignore",
    detached: true,
    env: { ...process.env },
  });
}

function startVite() {
  return spawn("npx", ["vite", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], {
    cwd: UI_WEB,
    stdio: "ignore",
    detached: true,
    env: { ...process.env },
  });
}

async function main() {
  let backend = null;
  let vite = null;
  let weStarted = false;

  const apiUp = await tryFetchOk(API, 800);
  const uiUp = await tryFetchOk(UI, 800);

  if (!apiUp || !uiUp) {
    if (apiUp !== uiUp) {
      console.error(
        "One of the dev servers is already running but not the other. Stop processes on ports 8000 and 5173, then retry."
      );
      process.exit(1);
    }
    console.error("Starting API (8000) and Vite (5173)...");
    backend = startBackend();
    vite = startVite();
    weStarted = true;
    if (backend.pid) {
      backend.on("error", (err) => console.error("backend:", err));
    }
    if (vite.pid) {
      vite.on("error", (err) => console.error("vite:", err));
    }
  } else {
    console.error("Using existing servers on 8000 and 5173.");
  }

  try {
    await waitForServers();

    await mkdir(CACHE_DIR, { recursive: true });

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      recordVideo: {
        dir: CACHE_DIR,
        size: { width: 1280, height: 720 },
      },
    });

    const page = await context.newPage();
    await page.goto(UI, { waitUntil: "networkidle", timeout: 120000 });
    await page.waitForSelector(".app-root", { timeout: 30000 });

    // Let the UI settle after bootstrap (loading banner may flash).
    await sleep(1400);

    await page.getByRole("button", { name: "config", exact: true }).click();
    await sleep(1000);
    await page.getByRole("button", { name: "profiles", exact: true }).click();
    await sleep(1000);
    await page.getByRole("button", { name: "agents", exact: true }).click();
    await sleep(1000);
    await page.getByRole("button", { name: "chat", exact: true }).click();
    await sleep(1600);

    const video = page.video();
    await context.close();
    await browser.close();

    if (!video) {
      throw new Error("Playwright did not produce a video recording.");
    }
    const webmPath = await video.path();

    console.error(`Encoding GIF → ${OUT_GIF}`);
    await execFileAsync("ffmpeg", [
      "-y",
      "-i",
      webmPath,
      "-vf",
      "fps=8,scale=1200:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
      "-loop",
      "0",
      OUT_GIF,
    ]);

    await rm(webmPath, { force: true }).catch(() => {});
    console.error("Done.");
  } finally {
    if (weStarted && backend?.pid) {
      try {
        process.kill(-backend.pid, "SIGTERM");
      } catch {
        try {
          backend.kill("SIGTERM");
        } catch {
          /* ignore */
        }
      }
    }
    if (weStarted && vite?.pid) {
      try {
        process.kill(-vite.pid, "SIGTERM");
      } catch {
        try {
          vite.kill("SIGTERM");
        } catch {
          /* ignore */
        }
      }
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
