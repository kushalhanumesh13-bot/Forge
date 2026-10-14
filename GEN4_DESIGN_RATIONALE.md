# Forge Gen 4 — Design Rationale

## Direction

Forge is a local engineering workspace, so the interface takes the form of a **field notebook for software investigation**, not an AI chat app or analytics dashboard. It uses warm paper surfaces for orientation and reasoning, a graphite reading surface for source code, and a single ember signal for actions that change state. The contrast between these materials gives the workspace a clear cognitive map: orient, inspect, decide, verify.

## References translated

- The supplied cinematic reference is translated into the boot sequence: staged lettering, quiet rules that frame the viewport, and a measured dissolve into the workbench. There is no supplied video file in the attachment, so this is an original treatment based on the written brief rather than a frame-for-frame recreation.
- The world-time reference informed oversized but restrained editorial display type, exact column alignment, and large numbered workflow waypoints.
- The travel-planning reference informed the warm, spacious paper context layer, but not its consumer-card patterns.
- Current Figma guidance reinforced a small set of intentional visual choices rather than trend accumulation. web.dev's motion guidance shaped the motion reduction and non-blocking transition behavior.
- Developer-tool references reinforced flat, hairline-separated surfaces, real proof over invented statistics, and a single saturated signal color.

## System

| Concern | Decision |
| --- | --- |
| Typography | `Iowan Old Style` / Georgia for editorial display moments; Segoe UI Variable / system UI for controls; Cascadia / system mono for code and paths. |
| Color | Paper `#f4f0e7`, graphite `#20211e`, ember `#bd492d`, pine `#2d6959`; semantic colors are reserved for actual state. |
| Geometry | Square control edges, 1px rules, no card grid, one reading canvas. |
| Motion | 110ms feedback, 180ms local transitions, 420ms boot handoff; opacity and transform only; all reduced to effectively instant under `prefers-reduced-motion`. |
| Workflow | Understand → Investigate → Plan → Review → Verify maps directly to explorer, search, task planning, Git diffs, and the real test command. |

## Scope and honesty

The UI exposes only the existing API operations: repository analysis, text search, file read/write, deterministic planning, Git diff, and the restricted test command. No autonomous modifications, fabricated progress, or fake repository metrics were added.
