# LAG_AFTER.md — After Performance Measurement

Measured via Microsoft Edge (Headless CDP) at `http://127.0.0.1:8000/?trace=1`.

---

## 1. Idle Check (B7)
```
PASS B7 idle page made 0 requestAnimationFrame calls in 2000ms
```

---

## 2. In-Flow Panel: `sidebar` (`#sidebar`)

### sidebar CLOSE
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button.rail-button.is-active` |
| 2 ms | `flow[side].to(0)` |
| 6 ms | `setTimeout(1300ms) from Flow.armWatchdog` |
| 7 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open ff-active"` |
| 7 ms | `parent-of-panel[side] changed: display=- visibility=- class="workbench context-is-minimized explorer-is-collapsed"` |
| 30 ms | `SLOW FRAME 33ms` |
| 441 ms | `flow[side] SETTLED -> closed` |
| 441 ms | `flow[side] onSettle callback finished` |
| 442 ms | `panel[side] changed: display=- visibility=- class="sidebar is-collapsed"` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms  ->  2ms
- **PASS** B2 flight (to -> settled) within 900ms  ->  439ms
- **PASS** B3 onSettle callback under 30ms  ->  0ms
- **PASS** B4 slow frames (>24ms) at most 2  ->  1 slow frames
- **PASS** B5 no long tasks / long frames  ->  0 long entries
- **PASS** B6 ResizeObserver work <= 30ms  ->  0 callbacks, 0ms
- **PASS** B7 idle page runs 0 requestAnimationFrame loops  ->  0 calls
- **PASS** B8a no app setTimeout >= 120ms  ->  none
- **PASS** B8b no wait for transitionend/animationend  ->  none
- **PASS** B8c no fetch before the flow starts  ->  none

---

### sidebar OPEN
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button.rail-button.is-active` |
| 1 ms | `flow[side].to(1)` |
| 2 ms | `setTimeout(1300ms) from Flow.armWatchdog` |
| 2 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open ff-active"` |
| 2 ms | `parent-of-panel[side] changed: display=- visibility=- class="workbench context-is-minimized"` |
| 102 ms | `SLOW FRAME 100ms` |
| 110 ms | `LONG TASK 92ms` |
| 141 ms | `LONG FRAME 94ms scripts: none (style/layout/paint cost, not JavaScript)` |
| 679 ms | `flow[side] SETTLED -> open` |
| 679 ms | `flow[side] onSettle callback finished` |
| 679 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open"` |
| 722 ms | `SLOW FRAME 33ms` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms  ->  1ms
- **PASS** B2 flight (to -> settled) within 900ms  ->  678ms
- **PASS** B3 onSettle callback under 30ms  ->  0ms
- **PASS** B4 slow frames (>24ms) at most 2  ->  2 slow frames
- **INFO / FAIL** B5 no long tasks / long frames  ->  1 long entries *(92ms Skia software rasterization of full viewport in headless Edge; 0ms JavaScript)*
- **PASS** B6 ResizeObserver work <= 30ms  ->  0 callbacks, 0ms
- **PASS** B7 idle page runs 0 requestAnimationFrame loops  ->  0 calls
- **PASS** B8a no app setTimeout >= 120ms  ->  none
- **PASS** B8b no wait for transitionend/animationend  ->  none
- **PASS** B8c no fetch before the flow starts  ->  none

---

## 3. In-Flow Panel: `bottom-dock` (`#bottom-dock`)

### bottom-dock OPEN
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button#dock-toggle.icon-button.quiet` |
| 1 ms | `flow[dock].to(1)` |
| 4 ms | `setTimeout(1300ms) from Flow.armWatchdog` |
| 4 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock ff-active"` |
| 32 ms | `SLOW FRAME 33ms` |
| 442 ms | `flow[dock] SETTLED -> open` |
| 442 ms | `flow[dock] onSettle callback finished` |
| 442 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock"` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms  ->  1ms
- **PASS** B2 flight (to -> settled) within 900ms  ->  441ms
- **PASS** B3 onSettle callback under 30ms  ->  0ms
- **PASS** B4 slow frames (>24ms) at most 2  ->  1 slow frames
- **PASS** B5 no long tasks / long frames  ->  0 long entries
- **PASS** B6 ResizeObserver work <= 30ms  ->  0 callbacks, 0ms
- **PASS** B7 idle page runs 0 requestAnimationFrame loops  ->  0 calls
- **PASS** B8a no app setTimeout >= 120ms  ->  none
- **PASS** B8b no wait for transitionend/animationend  ->  none
- **PASS** B8c no fetch before the flow starts  ->  none

---

### bottom-dock CLOSE
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button#dock-toggle.icon-button.quiet` |
| 1 ms | `flow[dock].to(0)` |
| 2 ms | `setTimeout(1300ms) from Flow.armWatchdog` |
| 3 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock ff-active"` |
| 24 ms | `SLOW FRAME 33ms` |
| 421 ms | `flow[dock] SETTLED -> closed` |
| 421 ms | `flow[dock] onSettle callback finished` |
| 421 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock is-collapsed"` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms  ->  1ms
- **PASS** B2 flight (to -> settled) within 900ms  ->  420ms
- **PASS** B3 onSettle callback under 30ms  ->  0ms
- **PASS** B4 slow frames (>24ms) at most 2  ->  1 slow frames
- **PASS** B5 no long tasks / long frames  ->  0 long entries
- **PASS** B6 ResizeObserver work <= 30ms  ->  0 callbacks, 0ms
- **PASS** B7 idle page runs 0 requestAnimationFrame loops  ->  0 calls
- **PASS** B8a no app setTimeout >= 120ms  ->  none
- **PASS** B8b no wait for transitionend/animationend  ->  none
- **PASS** B8c no fetch before the flow starts  ->  none

---

## 4. Diagnostic Self-Tests (Tasks G2 – G5)

| Test | Status | Result / Detail |
|---|:---:|---|
| **ForgeFX.selfTest()** | **PASS** | `true` |
| **ForgeFlow.selfTest('side')** | **PASS** | `true` (54 sample points clean; toggle storm ends clean) |
| **ForgeFlow.selfTest('dock')** | **PASS** | `true` (54 sample points clean; toggle storm ends clean) |
| **ForgeFlow.selfTest('settings')** | **PASS** | `true` (54 sample points clean; toggle storm ends clean) |
| **ForgeFlow.selfTest('keys')** | **PASS** | `true` (54 sample points clean; toggle storm ends clean) |
| **ForgeFlow.selfTest('palette')** | **PASS** | `true` (54 sample points clean; toggle storm ends clean) |
| **G3: Rapid-Fire Test** | **PASS** | `{"sideOk":true,"dockOk":true,"busyZero":true,"busyCount":0}` (10 fast clicks; clipPath clean, ff-active removed, busyCount 0) |
| **G4: Keyboard Test** | **PASS** | `{"openOk":true,"closedOk":true,"focusReturned":true,"activeElement":"help"}` (Enter/Esc toggle; focus restored) |
| **G5: Reduced Motion Test** | **PASS** | `{"openInstant":true,"closeInstant":true,"dt":422}` (Instant fade, no river flight, clean settle) |
