# Design system

One visual language for the whole platform. The React dashboard (`frontend/`) implements it; the classic pages share the same palette through `dashboard/assets/css/tokens.css` until they are rebuilt.

## Colour tokens

Defined once in `frontend/src/styles/tokens.css` and mapped to Tailwind names in `frontend/tailwind.config.ts`. Components use the names, never hex values.

| Token | Value | Use |
| --- | --- | --- |
| `forest` | #064E3B | Navigation, headings |
| `primary` / `primary-strong` | #087F5B / #065F46 | Actions, links, positive figures |
| `fresh` | #42B883 | Accents, focus ring |
| `mint` | #DFF4E7 | Soft positive fills |
| `canvas` | #F8FBF8 | Page background |
| `surface` | #FFFFFF | Cards |
| `ink` / `muted` | #17352C / #5C7066 | Body and secondary text |
| `line` | #DFE8E1 | Borders |
| `amber` / `amber-soft` | #925E08 / #FCF2DC | Warnings, demonstration data |
| `critical` / `critical-soft` | #BE3A34 / #FCE9E7 | Critical incidents, offline assets |
| `water` / `water-soft` | #1A688E / #E2F1F9 | Rainfall, citizen-report source |

The brief's amber (#D99828), red (#D9544D) and blue (#278AB8) are too light for text. The text tokens are darkened versions that meet WCAG AA (at least 4.5:1) on the canvas, on white and on their own soft fill; the original shades remain suitable for large chart marks.

Type: **Manrope** for headings and figures, **DM Sans** for text, both stored locally (no internet needed). Radius: 16 px cards, 10 px controls.

## Reading a figure honestly

Every headline figure is a `MetricCard` fed by a metric envelope from the API (`backend/app/services/executive.py`):

- **value and unit**: a missing value reads "No data", never 0;
- **period**: "Last 30 days", "Now", "Latest report per asset";
- **source badge**, in words and colour: *Citizen reports, unverified* · *Platform record* · *Documented* · *Demonstration data* · *Not enough data*;
- **note**: the denominator or the reason a value is missing;
- **definition**: behind the ⓘ button, so the card stays calm.

No trend arrows or growth percentages are shown until there is a validated baseline period to compare against.

## Data states

`DataState` is used everywhere data can be absent: loading (spinner, `role=status`), empty (an explanation of how data arrives, e.g. "dial *801#"), error and unreachable (`role=alert` with a retry). Skeletons hold the layout while loading; they never show placeholder numbers. A banner marks demonstration databases on every overview.

## Components

| Component | File |
| --- | --- |
| Card, CardHeader | `frontend/src/components/ui/Card.tsx` |
| Badge, SourceBadge | `frontend/src/components/ui/Badge.tsx`, `SourceBadge.tsx` |
| MetricCard | `frontend/src/components/ui/MetricCard.tsx` |
| Select (labelled native select) | `frontend/src/components/ui/Select.tsx` |
| Skeleton | `frontend/src/components/ui/Skeleton.tsx` |
| DataState | `frontend/src/components/feedback/DataState.tsx` |
| Sidebar, TopBar | `frontend/src/components/navigation/` |
| SchemeChart (Recharts, with a hidden data table) | `frontend/src/components/charts/SchemeChart.tsx` |
| SectorMap (Leaflet) | `frontend/src/components/maps/SectorMap.tsx` |

## Accessibility rules

- Every control has a visible label or an `sr-only` name; icons are `aria-hidden`.
- Status is never shown by colour alone (badges carry words).
- Charts and maps have a text alternative (hidden table, sector list).
- Visible focus ring on every interactive element; a "skip to main content" link.
- The closed mobile menu is removed from the tab order.
- `prefers-reduced-motion` turns animations off.
- Heavy libraries (Leaflet, Recharts) load only when their card renders, for low-bandwidth connections; built assets are cached for a year by file hash.

## Language

Interface text lives in `frontend/src/i18n/en.ts` (the source of every key) and `rw.ts`. Missing Kinyarwanda keys fall back to English. All Kinyarwanda strings need review by native-speaking field staff before the pilot; strings reused from the classic dashboard are marked "existing".
