// motion/index.js - Public entry point for Forge Motion System

import {
  TOKENS,
  SPRING_PRESETS,
  SYSTEM_PRESETS,
  getActiveConfig,
  getActivePresetName,
  setMotionPreset,
  updateKnob,
  resetKnobs,
  toggleSlowMotion,
  isSlowMotion,
  isReducedMotion,
  onConfigChange,
} from "./config.js";

import { Spring, simulateVMax, generateLinearEasing } from "./spring.js";
import { scheduler } from "./scheduler.js";
import {
  roundedRectOutline,
  computeLagWeights,
  computeCentroid,
  getElementGeometry,
} from "./outline.js";

import { MorphPanel, animateFileToTab } from "./morph.js";
import { stack } from "./stack.js";
import { SlidingIndicator } from "./indicator.js";
import { BadgeRoller } from "./badge.js";
import { FlipGroup } from "./flip.js";
import { Presence } from "./presence.js";
import {
  initDebugTools,
  scrub,
  scrubSwitch,
  scrubBadge,
  scrubFolder,
  scrubFileClick,
  scrubTabs,
  scrubJourney,
  report,
  toggleTuningPanel,
  toggleScrubberPanel,
} from "./debug.js";

// Initialize debug tools on load
initDebugTools();

// Global API bindings
if (typeof window !== "undefined") {
  window.Forge = window.Forge || {};
  window.Forge.setMotionPreset = setMotionPreset;
  window.Forge.motion = {
    TOKENS,
    SPRING_PRESETS,
    SYSTEM_PRESETS,
    getActiveConfig,
    getActivePresetName,
    setMotionPreset,
    updateKnob,
    resetKnobs,
    toggleSlowMotion,
    isSlowMotion,
    isReducedMotion,
    onConfigChange,
    Spring,
    simulateVMax,
    generateLinearEasing,
    scheduler,
    roundedRectOutline,
    computeLagWeights,
    computeCentroid,
    getElementGeometry,
    MorphPanel,
    animateFileToTab,
    stack,
    SlidingIndicator,
    BadgeRoller,
    FlipGroup,
    Presence,
    scrub,
    scrubSwitch,
    scrubBadge,
    scrubFolder,
    scrubFileClick,
    scrubTabs,
    scrubJourney,
    report,
    toggleTuningPanel,
    toggleScrubberPanel,
  };

  // Backwards compatibility for ForgeMotion
  window.ForgeMotion = {
    presets: SYSTEM_PRESETS,
    spring: (opts) => new Spring(opts),
    springLinear: (k, c, m, steps) => generateLinearEasing({ stiffness: k, damping: c, mass: m }, steps),
    open: (trigger, surface) => {
      let m = stack.getSurface(surface?.id || "default");
      if (!m && surface) {
        m = MorphPanel.attach({ trigger, panel: surface });
      }
      if (m) m.open();
    },
    close: (trigger, surface) => {
      let m = stack.getSurface(surface?.id || "default");
      if (m) m.close();
      else if (surface) surface.hidden = true;
      return Promise.resolve();
    },
    setPreset: setMotionPreset,
    toggleSlow: toggleSlowMotion,
    get preset() { return getActivePresetName(); },
  };
}

export {
  TOKENS,
  SPRING_PRESETS,
  SYSTEM_PRESETS,
  getActiveConfig,
  getActivePresetName,
  setMotionPreset,
  updateKnob,
  resetKnobs,
  toggleSlowMotion,
  isSlowMotion,
  isReducedMotion,
  onConfigChange,
  Spring,
  simulateVMax,
  generateLinearEasing,
  scheduler,
  roundedRectOutline,
  computeLagWeights,
  computeCentroid,
  getElementGeometry,
  MorphPanel,
  animateFileToTab,
  stack,
  SlidingIndicator,
  BadgeRoller,
  FlipGroup,
  Presence,
  scrub,
  scrubSwitch,
  scrubBadge,
  scrubFolder,
  scrubFileClick,
  scrubTabs,
  scrubJourney,
  report,
  toggleTuningPanel,
  toggleScrubberPanel,
};
