# LAG_BASELINE.md — Baseline Performance Measurement

Measured via Microsoft Edge (Headless CDP) at `http://127.0.0.1:8000/?trace=1`.

---

## 1. Idle Check (B7)
```
FAIL B7 idle page made 60 requestAnimationFrame calls in 2000ms
  (first caller: setBootProgress (static/app.js?v=20261015-12:155:52) <- completeBootStage (static/app.js?v=20261015-12:168:3) <- loadAnalysis (static/app.js?v=20261015-12:564:5))
```

---

## 2. In-Flow Panel: `sidebar` (`#sidebar`)

### sidebar CLOSE
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button.rail-button.is-active` |
| 1 ms | `flow[side].to(0)` |
| 85 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open ff-active"` |
| 254 ms | `LONG TASK 86ms` |
| 254 ms | `LONG TASK 168ms` |
| 254 ms | `SLOW FRAME 250ms` |
| 287 ms | `LONG FRAME 260ms scripts: 85ms BUTTON.onclick @ app.js:61548` |
| 454 ms | `parent-of-panel[dock] changed: display=- visibility=- class="forge-app"` |
| 502 ms | `SLOW FRAME 34ms` |
| 869 ms | `flow[side] SETTLED -> closed` |
| 869 ms | `flow[side] onSettle callback finished` |
| 871 ms | `panel[side] changed: display=- visibility=- class="sidebar is-collapsed"` |
| 871 ms | `parent-of-panel[side] changed: display=- visibility=- class="workbench context-is-minimized explorer-is-collapsed"` |
| 1020 ms | `LONG TASK 151ms` |
| 1020 ms | `SLOW FRAME 150ms` |
| 1053 ms | `LONG FRAME 164ms scripts: none (style/layout/paint cost, not JavaScript)` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms -> 1ms
- **PASS** B2 flight (to -> settled) within 900ms -> 868ms
- **PASS** B3 onSettle callback under 30ms -> 0ms
- **FAIL** B4 slow frames (>24ms) at most 2 -> 3 slow frames
- **FAIL** B5 no long tasks / long frames -> 3 long entries
- **PASS** B6 ResizeObserver work <= 30ms -> 0 callbacks, 0ms
- **PASS** B8a no app setTimeout >= 120ms -> none
- **PASS** B8b no wait for transitionend/animationend -> none
- **PASS** B8c no fetch before the flow starts -> none

---

### sidebar OPEN
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button.rail-button.is-active` |
| 1 ms | `flow[side].to(1)` |
| 178 ms | `flow[side].to(1)` |
| 178 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open ff-active"` |
| 178 ms | `parent-of-panel[side] changed: display=- visibility=- class="workbench context-is-minimized"` |
| 300 ms | `LONG TASK 178ms` |
| 300 ms | `LONG TASK 121ms` |
| 301 ms | `SLOW FRAME 300ms` |
| 350 ms | `LONG FRAME 292ms scripts: 178ms BUTTON.onclick @ app.js:61548` |
| 1394 ms | `flow[side] SETTLED -> open` |
| 1394 ms | `flow[side] onSettle callback finished` |
| 1394 ms | `panel[side] changed: display=- visibility=- class="sidebar is-open"` |
| 1497 ms | `LONG TASK 104ms` |
| 1497 ms | `SLOW FRAME 100ms` |
| 1527 ms | `LONG FRAME 111ms scripts: none (style/layout/paint cost, not JavaScript)` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms -> 1ms
- **FAIL** B2 flight (to -> settled) within 900ms -> 1393ms
- **PASS** B3 onSettle callback under 30ms -> 0ms
- **PASS** B4 slow frames (>24ms) at most 2 -> 2 slow frames
- **FAIL** B5 no long tasks / long frames -> 3 long entries
- **PASS** B6 ResizeObserver work <= 30ms -> 0 callbacks, 0ms
- **PASS** B8a no app setTimeout >= 120ms -> none
- **PASS** B8b no wait for transitionend/animationend -> none
- **PASS** B8c no fetch before the flow starts -> none

---

## 3. In-Flow Panel: `bottom-dock` (`#bottom-dock`)

### bottom-dock OPEN
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button#dock-toggle.icon-button.quiet` |
| 1 ms | `flow[dock].to(1)` |
| 14 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock ff-active"` |
| 27 ms | `SLOW FRAME 33ms` |
| 720 ms | `flow[dock] SETTLED -> open` |
| 720 ms | `flow[dock] onSettle callback finished` |
| 720 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock"` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms -> 1ms
- **PASS** B2 flight (to -> settled) within 900ms -> 719ms
- **PASS** B3 onSettle callback under 30ms -> 0ms
- **PASS** B4 slow frames (>24ms) at most 2 -> 1 slow frames
- **PASS** B5 no long tasks / long frames -> 0 long entries
- **PASS** B6 ResizeObserver work <= 30ms -> 0 callbacks, 0ms
- **PASS** B8a no app setTimeout >= 120ms -> none
- **PASS** B8b no wait for transitionend/animationend -> none
- **PASS** B8c no fetch before the flow starts -> none

---

### bottom-dock CLOSE
#### Timeline Events
| Time (ms) | Event |
|---:|---|
| 0 ms | `CLICK button#dock-toggle.icon-button.quiet` |
| 0 ms | `flow[dock].to(0)` |
| 4 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock ff-active"` |
| 460 ms | `flow[dock] SETTLED -> closed` |
| 460 ms | `flow[dock] onSettle callback finished` |
| 460 ms | `panel[dock] changed: display=- visibility=- class="bottom-dock is-collapsed"` |

#### Budget Checks
- **PASS** B1 click -> flow.to() within 50ms -> 0ms
- **PASS** B2 flight (to -> settled) within 900ms -> 460ms
- **PASS** B3 onSettle callback under 30ms -> 0ms
- **PASS** B4 slow frames (>24ms) at most 2 -> 0 slow frames
- **PASS** B5 no long tasks / long frames -> 0 long entries
- **PASS** B6 ResizeObserver work <= 30ms -> 0 callbacks, 0ms
- **PASS** B8a no app setTimeout >= 120ms -> none
- **PASS** B8b no wait for transitionend/animationend -> none
- **PASS** B8c no fetch before the flow starts -> none
