---
name: Bilateral timeline SVG overlay
description: How connector lines from range events to the amber axis are implemented; includes all root-cause findings and screenshot-tool limitation
---

## Current architecture (body-fixed SVG)
A `position:fixed; top:0; left:0; width:100vw; height:100vh; z-index:2147483647; pointer-events:none`
SVG is appended to `document.body` from `setupRangeLines()`. It draws:
- A 6px dark + 3px amber dashed line (strokeDasharray "6,4") from each range-event left/right edge to `axisY`
- An amber glow circle (r=10, 22% opacity) + solid amber dot (r=6, border rgba(18,12,4,0.7)) at `axisY`

`redraw()` is called on `timelineAbove.on('changed')`, `timelineBelow.on('changed')`, `resize`, and `scroll`.

## axisY calculation
`axisY` = the viewport Y of the visible amber axis border-bottom in the below top-panel.
vis.js 7.7.0 may have 1 or 2 `.vis-time-axis` elements in the below `vis-panel.vis-top`:
- Sort them by height. If the shortest is < 95% of panel height, use its `.bottom` as axisY.
- Otherwise fall back to `topPanel.getBoundingClientRect().bottom`.
- Further fallback: `belowEl .vis-panel.vis-center` top, or `aboveEl .vis-panel.vis-center` bottom.

## Screenshot tool limitation — gap area
The Replit screenshot tool (headless Chromium) does NOT faithfully composite body-fixed SVG
over the vis.js panels in the ~44px gap between the above and below timeline containers.
**SVG `<line>` elements in this y-band are invisible in screenshots — this is a screenshot artifact only.**
Evidence: amber circles (`makeDot`) AT the same axisY ARE visible in screenshots. SVG circles vs
lines differ in compositing in the screenshot pipeline.
**In a real browser, z-index:2147483647 guarantees the SVG is above all vis.js content.**

## gap size (~44px)
- `#timeline-above .vis-panel.vis-bottom` (above axis bar): ~30px — hidden labels via CSS `display:none`
- `#timeline-below .vis-panel.vis-top` (below date labels): ~14px
- `showMinorLabels: false, showMajorLabels: false` on the above timeline reduces vis.js allocation for axis bar.
- CSS `border: none !important` on `#timeline-above .vis-time-axis` removes the amber border from the above side.

## vis.js z-index reference (7.7.0 CDN)
- `.vis-overlay`: z-index 10
- `.vis-item.vis-selected`: z-index 2
- `.vis-item`, `.vis-axis`, `.vis-current-time`: z-index 1
