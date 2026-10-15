// motion/stack.js - Surface registry, group coordination, z-order, Esc and outside-click handling

class SurfaceStack {
  constructor() {
    this.surfaces = new Map(); // id -> surface instance
    this.openStack = [];       // array of surface ids in z-order (most recent on top)
    this.groups = new Map();   // groupName -> Set of surface ids
    this.hasBoundGlobalEvents = false;
  }

  ensureGlobalListeners() {
    if (this.hasBoundGlobalEvents || typeof window === "undefined") return;
    this.hasBoundGlobalEvents = true;

    // Esc closes topmost open surface that permits Esc closing
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        for (let i = this.openStack.length - 1; i >= 0; i--) {
          const surface = this.surfaces.get(this.openStack[i]);
          if (!surface || (surface.state !== "open" && surface.state !== "opening")) continue;
          if (surface.closeOnEsc === false) continue;
          e.preventDefault();
          e.stopPropagation();
          surface.close();
          break;
        }
      }
    }, { capture: true });

    // Outside-click handling
    window.addEventListener("pointerdown", (e) => {
      for (let i = this.openStack.length - 1; i >= 0; i--) {
        const surface = this.surfaces.get(this.openStack[i]);
        if (!surface || (surface.state !== "open" && surface.state !== "opening")) continue;
        if (surface.closeOnOutsideClick === false) continue;

        const trigger = surface.getTriggerElement ? surface.getTriggerElement() : surface.trigger;
        const panel = surface.getPanelElement ? surface.getPanelElement() : surface.panel;

        // Ignore clicks on trigger or inside panel
        if (trigger && (trigger === e.target || trigger.contains(e.target))) continue;
        if (panel && (panel === e.target || panel.contains(e.target))) continue;

        surface.close();
      }
    }, { capture: true });
  }

  register(surface) {
    this.ensureGlobalListeners();
    this.surfaces.set(surface.id, surface);

    const group = surface.group || "default";
    if (!this.groups.has(group)) {
      this.groups.set(group, new Set());
    }
    this.groups.get(group).add(surface.id);
  }

  unregister(surfaceId) {
    this.surfaces.delete(surfaceId);
    this.openStack = this.openStack.filter((id) => id !== surfaceId);
    for (const members of this.groups.values()) {
      members.delete(surfaceId);
    }
  }

  onSurfaceOpening(surface) {
    const group = surface.group || "default";
    // Check if another surface in the same group is open or opening
    const groupMembers = this.groups.get(group);
    if (groupMembers) {
      for (const id of groupMembers) {
        if (id !== surface.id) {
          const sibling = this.surfaces.get(id);
          if (sibling && (sibling.state === "open" || sibling.state === "opening")) {
            // Close old surface
            sibling.close();
          }
        }
      }
    }

    if (!this.openStack.includes(surface.id)) {
      this.openStack.push(surface.id);
    }
  }

  onSurfaceClosed(surface) {
    const id = typeof surface === "string" ? surface : surface?.id;
    this.openStack = this.openStack.filter((item) => item !== id);
  }

  getTopmostOpen() {
    for (let i = this.openStack.length - 1; i >= 0; i--) {
      const surface = this.surfaces.get(this.openStack[i]);
      if (surface && (surface.state === "open" || surface.state === "opening")) {
        return surface;
      }
    }
    return null;
  }

  getSurface(id) {
    return this.surfaces.get(id);
  }

  getAllSurfaces() {
    return Array.from(this.surfaces.values());
  }
}

export const stack = new SurfaceStack();
