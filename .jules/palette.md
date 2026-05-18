## 2025-03-05 - Hidden Text Labels on Mobile
**Learning:** Buttons with `hidden sm:inline` text labels become icon-only buttons on mobile breakpoints. Without an `aria-label`, they are completely inaccessible to screen reader users on mobile devices, even if they appear accessible on desktop.
**Action:** Always provide an explicit `aria-label` on buttons where the text content is conditionally hidden by responsive utility classes.
