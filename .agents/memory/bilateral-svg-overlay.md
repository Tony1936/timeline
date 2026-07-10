---
name: Bilateral timeline SVG overlay
description: How to correctly draw range connector lines across the above/below bilateral vis.js timeline containers
---

## The problem
`#timeline-above` (orientation: bottom) and `#timeline-below` (orientation: top) are separate DOM containers. A per-container SVG cannot cross the boundary to reach the real axis line in the other container.

## Root cause of the invisible band (CONFIRMED)
`backdrop-filter: blur(1px)` on the wrapper element causes Chrome's GPU compositor to capture everything BELOW the wrapper — including any `position:fixed` SVG on `document.body`, regardless of z-index — as the backdrop to blur. The wrapper's content is then composited ON TOP of the blurred layer. This makes fixed-positioned SVG lines invisible in the area covered by the wrapper's top panel, no matter how high their z-index.

This manifested as an "invisible band" where connector lines from above-section events appeared to stop before reaching the timeline axis.

## The fix
1. **CSS on wrapper**: Replace `backdrop-filter` with `isolation: isolate; position: relative`. `isolation:isolate` creates an explicit stacking context with no compositor interference.
2. **JS SVG placement**: Attach the SVG inside the wrapper element (`position:absolute; top:0; left:0; width:100%; height:100%; z-index:9999; overflow:visible; pointer-events:none`) — NOT on `document.body`. Inside the wrapper's `isolation:isolate` stacking context, z-index:9999 unambiguously beats vis.js's maximum of z-index:10 (from `.vis-overlay`).
3. **JS coordinates**: All coordinates must be **wrapper-relative** — subtract `wrapEl.getBoundingClientRect().top/left` from viewport coordinates.

## Finding axisY correctly
**DO NOT** query `.vis-panel.vis-top .vis-time-axis` — vis.js renders `.vis-time-axis.vis-background` (zero-height) first, `querySelector` returns it and gives `bottom = container.top`.

**DO** query the center panel instead:
```js
// Primary: below has axis at top → orientation: 'top'
var bc = belowEl.querySelector('.vis-panel.vis-center');
if (bc) { axisY = bc.getBoundingClientRect().top - wR.top; }

// Fallback: above-only layout → orientation: 'bottom', axis at bottom
var ac = aboveEl.querySelector('.vis-panel.vis-center');
if (ac) { axisY = ac.getBoundingClientRect().bottom - wR.top; }
```

**Why:** `.vis-panel.vis-center` top = bottom of top-axis panel = exact position of the amber border-bottom line.

## vis.js z-index values (from CDN CSS)
- `.vis-overlay`: z-index 10 (full-container pointer-events overlay — transparent, no background)
- `.vis-item.vis-selected`: z-index 2
- `.vis-item`, `.vis-axis`, `.vis-current-time`: z-index 1
- Our SVG at z-index: 9999 safely above all of them within `isolation:isolate` stacking context.

## Event listeners
Register on both `timelineAbove.on('changed', redraw)` and `timelineBelow.on('changed', redraw)` plus `window.addEventListener('resize', redraw)`.
