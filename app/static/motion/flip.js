// motion/flip.js - FLIP (First, Last, Invert, Play) animation helper

import { Spring } from "./spring.js";
import { scheduler } from "./scheduler.js";
import { SPRING_PRESETS, isReducedMotion } from "./config.js";

export class FlipGroup {
  constructor(container, { preset = "glide" } = {}) {
    this.container = typeof container === "string" ? document.querySelector(container) : container;
    this.preset = SPRING_PRESETS[preset] || SPRING_PRESETS.glide;
    this.firstPositions = new Map();
    this.activeAnimations = new Map();
  }

  snapshot(selector = "> *") {
    if (!this.container) return;
    this.firstPositions.clear();
    const children = this.container.querySelectorAll(selector);
    for (const child of children) {
      const key = child.dataset.key || child.dataset.tab || child.id || child;
      const rect = child.getBoundingClientRect();
      this.firstPositions.set(key, { left: rect.left, top: rect.top, width: rect.width, height: rect.height });
    }
  }

  play(selector = "> *") {
    if (!this.container || isReducedMotion()) return;
    const children = this.container.querySelectorAll(selector);

    for (const child of children) {
      const key = child.dataset.key || child.dataset.tab || child.id || child;
      const first = this.firstPositions.get(key);
      if (!first) continue;

      const last = child.getBoundingClientRect();
      const dx = first.left - last.left;
      const dy = first.top - last.top;

      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) continue;

      // Invert
      child.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;

      // Play using spring
      const springX = new Spring({ ...this.preset, value: dx, target: 0 });
      const springY = new Spring({ ...this.preset, value: dy, target: 0 });

      const anim = {
        step: (dt) => {
          const settledX = springX.step(dt);
          const settledY = springY.step(dt);
          child.style.transform = `translate3d(${springX.value.toFixed(1)}px, ${springY.value.toFixed(1)}px, 0)`;
          if (settledX && settledY) {
            child.style.transform = "none";
            return true;
          }
          return false;
        },
      };

      scheduler.register(anim);
    }
  }
}
