---
name: Bilateral timeline SVG overlay
description: How connector lines and the custom axis line/labels are implemented; confirmed root causes and architecture
---

## Architecture (current)

### Custom axis strip (#tl-axis)
A 28px `<div id="tl-axis">` sits between `#timeline-above` and `#timeline-below` as a flex child
of `.timeline-wrapper`. It is shown only in bilateral mode (`hasAbove && hasBelow`).
It has no visible CSS — the amber line and year labels are drawn entirely in the body-fixed SVG.

### Body-fixed SVG (z-index:2147483647)
Appended to `document.body` from `setupRangeLines()`. `redraw()` draws in this order:
1. **Dark backdrop rect** — from `aboveCenter.bottom` to `axisY+2` (covers vis.js axis bar remnant + custom axis area). Fill `rgba(10,14,20,0.78)`. Needed because the gap has no group-row dark overlay so the medieval bg makes thin lines invisible.
2. **SVG amber axis line** — 2px rect at `axisY-1` to `axisY+1`, full content width. Fill `rgba(250,180,50,0.70)`.
3. **Year labels** — SVG `<text>` elements at `y = axisY - 6` (baseline 6px above line centre). Colour `#fbbf24`, font-size 11, font-weight 600. Interval chosen so ≤10 labels appear (steps array: 1,2,5,10,25,50,100,200,250,500,1000,2000,5000).
4. **Connector lines** — 6px dark shadow + 3px amber glowing dashed line (dasharray "6,4") from each range-event left/right edge to `axisY`.
5. **Dots** — amber glow circle (r=10, 22% opacity) + solid amber dot (r=6) at `axisY`.

Listeners: `timelineAbove.on('changed')`, `timelineBelow.on('changed')`, `resize`, `scroll`.

### axisY derivation
```js
var axR = tlAxisEl.getBoundingClientRect();
axisY = axR.bottom - 1;  // centre of the 2px amber line (drawn at bottom of #tl-axis)
```
Fallback (single-side mode): `belowEl .vis-panel.vis-center .top` or `aboveEl .vis-panel.vis-center .bottom`.

### gapTop
```js
var aboveCenter = aboveEl.querySelector('.vis-panel.vis-center');
gapTop = aboveCenter.getBoundingClientRect().bottom;
```

## Layout height maths (calcLayout)
```
bilateral=true : axisBarH=0,  customH=28, perG=(totalH-28)/totalGroups
                 aboveH = aboveGroups*perG,  belowH = belowGroups*perG
bilateral=false: axisBarH=52, customH=0,  perG=(totalH-52)/totalGroups
                 aboveH/belowH = groups*perG + 52
```

## vis.js options — both timelines in bilateral mode
```js
showMinorLabels: false,
showMajorLabels: false
```
This collapses vis.js's internal axis bar to near-zero, leaving only our SVG axis.

## Root cause — lines invisible in gap (CONFIRMED)
Thin dashed lines are invisible against the medieval bg image in the gap area (no group-row overlay).
Fixed by drawing a dark SVG backdrop rect before any lines. Dots (r=6) always visible regardless.

## Glow filter (SVG defs, created once at setup)
```
feGaussianBlur stdDeviation="2.5" → feMerge(blur, SourceGraphic)
```
Applied via `filter="url(#rl-glow)"` on the amber (foreground) connector line elements only.

## vis.js z-index reference (7.7.0 CDN)
`.vis-overlay`: 10 · `.vis-item.vis-selected`: 2 · `.vis-item/.vis-axis/.vis-current-time`: 1
Our SVG at z-index:2147483647 in the body stacking context is above all of them.
