// motion/indicator.js - Shared sliding indicator with stretch and glide spring

import { Spring } from "./spring.js";
import { scheduler } from "./scheduler.js";
import { SPRING_PRESETS, isReducedMotion } from "./config.js";

export class SlidingIndicator {
  constructor({
    container,
    selector = ".is-active",
    className = "motion-indicator",
    axis = "y", // "x" or "y"
    stretch = true,
  } = {}) {
    this.container = typeof container === "string" ? document.querySelector(container) : container;
    this.selector = selector;
    this.className = className;
    this.axis = axis;
    this.stretch = stretch;

    this.posSpring = new Spring({
      stiffness: SPRING_PRESETS.glide.stiffness,
      damping: SPRING_PRESETS.glide.damping,
      mass: SPRING_PRESETS.glide.mass,
      value: 0,
      target: 0,
    });
    this.sizeSpring = new Spring({
      stiffness: SPRING_PRESETS.glide.stiffness,
      damping: SPRING_PRESETS.glide.damping,
      mass: SPRING_PRESETS.glide.mass,
      value: 0,
      target: 0,
    });

    this.indicatorEl = null;
    this.currentElement = null;
    this.initDOM();
  }

  initDOM() {
    if (!this.container) return;
    this.indicatorEl = this.container.querySelector(`.${this.className}`);
    if (!this.indicatorEl) {
      this.indicatorEl = document.createElement("div");
      this.indicatorEl.className = this.className;
      this.indicatorEl.style.cssText = `
        position: absolute;
        ${this.axis === "y" ? "top: 0;" : ""}
        left: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0;
        transition: opacity 120ms ease;
      `;
      this.container.style.position = "relative";
      this.container.prepend(this.indicatorEl);
    }
    this.container.classList.add("has-sliding-indicator");
  }

  moveTo(element, immediate = false) {
    if (!element || !this.container) return;
    if (this.currentElement === element && this.indicatorEl && this.indicatorEl.style.opacity === "1" && !immediate) return;
    if (!this.indicatorEl || !this.indicatorEl.isConnected) {
      this.initDOM();
    }
    this.currentElement = element;

    const cRect = this.container.getBoundingClientRect();
    const eRect = element.getBoundingClientRect();

    const scrollOffset = this.axis === "y" ? (this.container.scrollTop || 0) : (this.container.scrollLeft || 0);
    const targetPos = (this.axis === "y" ? (eRect.top - cRect.top) : (eRect.left - cRect.left)) + scrollOffset;
    const targetSize = this.axis === "y" ? eRect.height : eRect.width;

    if (this.axis === "y") {
      const left = Math.round(eRect.left - cRect.left);
      this.indicatorEl.style.top = "0px";
      this.indicatorEl.style.left = `${left}px`;
      this.indicatorEl.style.width = `${Math.round(eRect.width)}px`;
    } else {
      this.indicatorEl.style.left = "0px";
    }

    if (immediate || isReducedMotion() || this.indicatorEl.style.opacity === "0") {
      this.posSpring.value = targetPos;
      this.posSpring.target = targetPos;
      this.posSpring.velocity = 0;

      this.sizeSpring.value = targetSize;
      this.sizeSpring.target = targetSize;
      this.sizeSpring.velocity = 0;

      this.render();
      this.indicatorEl.style.opacity = "1";
      return;
    }

    this.posSpring.retarget(targetPos);
    this.sizeSpring.retarget(targetSize);
    this.indicatorEl.style.opacity = "1";

    scheduler.register(this);
  }

  step(dt) {
    const posSettled = this.posSpring.step(dt);
    const sizeSettled = this.sizeSpring.step(dt);

    this.render();

    if (posSettled && sizeSettled) {
      return true;
    }
    return false;
  }

  render() {
    if (!this.indicatorEl) return;
    const pos = this.posSpring.value;
    let size = this.sizeSpring.value;

    // Subtle stretch while traveling: up to 15% mid-travel
    if (this.stretch) {
      const v = Math.abs(this.posSpring.velocity);
      const stretchAmount = Math.min(size * 0.15, v * 0.04);
      size += stretchAmount;
    }

    if (this.axis === "y") {
      this.indicatorEl.style.transform = `translate3d(0, ${pos.toFixed(1)}px, 0)`;
      this.indicatorEl.style.height = `${size.toFixed(1)}px`;
    } else {
      this.indicatorEl.style.transform = `translate3d(${pos.toFixed(1)}px, 0, 0)`;
      this.indicatorEl.style.width = `${size.toFixed(1)}px`;
    }
  }

  hide() {
    if (this.indicatorEl) {
      this.indicatorEl.style.opacity = "0";
    }
  }
}
