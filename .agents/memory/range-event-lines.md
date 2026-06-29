---
name: Range event date lines
description: Pending feature — draw vertical connector lines from both ends of a range event box to the timeline axis dates
---

# Feature: Connector lines for range events

## Request
Events that span a date range (start + end) should show a vertical line dropping from **both** the left edge (start date) and the right edge (end date) of the event box down to the timeline axis, making it clear exactly which dates are covered.

Currently Vis.js only draws a line at the start date for range items.

## Approach to investigate
- Vis.js Timeline `type: 'range'` items do not natively draw a line at the end date.
- Options:
  1. Use the Vis.js `afterRender` / `changed` event to find rendered range item DOM elements and inject SVG/div lines for both edges.
  2. Override CSS to show a border on the right edge of `.vis-item.vis-range` that visually implies the end boundary.
  3. Draw on a canvas overlay positioned behind the timeline.
- Option 1 (DOM injection after render) is most flexible and precise.

## Why
User explicitly requested this; it improves readability of multi-year events on the medieval timeline.
