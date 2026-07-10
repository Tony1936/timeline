---
name: Bilateral timeline SVG overlay
description: How connector lines from range events to the amber axis are implemented; confirmed root cause and fixes
---

## Current architecture (body-fixed SVG)
A `position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:2147483647; pointer-events:none`
SVG is appended to `document.body` from `setupRangeLines()`. It draws:
1. A dark background rect spanning the gap band (gapTop → axisY) to ensure contrast
2. A 6px dark shadow + 3px amber glowing dashed line (strokeDasharray "6,4") from each range-event left/right edge to `axisY`
3. An amber glow circle (r=10, 22% opacity) + solid amber dot (r=6) at `axisY`

`redraw()` is called on `timelineAbove.on('changed')`, `timelineBelow.on('changed')`, `resize`, and `scroll`.

## Root cause — lines invisible in gap (CONFIRMED)
The gap between the two timelines (~44px) has NO `.vis-foreground .vis-group` dark overlay.
The medieval background image shows through at full brightness. A 3px dashed amber line is
**invisible against the complex medieval image texture** — this is a pure visual contrast problem,
NOT a z-index or compositor problem. The SVG IS above vis.js; the lines just can't be SEEN.

Evidence: amber dots (r=6/r=10) at the same axisY ARE always visible — large filled circles
provide enough area to overcome the busy background. Thin lines do not.

**Fix: draw a dark SVG rect (`rgba(10,14,20,0.75)`) covering the gap area in the SVG itself.**
This gives the amber lines the same dark-background contrast as inside the group rows.
Add an SVG `feGaussianBlur` glow filter on the amber lines (stdDeviation 2.5) for extra pop.

## gapTop computation
```js
var aboveCenter = aboveEl.querySelector('.vis-panel.vis-center');
if (aboveCenter) { gapTop = aboveCenter.getBoundingClientRect().bottom; }
```
The gap rect x-offset = `.vis-panel.vis-left` width (the group-labels column, ~160px).

## axisY computation
`axisY` = viewport Y of the amber border-bottom in the below top-panel.
- Sort `.vis-time-axis` elements in the below `vis-panel.vis-top` by height.
- If the shortest is < 95% of the panel height → use its `.bottom` as axisY.
- Otherwise fall back to `topPanel.getBoundingClientRect().bottom`.
- Final fallbacks: `.vis-panel.vis-center` top (below), then center bottom (above).

## Glow filter (in SVG defs, created once at setup)
```
feGaussianBlur stdDeviation="2.5" → feMerge(blur, SourceGraphic)
```
Applied via `filter="url(#rl-glow)"` on the amber (foreground) line element only.

## vis.js z-index reference (7.7.0 CDN)
- `.vis-overlay`: z-index 10
- `.vis-item.vis-selected`: z-index 2
- `.vis-item`, `.vis-axis`, `.vis-current-time`: z-index 1
- Our SVG at z-index:2147483647 in the body stacking context is safely above all of them.

## gap size (~44px)
- `#timeline-above .vis-panel.vis-bottom` (above axis bar): ~30px — labels hidden via CSS
- `#timeline-below .vis-panel.vis-top` (below date labels): ~14px
- `showMinorLabels: false, showMajorLabels: false` on the above timeline reduces vis.js allocation.
- CSS `border: none !important` on `#timeline-above .vis-time-axis` removes the above amber border.
