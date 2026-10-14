// motion/config.js - Tokens, spring presets, knobs, and persistence

export const TOKENS = {
  durations: {
    instant: 90,
    fast: 160,
    base: 260,
    slow: 380,
    morph: 520,
  },
  easings: {
    out: "cubic-bezier(0.22, 1, 0.36, 1)",
    in: "cubic-bezier(0.4, 0, 1, 1)",
    inout: "cubic-bezier(0.65, 0, 0.35, 1)",
  },
  distances: {
    xs: 4,
    sm: 8,
    md: 16,
  },
  depth: {
    recedeScale: 0.985,
    recedeDim: 0.92,
  },
};

export const SPRING_PRESETS = {
  glide: { stiffness: 170, damping: 26, mass: 1 },       // zeta ~1.00
  settle: { stiffness: 200, damping: 22, mass: 1 },      // zeta ~0.78
  snap: { stiffness: 420, damping: 34, mass: 1 },        // zeta ~0.83
  morphOpen: { stiffness: 170, damping: 22, mass: 1 },   // zeta ~0.84
  morphClose: { stiffness: 230, damping: 27, mass: 1 },  // zeta ~0.89
  iconBounce: { stiffness: 320, damping: 15, mass: 1 },  // zeta ~0.42
};

export function computeZeta(stiffness, damping, mass = 1) {
  return damping / (2 * Math.sqrt(stiffness * mass));
}

// Log zeta of every preset on module load
console.groupCollapsed("[Forge Motion] Spring Preset Zetas");
for (const [name, p] of Object.entries(SPRING_PRESETS)) {
  const z = computeZeta(p.stiffness, p.damping, p.mass);
  console.log(`Preset: %c${name}%c | k=${p.stiffness}, c=${p.damping}, m=${p.mass} -> zeta=${z.toFixed(4)}`, "font-weight:bold", "");
}
console.groupEnd();

export const SYSTEM_PRESETS = {
  elegant: {
    name: "elegant",
    label: "Elegant (Default)",
    stretch: 0.12,
    lag: 0.35,
    curvature: 0.12,
    neckStrength: 0.55,
    bounce: true,
    speed: 1.0,
    overshoot: 1.0,
    pointCount: 80,
    openSpring: { ...SPRING_PRESETS.morphOpen },
    closeSpring: { ...SPRING_PRESETS.morphClose },
  },
  classic: {
    name: "classic",
    label: "Classic",
    stretch: 0.06,
    lag: 0.20,
    curvature: 0.08,
    neckStrength: 0.25,
    bounce: false,
    speed: 1.0,
    overshoot: 0.4,
    pointCount: 80,
    openSpring: { stiffness: 190, damping: 27, mass: 1 },
    closeSpring: { stiffness: 250, damping: 32, mass: 1 },
  },
  dynamic: {
    name: "dynamic",
    label: "Dynamic",
    stretch: 0.08,
    lag: 0.25,
    curvature: 0.10,
    neckStrength: 0.35,
    bounce: false,
    speed: 1.4,
    overshoot: 0.2,
    pointCount: 80,
    openSpring: { stiffness: 272, damping: 33, mass: 1 },
    closeSpring: { stiffness: 368, damping: 40, mass: 1 },
  },
  sweet: {
    name: "sweet",
    label: "Sweet",
    stretch: 0.14,
    lag: 0.40,
    curvature: 0.15,
    neckStrength: 0.65,
    bounce: true,
    speed: 0.75,
    overshoot: 1.25,
    pointCount: 80,
    openSpring: { stiffness: 140, damping: 20, mass: 1 },
    closeSpring: { stiffness: 180, damping: 24, mass: 1 },
  },
};

const STORAGE_PRESET_KEY = "forge_motion_preset";
const STORAGE_KNOBS_KEY = "forge_motion_knobs";

let currentPresetName = "elegant";
let currentKnobs = { ...SYSTEM_PRESETS.elegant };
let slowMotion = false;
const listeners = new Set();

function loadPersistedConfig() {
  try {
    const savedPreset = localStorage.getItem(STORAGE_PRESET_KEY);
    if (savedPreset && SYSTEM_PRESETS[savedPreset]) {
      currentPresetName = savedPreset;
    }
    const savedKnobs = localStorage.getItem(STORAGE_KNOBS_KEY);
    if (savedKnobs) {
      const parsed = JSON.parse(savedKnobs);
      currentKnobs = { ...SYSTEM_PRESETS[currentPresetName], ...parsed };
    } else {
      currentKnobs = { ...SYSTEM_PRESETS[currentPresetName] };
    }
  } catch (e) {
    console.warn("[Forge Motion] Failed to read localStorage:", e);
    currentKnobs = { ...SYSTEM_PRESETS.elegant };
  }
  document.documentElement.dataset.motionPreset = currentPresetName;
}

loadPersistedConfig();

export function getActiveConfig() {
  return { ...currentKnobs };
}

export function getActivePresetName() {
  return currentPresetName;
}

export function setMotionPreset(presetName) {
  const norm = String(presetName).toLowerCase();
  const matched = norm === "elegance" ? "elegant" : norm;
  if (!SYSTEM_PRESETS[matched]) {
    console.warn(`[Forge Motion] Unknown preset: ${presetName}. Options: elegant, classic, dynamic, sweet`);
    return currentPresetName;
  }
  currentPresetName = matched;
  currentKnobs = { ...SYSTEM_PRESETS[matched] };
  try {
    localStorage.setItem(STORAGE_PRESET_KEY, matched);
    localStorage.removeItem(STORAGE_KNOBS_KEY);
  } catch (e) {}
  document.documentElement.dataset.motionPreset = matched;
  notifyChange();
  return currentPresetName;
}

export function updateKnob(key, value) {
  currentKnobs[key] = value;
  try {
    localStorage.setItem(STORAGE_KNOBS_KEY, JSON.stringify(currentKnobs));
  } catch (e) {}
  notifyChange();
}

export function resetKnobs() {
  currentKnobs = { ...SYSTEM_PRESETS[currentPresetName] };
  try {
    localStorage.removeItem(STORAGE_KNOBS_KEY);
  } catch (e) {}
  notifyChange();
}

export function toggleSlowMotion() {
  slowMotion = !slowMotion;
  document.documentElement.classList.toggle("motion-slow", slowMotion);
  notifyChange();
  return slowMotion;
}

export function isSlowMotion() {
  return slowMotion;
}

export function isReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function onConfigChange(cb) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function notifyChange() {
  for (const fn of listeners) {
    try { fn(getActiveConfig()); } catch (e) { console.error(e); }
  }
}
