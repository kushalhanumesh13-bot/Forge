// motion/morph.js - Direct, lightweight MorphPanel engine (origin-anchored spring morph)

import { Spring } from "./spring.js";
import { scheduler } from "./scheduler.js";
import { getElementGeometry, clamp } from "./outline.js";
import { getActiveConfig, isReducedMotion } from "./config.js";
import { stack } from "./stack.js";

export class MorphPanel {
  static attach(options) {
    const instance = new MorphPanel(options);
    stack.register(instance);
    return instance;
  }

  constructor({
    id,
    trigger,
    panel,
    group = "default",
    anchor = "left",
    direction = "right",
    isModal = false,
    closeOnEsc = true,
    closeOnOutsideClick = true,
  }) {
    this.id = id || (typeof panel === "function" ? panel()?.id : panel?.id) || `surface-${Math.random().toString(36).substr(2, 6)}`;
    this._trigger = trigger;
    this._panel = panel;
    this.group = group;
    this.anchor = anchor;
    this.direction = direction;
    this.isModal = isModal;
    this.closeOnEsc = closeOnEsc;
    this.closeOnOutsideClick = closeOnOutsideClick;

    this.state = "closed"; // "closed" | "opening" | "open" | "closing"
    this.progress = 0;
    this.velocity = 0;

    this.listeners = new Map();
    this.hasTriggeredBounce = false;

    const initialConfig = getActiveConfig();

    this.spring = new Spring({
      stiffness: initialConfig.openSpring.stiffness,
      damping: initialConfig.openSpring.damping,
      mass: initialConfig.openSpring.mass,
      value: 0,
      target: 0,
      precision: 0.001,
    });

    this.cachedTGeom = null;
    this.cachedPGeom = null;
    this._handledSettledInStep = false;

    this.initDOM();
  }

  get trigger() {
    return typeof this._trigger === "function" ? this._trigger() : this._trigger;
  }

  get panel() {
    return typeof this._panel === "function" ? this._panel() : this._panel;
  }

  initDOM() {
    const p = this.panel;
    if (!p) return;
    const t = this.trigger;
    if (t) {
      t.setAttribute("aria-expanded", "false");
      if (p.id) t.setAttribute("aria-controls", p.id);
    }
  }

  on(event, fn) {
    if (!this.listeners.has(event)) this.listeners.set(event, new Set());
    this.listeners.get(event).add(fn);
    return () => this.listeners.get(event).delete(fn);
  }

  emit(event, ...args) {
    const set = this.listeners.get(event);
    if (set) {
      for (const fn of set) {
        try { fn(...args); } catch (e) { console.error(e); }
      }
    }
  }

  triggerLandingBounce() {
    const t = this.trigger;
    if (!t) return;
    t.classList.remove("motion-landing");
    void t.offsetWidth; // Reflow
    t.classList.add("motion-landing");
    window.setTimeout(() => t.classList.remove("motion-landing"), 380);
  }

  open() {
    if (this.state === "open" || (this.state === "opening" && this.spring.target === 1)) {
      return;
    }

    stack.onSurfaceOpening(this);

    const config = getActiveConfig();
    this.spring.configure({
      stiffness: config.openSpring.stiffness * (config.speed || 1.0),
      damping: config.openSpring.damping,
      mass: config.openSpring.mass,
    });
    this.spring.retarget(1);

    if (this.state === "closed") {
      this.spring.value = 0;
      this.spring.velocity = 0;
      this.progress = 0;
    }

    this.state = "opening";
    this.hasTriggeredBounce = false;
    this._handledSettledInStep = false;

    const t = this.trigger;
    const p = this.panel;
    const isSidebar = p?.id === "sidebar";
    const workbench = document.getElementById("workbench");

    if (t) t.setAttribute("aria-expanded", "true");

    if (p) {
      if (isSidebar) {
        p.style.opacity = "0";
        p.hidden = false;
        p.setAttribute("aria-hidden", "false");
        p.classList.remove("is-collapsed", "is-minimized");
        p.classList.add("is-open");
        if (workbench) {
          workbench.classList.remove("explorer-is-collapsed");
          workbench.style.setProperty("--explorer-width", "0px");
        }
        this.renderProgress(0);
      } else {
        // Floating panel (Settings, Keys)
        // Measure true untransformed dimensions BEFORE paint
        p.style.opacity = "0";
        p.style.transform = "none";
        p.hidden = false;
        p.setAttribute("aria-hidden", "false");
        p.classList.remove("is-collapsed", "is-minimized");
        p.classList.add("is-open");

        this.cachedTGeom = t ? getElementGeometry(t) : null;
        this.cachedPGeom = getElementGeometry(p);

        // Pre-apply initial spring state (progress = 0) immediately before paint!
        this.renderProgress(0);
      }
    }

    this.emit("opening");

    if (isReducedMotion()) {
      this.fastForward();
      return;
    }

    scheduler.register(this);
  }

  close() {
    if (this.state === "closed" || (this.state === "closing" && this.spring.target === 0)) {
      return;
    }

    const config = getActiveConfig();
    this.spring.configure({
      stiffness: config.closeSpring.stiffness * (config.speed || 1.0),
      damping: config.closeSpring.damping,
      mass: config.closeSpring.mass,
    });
    this.spring.retarget(0);

    if (this.state === "open") {
      this.spring.value = 1;
      this.spring.velocity = 0;
      this.progress = 1;
    }

    this.state = "closing";
    this.hasTriggeredBounce = false;
    this._handledSettledInStep = false;

    const t = this.trigger;
    const p = this.panel;
    const isSidebar = p?.id === "sidebar";

    if (t) t.setAttribute("aria-expanded", "false");

    if (p && !isSidebar && (!this.cachedPGeom || !this.cachedTGeom)) {
      this.cachedTGeom = t ? getElementGeometry(t) : null;
      const prevTransform = p.style.transform;
      p.style.transform = "none";
      this.cachedPGeom = getElementGeometry(p);
      p.style.transform = prevTransform;
    }

    this.emit("closing");

    if (isReducedMotion()) {
      this.fastForward();
      return;
    }

    scheduler.register(this);
  }

  toggle() {
    if (this.state === "open" || this.state === "opening") {
      this.close();
    } else {
      this.open();
    }
  }

  step(dt) {
    const settled = this.spring.step(dt);
    this.progress = this.spring.value;
    this.velocity = this.spring.velocity;

    if (this.state === "closing" && this.progress < 0.08 && !this.hasTriggeredBounce) {
      this.hasTriggeredBounce = true;
      this.triggerLandingBounce();
    }

    this.renderProgress(this.progress);

    if (settled) {
      this._handledSettledInStep = true;
      this.onSettled();
      return true;
    }
    return false;
  }

  renderProgress(p) {
    const panel = this.panel;
    const trigger = this.trigger;
    if (!panel) return;

    const isSidebar = panel.id === "sidebar";

    // old animation, disconnected by motion upgrade:
    /*
    if (isSidebar) {
      const workbench = document.getElementById("workbench");
      const clampedP = clamp(p, 0, 1);
      const targetWidth = 274;
      const currentWidth = (targetWidth * clampedP).toFixed(1);
      if (workbench) {
        workbench.style.setProperty("--explorer-width", `${currentWidth}px`);
      }
      panel.style.opacity = clamp(p * 1.5, 0, 1).toFixed(3);
      return;
    }
    */

    // Floating panels (Settings, Keys) - use cached resting geometry to prevent transform feedback loops
    const tGeom = this.cachedTGeom || (trigger ? getElementGeometry(trigger) : null);
    const pGeom = this.cachedPGeom || getElementGeometry(panel);

    if (!tGeom || !pGeom || pGeom.w === 0 || pGeom.h === 0) {
      panel.style.opacity = clamp(p, 0, 1).toFixed(3);
      return;
    }

    const scaleX = tGeom.w / pGeom.w;
    const scaleY = tGeom.h / pGeom.h;
    const currentScaleX = (scaleX + (1 - scaleX) * p).toFixed(3);
    const currentScaleY = (scaleY + (1 - scaleY) * p).toFixed(3);

    const dx = tGeom.x - pGeom.x;
    const dy = (tGeom.y + tGeom.h) - (pGeom.y + pGeom.h);
    const currentDx = (dx * (1 - p)).toFixed(1);
    const currentDy = (dy * (1 - p)).toFixed(1);

    panel.style.transformOrigin = "bottom left";
    panel.style.transform = `translate3d(${currentDx}px, ${currentDy}px, 0) scale(${currentScaleX}, ${currentScaleY})`;
    panel.style.opacity = clamp(p * 1.6, 0, 1).toFixed(3);
  }

  onSettled() {
    const panel = this.panel;
    const target = this.spring.target;
    const isSidebar = panel?.id === "sidebar";
    const workbench = document.getElementById("workbench");

    this.cachedTGeom = null;
    this.cachedPGeom = null;

    if (target === 1) {
      // Settled OPEN
      this.state = "open";
      this.progress = 1;
      this.velocity = 0;

      if (panel) {
        panel.style.transform = "";
        panel.style.opacity = "";
        panel.hidden = false;
        panel.setAttribute("aria-hidden", "false");
        panel.classList.remove("is-collapsed");
        panel.classList.add("is-open");
      }
      if (isSidebar && workbench) {
        workbench.style.removeProperty("--explorer-width");
        workbench.classList.remove("explorer-is-collapsed");
      }
      this.emit("opened");
    } else {
      // Settled CLOSED
      this.state = "closed";
      this.progress = 0;
      this.velocity = 0;

      if (panel) {
        panel.style.transform = "";
        panel.style.opacity = "";
        panel.hidden = true;
        panel.setAttribute("aria-hidden", "true");
        panel.classList.add("is-collapsed");
        panel.classList.remove("is-open");
      }
      if (isSidebar && workbench) {
        workbench.style.removeProperty("--explorer-width");
        workbench.classList.add("explorer-is-collapsed");
      }
      stack.onSurfaceClosed(this);
      this.emit("closed");
    }
  }

  fastForward() {
    const target = this.spring.target;
    this.spring.value = target;
    this.spring.velocity = 0;
    this.onSettled();
  }
}

export function animateFileToTab(fileRow, targetTab) {
  if (!fileRow || !targetTab || isReducedMotion()) return;
  const fGeom = getElementGeometry(fileRow);
  const tGeom = getElementGeometry(targetTab);
  if (!fGeom || !tGeom) return;

  const clone = document.createElement("div");
  clone.className = "file-fly-ghost";
  clone.textContent = fileRow.querySelector(".tree-label")?.textContent || "file";
  clone.style.cssText = `
    position: fixed;
    left: ${fGeom.x}px;
    top: ${fGeom.y}px;
    width: ${fGeom.w}px;
    height: ${fGeom.h}px;
    pointer-events: none;
    z-index: 999;
    background: var(--accent-subtle);
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: var(--text-on-rail);
    font: 11px var(--mono, monospace);
    display: flex;
    align-items: center;
    padding: 0 8px;
    box-shadow: var(--shadow-md);
    transition: transform 320ms cubic-bezier(.22, 1, .36, 1), opacity 320ms ease;
  `;
  document.body.appendChild(clone);

  requestAnimationFrame(() => {
    const dx = tGeom.x - fGeom.x;
    const dy = tGeom.y - fGeom.y;
    const sx = tGeom.w / fGeom.w;
    const sy = tGeom.h / fGeom.h;
    clone.style.transform = `translate3d(${dx}px, ${dy}px, 0) scale(${sx.toFixed(3)}, ${sy.toFixed(3)})`;
    clone.style.opacity = "0.7";
  });

  setTimeout(() => clone.remove(), 340);
}
