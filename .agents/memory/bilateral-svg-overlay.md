---
name: Bilateral timeline SVG overlay
description: How to correctly draw range connector lines across the above/below bilateral vis.js timeline containers, including all root-cause findings
---

## Architecture
`#timeline-above` (orientation:'bottom') sits above `#timeline-below` (orientation:'top').
A wrapper-level SVG (`position:absolute; top:0; left:0; width:100%; height:100%; z-index:9999; overflow:visible`) draws amber dashed connector lines across both sections.
The wrapper has `isolation:isolate; position:relative` — this creates a clean stacking context so z-9999 beats vis.js's max z-index of 10 (`.vis-overlay`).

## Root cause 1 — `backdrop-filter` (RESOLVED)
`backdrop-filter: blur(1px)` on `.timeline-wrapper` caused Chrome's GPU compositor to capture the body-fixed SVG as the "backdrop" to blur, then composite the wrapper's content on top. The SVG was invisible regardless of z-index. Fix: replace `backdrop-filter` with `isolation:isolate; position:relative`. Move SVG inside wrapper (not body-fixed).

## Root cause 2 — lines invisible in gap area (RESOLVED)
The gap between the above and below sections has a **lighter background** than the group-row area (which has `.vis-foreground .vis-group { background:rgba(15,20,30,0.6) }` overlay). Amber dashed lines at 2.25px were invisible against this lighter background. Fixes:
1. Draw a dark fill rect (`rgba(10,14,20,0.72)`) in the SVG covering the gap area (from above center-panel bottom to axisY). This fills the gap with the same dark tone as the group rows, making lines visible.
2. Increase stroke-width to 3px, full opacity `rgba(251,191,36,1.0)`.
3. Add SVG `feGaussianBlur` glow filter to the `<g>` element so lines glow against any background.

## Root cause 3 — dots wrong position (RESOLVED)
Using `.vis-panel.vis-center` top as `axisY` placed dots below the visible amber axis line. The correct target is `.vis-panel.vis-top .vis-time-axis.vis-foreground` bottom, which is exactly where the `border-bottom: 3px solid amber` lives.

Fallback chain for axisY (bilateral mode):
```js
// Primary: below section has orientation:'top' — axis is at top of center panel
var fga = belowEl.querySelector('.vis-panel.vis-top .vis-time-axis.vis-foreground');
if (fga) { axisY = fga.getBoundingClientRect().bottom - wR.top; }
else {
    var tp = belowEl.querySelector('.vis-panel.vis-top');
    if (tp) { axisY = tp.getBoundingClientRect().bottom - wR.top; }
    else {
        var bc = belowEl.querySelector('.vis-panel.vis-center');
        if (bc) { axisY = bc.getBoundingClientRect().top - wR.top; }
    }
}
// Fallback: above-only layout
var fgb = aboveEl.querySelector('.vis-panel.vis-bottom .vis-time-axis.vis-foreground');
if (fgb) { axisY = fgb.getBoundingClientRect().top - wR.top; }
else {
    var ac = aboveEl.querySelector('.vis-panel.vis-center');
    if (ac) { axisY = ac.getBoundingClientRect().bottom - wR.top; }
}
```

## Root cause 4 — "imaginary role gap" (RESOLVED)
The above timeline's axis bar (`.vis-panel.vis-bottom`) has no group-row backgrounds, making it appear as an empty row between the above groups and the date-label area. Fix: extend the dark fill rect to start at the above CENTER PANEL bottom (`aboveEl.querySelector('.vis-panel.vis-center').getBoundingClientRect().bottom`), not the container bottom. This covers both the above axis-bar area and the below top-panel area with a unified dark fill.

**Note:** vis.js collapses the above axis bar to near-zero height when labels are hidden (`display:none`), so the practical effect is the dark fill mainly covers the below top-panel (~40px).

## vis.js z-index values (from CDN CSS 7.7.0)
- `.vis-overlay`: z-index 10 (full-container transparent pointer-events catcher)
- `.vis-item.vis-selected`: z-index 2
- `.vis-item`, `.vis-axis`, `.vis-current-time`: z-index 1
- Our SVG at z-index:9999 within `isolation:isolate` stacking context is safely above all of them.

## Confirmed SVG rendering in gap (from debug session)
Adding a `rgba(255,0,255,0.45)` debug rect to the SVG over the gap area confirmed the SVG IS rendering in the gap. The "invisible lines" issue was the light background — not a z-index or compositor problem. The dark fill approach (drawing a dark SVG rect in the gap) definitively solves the visibility problem.

## Event listeners
Register on both `timelineAbove.on('changed', redraw)` and `timelineBelow.on('changed', redraw)` plus `window.addEventListener('resize', redraw)`.
