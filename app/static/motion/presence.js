// motion/presence.js - Enter/exit helper for simple surfaces (tooltips, toasts, menus)

import { Spring } from "./spring.js";
import { scheduler } from "./scheduler.js";
import { SPRING_PRESETS, isReducedMotion } from "./config.js";

export class Presence {
  constructor(element, {
    preset = "settle",
    offsetY = 12,
    initialScale = 0.95,
  } = {}) {
    this.element = typeof element === "string" ? document.querySelector(element) : element;
    this.preset = SPRING_PRESETS[preset] || SPRING_PRESETS.settle;
    this.offsetY = offsetY;
    this.initialScale = initialScale;

    this.spring = new Spring({ ...this.preset, value: 0, target: 0 });
    this.isOpen = false;
  }

  prepareShow() {
    if (!this.element) return;
    this.isOpen = true;
    this.spring.value = 0;
    this.spring.velocity = 0;
    this.spring.retarget(1);

    const scale = this.initialScale;
    const dy = this.offsetY;
    this.element.style.opacity = "0";
    this.element.style.transform = `translate3d(0, ${dy.toFixed(1)}px, 0) scale(${scale.toFixed(3)})`;
  }

  show() {
    if (!this.element) return;
    this.prepareShow();
    this.element.hidden = false;

    if (isReducedMotion()) {
      this.element.style.opacity = "1";
      this.element.style.transform = "none";
      return;
    }

    scheduler.register(this);
  }

  hide() {
    if (!this.element) return;
    this.isOpen = false;

    if (isReducedMotion()) {
      this.element.style.opacity = "0";
      this.element.hidden = true;
      return;
    }

    this.spring.retarget(0);
    scheduler.register(this);
  }

  step(dt) {
    const settled = this.spring.step(dt);
    const p = this.spring.value;

    const opacity = Math.max(0, Math.min(1, p));
    const scale = this.initialScale + (1 - this.initialScale) * p;
    const dy = (1 - p) * this.offsetY;

    this.element.style.opacity = opacity.toFixed(3);
    this.element.style.transform = `translate3d(0, ${dy.toFixed(1)}px, 0) scale(${scale.toFixed(3)})`;

    if (settled) {
      if (!this.isOpen) {
        this.element.hidden = true;
        this.element.style.opacity = "";
        this.element.style.transform = "";
      } else {
        this.element.style.opacity = "";
        this.element.style.transform = "";
      }
      return true;
    }
    return false;
  }
}
