---
name: Bilateral timeline dot fix
description: Root cause and fix for D-shaped half-circle dots at the amber axis seam in the bilateral vis.js timeline
---

## Root Cause

Above-panel events in the bilateral timeline render as `.vis-item.vis-box` (point/box events), **not** `.vis-item.vis-range`. The original code only queried `.vis-item.vis-range`, so it found zero above-panel items — explaining why connector lines appeared (from vis.js's own `.vis-item.vis-line` built-ins) but no custom dots were generated.

Vis.js's built-in `.vis-item.vis-dot` elements for box events appear as **D-shaped half-circles** because the vis.js panel that should show the lower half (`vis-panel-bottom` for above, `vis-panel-top` for below) is collapsed to `height: 0 !important; overflow: hidden !important` — clipping the dot's lower (or upper) hemisphere.

## Fix

1. **CSS** — hide vis.js built-in connectors and dots:
   ```css
   .vis-item.vis-line,
   .vis-item.vis-dot { display: none !important; }
   ```

2. **JS** — handle both item types in `drawLinesFor()`:
   - `.vis-item.vis-range` → connector at left **and** right edges (existing behaviour)
   - `.vis-item.vis-box` → connector at center-x (`(r.left + r.right) / 2 - wrapRect.left`)
   - Both push `{ x, dotY: axisY }` to the dots array

3. **Dots** rendered as HTML `<div>`s in `dotLayer` (`position:absolute; z-index:1000` inside `.timeline-wrapper`), not SVG circles — avoids SVG compositor-layer clipping issues.

**Why:** `overflow: hidden` on a flex child in Chrome can promote it to a GPU compositing layer that paints over absolutely-positioned siblings at lower z-indices. HTML divs in a separate absolutely-positioned dotLayer are not affected by this.

## Key selector facts (vis.js 7.7.0)
- Range items (start + end date): `.vis-item.vis-range`
- Point/box items (start date only): `.vis-item.vis-box`
- Built-in connector line: `.vis-item.vis-line`
- Built-in axis dot: `.vis-item.vis-dot`
