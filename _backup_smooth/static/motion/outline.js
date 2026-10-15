// motion/outline.js - Topology-matched rounded rectangle outline sampling and geometry helpers

export function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function smoothstep(edge0, edge1, x) {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

/**
 * Samples a rounded rectangle into an 80-point (or pointCount) clockwise polygon
 * Segments:
 *  1. Top edge (start inc, end exc)
 *  2. Top-right corner arc (-90 deg to 0 deg)
 *  3. Right edge
 *  4. Bottom-right corner arc (0 deg to 90 deg)
 *  5. Bottom edge
 *  6. Bottom-left corner arc (90 deg to 180 deg)
 *  7. Left edge
 *  8. Top-left corner arc (180 deg to 270 deg)
 */
export function roundedRectOutline({ x, y, w, h, r = 0 }, edgeN = 12, cornerN = 8) {
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  const P = [];

  const edge = (x0, y0, x1, y1) => {
    for (let i = 0; i < edgeN; i++) {
      const t = i / edgeN;
      P.push(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t);
    }
  };

  const arc = (cx, cy, a0) => {
    for (let i = 0; i < cornerN; i++) {
      const a = ((a0 + (90 * i) / cornerN) * Math.PI) / 180;
      P.push(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
  };

  // Top edge & TR corner
  edge(x + r, y, x + w - r, y);
  arc(x + w - r, y + r, -90);

  // Right edge & BR corner
  edge(x + w, y + r, x + w, y + h - r);
  arc(x + w - r, y + h - r, 0);

  // Bottom edge & BL corner
  edge(x + w - r, y + h, x + r, y + h);
  arc(x + r, y + h - r, 90);

  // Left edge & TL corner
  edge(x, y + h - r, x, y + r);
  arc(x + r, y + r, 180);

  return new Float32Array(P);
}

/**
 * Compute lag weights for outline S with respect to movement direction `dir` (unit vector).
 * w_i = 0.5 + 0.5 * dot(unit(S_i - S_center), dir)
 * w = 1 on the leading side (facing destination), 0 on the trailing side.
 */
export function computeLagWeights(outline, center, dir) {
  const numPoints = outline.length / 2;
  const weights = new Float32Array(numPoints);

  for (let i = 0; i < numPoints; i++) {
    const px = outline[i * 2];
    const py = outline[i * 2 + 1];
    const dx = px - center.x;
    const dy = py - center.y;
    const len = Math.hypot(dx, dy) || 1e-5;
    const ux = dx / len;
    const uy = dy / len;
    const dot = ux * dir.x + uy * dir.y;
    weights[i] = clamp(0.5 + 0.5 * dot, 0, 1);
  }

  return weights;
}

/**
 * Get centroid of a Float32Array outline
 */
export function computeCentroid(outline) {
  const numPoints = outline.length / 2;
  let sx = 0;
  let sy = 0;
  for (let i = 0; i < numPoints; i++) {
    sx += outline[i * 2];
    sy += outline[i * 2 + 1];
  }
  return { x: sx / numPoints, y: sy / numPoints };
}

/**
 * Get DOM element bounding rect with computed border-radius
 */
export function getElementGeometry(element) {
  if (!element || !element.isConnected) return null;
  const rect = element.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return null;

  const style = window.getComputedStyle(element);
  const rTopLeft = parseFloat(style.borderTopLeftRadius) || 0;
  const rTopRight = parseFloat(style.borderTopRightRadius) || 0;
  const rBottomRight = parseFloat(style.borderBottomRightRadius) || 0;
  const rBottomLeft = parseFloat(style.borderBottomLeftRadius) || 0;
  const avgRadius = (rTopLeft + rTopRight + rBottomRight + rBottomLeft) / 4;

  return {
    x: rect.left,
    y: rect.top,
    w: rect.width,
    h: rect.height,
    r: avgRadius,
    rect,
  };
}
