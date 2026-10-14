# Forge Motion System Specification & Documentation

Forge uses vanilla JavaScript (ES modules) and CSS served by FastAPI. The motion layer is zero-dependency, framework-agnostic, completely reversible, and runs at 60fps on a single `requestAnimationFrame` loop.

---

## 1. Core Principles (Implemented to User Direction)

1. **Springy Spongy Morphing (Panel Open & Close Only)**:
   - Fluid, organic spring morphing occurs **only** when opening a new surface or closing a surface.
   - **Sidebar**:
     - When closed: clicking any rail icon (Explore, Search, Review, Plan) smoothly expands the sidebar out from that button's coordinates to 274px via the `morphOpen` spring ($k=170, c=22, m=1$).
     - When open: clicking the active button again or `#sidebar-close` funnels the sidebar back into that icon with an expressive `iconBounce` ($k=320, c=15$).
   - **Settings & Keys Floating Panels**:
     - Expand out directly from their respective rail button origins into bounded floating cards.
     - Close by funnelling back into the button with velocity preservation and landing bounce.
   - **Verification Dock**:
     - Smooth spring height transition between 41px and 190px.
   - **Command Palette**:
     - Pops open with spring scale and triggers subtle background recede (`.motion-receding`).

2. **In-Panel Content Switching (When Sidebar is Already Open)**:
   - When the sidebar is already open and docked, clicking a different rail view (e.g. Explore $\to$ Search $\to$ Review):
     - **The sidebar container DOES NOT morph.**
     - The **Rail Indicator** (translucent dock pill) glides smoothly along the rail using the `glide` spring ($k=170, c=26$).
     - The **Sidebar Content** undergoes a fluid **directional slide-fade**:
       - Navigating down the rail: outgoing slides up slightly and fades; incoming slides up from $+16\text{px}$ to $0$ with a spring settle.
       - Navigating up the rail: outgoing slides down and fades; incoming slides down from $-16\text{px}$ to $0$.
       - The header labels crossfade with a subtle vertical nudge.
       - Incoming views use absolute positioning (`top: 76px; inset: 76px 0 0 0`) during transition to eliminate flex layout squishing.

3. **Cinematic Liquid Iris Boot Transition**:
   - When workspace analysis completes on the boot screen:
     - An expanding liquid iris aperture (`clip-path: circle(...)`) pulls open from the center outward, revealing the workspace underneath.
     - The boot screen letters converge and fade gracefully.
     - The workspace (`#forge-app`) emerges with physical depth, scaling up from `scale(0.965)` to `scale(1.0)` and brightening from $0.88$ to $1.0$.
     - The top navigation bar and activity rail slide smoothly into place (`translateY(-10px) -> 0`, `translateX(-10px) -> 0`).
     - Once settled, all inline transforms and masks are removed, leaving a pristine DOM.

---

## 2. File Structure

All motion modules reside in [`app/static/motion/`](file:///e:/Projects/001/app/static/motion/):

- [`config.js`](file:///e:/Projects/001/app/static/motion/config.js): Motion tokens, spring presets, damping ratios, and persistence.
- [`spring.js`](file:///e:/Projects/001/app/static/motion/spring.js): 240Hz sub-stepped second-order semi-implicit Euler numerical spring solver.
- [`scheduler.js`](file:///e:/Projects/001/app/static/motion/scheduler.js): Global single rAF execution loop.
- [`morph.js`](file:///e:/Projects/001/app/static/motion/morph.js): Clean, direct element-level spring morphing (zero `#motion-root` DOM reparenting).
- [`indicator.js`](file:///e:/Projects/001/app/static/motion/indicator.js): Sliding indicator system powering the translucent dock pill, tab indicators, and step bars.
- [`motion.css`](file:///e:/Projects/001/app/static/motion/motion.css): CSS variables, translucent dock pill styling, and reduced-motion fallbacks.

---

## 3. Presets & Physics Specs

| Preset | Stiffness ($k$) | Damping ($c$) | Mass ($m$) | Damping Ratio ($\zeta$) | Behavior |
|---|---:|---:|---:|---:|---|
| **glide** | 170 | 26 | 1.0 | ~1.00 | Critically damped, zero overshoot. Used for rail indicator and tabs. |
| **settle** | 200 | 22 | 1.0 | 0.78 | ~3% gentle overshoot. Used for dialogs and content reveals. |
| **morphOpen** | 170 | 22 | 1.0 | 0.84 | Organic expansion from trigger origin. |
| **morphClose** | 230 | 27 | 1.0 | 0.89 | Asymmetric, snappy funnel return into trigger. |
| **iconBounce** | 320 | 15 | 1.0 | 0.42 | Expressive landing bounce on trigger icon. |
