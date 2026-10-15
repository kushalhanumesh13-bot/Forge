// motion/badge.js - Badge pop (settle spring) and vertical digit roller (200ms)

import { Spring } from "./spring.js";
import { scheduler } from "./scheduler.js";
import { SPRING_PRESETS, isReducedMotion } from "./config.js";

export class BadgeRoller {
  constructor(element) {
    this.el = typeof element === "string" ? document.getElementById(element) : element;
    this.currentValue = this.el ? (parseInt(this.el.textContent, 10) || 0) : 0;
    this.spring = new Spring({
      stiffness: SPRING_PRESETS.settle.stiffness,
      damping: SPRING_PRESETS.settle.damping,
      mass: SPRING_PRESETS.settle.mass,
      value: 1,
      target: 1,
      precision: 0.001,
    });
    this.isPopping = false;
    this.rollTimer = null;
  }

  set(newValue) {
    if (!this.el) return;
    const num = typeof newValue === "number" ? newValue : parseInt(newValue, 10) || 0;
    if (num === this.currentValue) return;

    const oldVal = this.currentValue;
    this.currentValue = num;

    if (isReducedMotion()) {
      this.el.textContent = String(num);
      return;
    }

    // Pop on settle spring: start at scale 0.6, retarget to 1.0 (settles with ~3% overshoot)
    this.spring.value = 0.6;
    this.spring.velocity = 0;
    this.spring.retarget(1.0);
    this.isPopping = true;
    scheduler.register(this);

    // Roll digits vertically: old digit up and out, new one rising in (200ms)
    this.rollDigits(oldVal, num);
  }

  rollDigits(oldVal, newVal) {
    if (this.rollTimer) {
      clearTimeout(this.rollTimer);
      this.rollTimer = null;
    }

    const wrapper = document.createElement("span");
    wrapper.className = "digit-roll-wrapper";
    wrapper.style.cssText = "display:inline-block;position:relative;height:14px;overflow:hidden;vertical-align:middle;width:100%;";

    const oldEl = document.createElement("span");
    oldEl.className = "digit-roll-item digit-roll-old";
    oldEl.textContent = String(oldVal);
    oldEl.style.cssText = "display:block;height:14px;line-height:14px;text-align:center;transform:translateY(0);transition:transform 200ms cubic-bezier(0.4, 0, 1, 1), opacity 200ms cubic-bezier(0.4, 0, 1, 1);";

    const newEl = document.createElement("span");
    newEl.className = "digit-roll-item digit-roll-new";
    newEl.textContent = String(newVal);
    newEl.style.cssText = "display:block;position:absolute;top:0;left:0;right:0;height:14px;line-height:14px;text-align:center;transform:translateY(100%);opacity:0;transition:transform 200ms cubic-bezier(0.22, 1, 0.36, 1), opacity 200ms cubic-bezier(0.22, 1, 0.36, 1);";

    wrapper.appendChild(oldEl);
    wrapper.appendChild(newEl);

    this.el.innerHTML = "";
    this.el.appendChild(wrapper);

    // Trigger transition next frame
    requestAnimationFrame(() => {
      oldEl.style.transform = "translateY(-100%)";
      oldEl.style.opacity = "0";
      newEl.style.transform = "translateY(0)";
      newEl.style.opacity = "1";
    });

    this.rollTimer = setTimeout(() => {
      if (this.el && this.currentValue === newVal) {
        this.el.textContent = String(newVal);
      }
      this.rollTimer = null;
    }, 220);
  }

  step(dt) {
    if (!this.isPopping) return true;
    const settled = this.spring.step(dt);
    if (this.el) {
      this.el.style.transform = `scale(${this.spring.value.toFixed(3)})`;
    }
    if (settled) {
      this.isPopping = false;
      if (this.el) this.el.style.transform = "none";
      return true;
    }
    return false;
  }
}
