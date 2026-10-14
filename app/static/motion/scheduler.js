// motion/scheduler.js - Single global requestAnimationFrame loop with frame timing

import { isSlowMotion } from "./config.js";

class MotionScheduler {
  constructor() {
    this.activeItems = new Set();
    this.rafId = null;
    this.lastTime = 0;
    this.isRunning = false;

    // Frame metrics for Part 11
    this.frameHistory = [];
    this.isRecordingMetrics = false;

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
          // If tab hidden: skip all active animations immediately to their target states
          this.fastForwardAll();
        }
      });
    }
  }

  // Register an item with step(dt, now) returning false when settled
  register(item) {
    this.activeItems.add(item);
    if (!this.isRunning) {
      this.start();
    }
  }

  unregister(item) {
    this.activeItems.delete(item);
    if (this.activeItems.size === 0) {
      this.stop();
    }
  }

  start() {
    this.isRunning = true;
    this.lastTime = 0;
    this.rafId = requestAnimationFrame(this.tick.bind(this));
  }

  stop() {
    this.isRunning = false;
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.lastTime = 0;
  }

  tick(now) {
    if (!this.isRunning) return;

    const rawDt = this.lastTime ? (now - this.lastTime) / 1000 : 1 / 60;
    this.lastTime = now;

    const startExecution = performance.now();

    // Handle slow motion scale (0.1x) or clamp
    const speedMultiplier = isSlowMotion() ? 0.1 : 1.0;
    const clampedRawDt = Math.min(rawDt, 1 / 30);
    const dt = clampedRawDt * speedMultiplier;

    // Step each active item
    const items = Array.from(this.activeItems);
    for (const item of items) {
      try {
        const settled = item.step(dt, now);
        if (settled) {
          this.activeItems.delete(item);
          if (item.onSettled && !item._handledSettledInStep) {
            item.onSettled();
          }
        }
      } catch (err) {
        console.error("[Forge Motion] Error in animation step:", err);
        this.activeItems.delete(item);
      }
    }

    const scriptDuration = performance.now() - startExecution;
    const frameDeltaMs = rawDt * 1000;

    // Metrics recording
    if (frameDeltaMs > 16.7 && frameDeltaMs < 200) {
      // Frame drop warning
      console.warn(`[Forge Motion] Long frame: ${frameDeltaMs.toFixed(1)}ms (script: ${scriptDuration.toFixed(1)}ms, active: ${items.length})`);
    }

    if (this.isRecordingMetrics) {
      this.frameHistory.push({ delta: frameDeltaMs, script: scriptDuration, time: now });
    }

    if (this.activeItems.size > 0) {
      this.rafId = requestAnimationFrame(this.tick.bind(this));
    } else {
      this.stop();
    }
  }

  fastForwardAll() {
    const items = Array.from(this.activeItems);
    for (const item of items) {
      if (typeof item.fastForward === "function") {
        item.fastForward();
      }
      this.activeItems.delete(item);
    }
    this.stop();
  }

  startMetricsRecording() {
    this.frameHistory = [];
    this.isRecordingMetrics = true;
  }

  stopMetricsRecording() {
    this.isRecordingMetrics = false;
    const count = this.frameHistory.length;
    if (count === 0) return { p95: 0, max: 0, frames: 0 };

    const deltas = this.frameHistory.map((f) => f.delta).sort((a, b) => a - b);
    const p95 = deltas[Math.min(deltas.length - 1, Math.floor(deltas.length * 0.95))];
    const max = deltas[deltas.length - 1];
    return { p95, max, frames: count, history: this.frameHistory };
  }
}

export const scheduler = new MotionScheduler();
