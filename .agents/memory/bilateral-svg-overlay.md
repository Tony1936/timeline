---
name: Bilateral timeline SVG overlay
description: How to correctly compute axisY and render range connector lines across the above/below bilateral vis.js timeline containers
---

## The problem
`#timeline-above` (orientation: bottom) and `#timeline-below` (orientation: top) are separate DOM containers. A per-container SVG cannot cross the boundary to reach the real axis line in the other container. z-index stacking contexts inside vis.js panels also occlude sibling SVGs.

## The fix
Attach ONE SVG to `document.body` with `position: fixed; z-index: 9999; overflow: visible`. Use raw viewport coordinates from `getBoundingClientRect()` — no subtraction needed. This beats every stacking context.

## Finding axisY correctly
**DO NOT** query `.vis-panel.vis-top .vis-time-axis` — vis.js 7.7.0 renders BOTH `.vis-time-axis.vis-background` (zero-height) and `.vis-time-axis.vis-foreground`, and `querySelector` returns the background one first, giving `bottom = container.top`.

**DO** query the center panel instead — its top/bottom edge is the exact axis position:
```js
// Primary (below has axis at top → orientation: 'top')
var bc = belowEl.querySelector('.vis-panel.vis-center');
if (bc) { axisY = bc.getBoundingClientRect().top; }

// Fallback (above-only layout → orientation: 'bottom', axis at bottom)
var ac = aboveEl.querySelector('.vis-panel.vis-center');
if (ac) { axisY = ac.getBoundingClientRect().bottom; }
```

**Why:** `.vis-panel.vis-center` top = bottom of top-axis panel = exact position of the `border-bottom` amber line.

## Diagnosing axisY
Add a temporary `<line stroke="magenta" x1="0" x2="3000" y1=axisY y2=axisY>` to the SVG `<g>` element. A screenshot shows where the code thinks the axis is relative to the visible amber line.

## Event listeners
Register on both `timelineAbove.on('changed', redraw)` and `timelineBelow.on('changed', redraw)` plus `window.addEventListener('resize', redraw)`.
