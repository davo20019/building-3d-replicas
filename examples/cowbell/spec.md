# Cowbell: NMAH 2018.0174.01

A hand-held cowbell, red enamel over folded sheet steel, with a black-painted tube handle and two strip
loops beside it. Picked as the public example because everything about it may be published (CC0), it has
no trademarks, and the museum's scan grades the result.

## Dimensions (mm)

| What | Value | Source |
|---|---|---|
| Overall height x width x depth | 266.7 x 88.9 x 63.5 | NMAH record ("10 1/2 in x 3 1/2 in x 2 1/2 in") |
| Mouth width | ~90 | photo, scaled by the published height (3.8 px/mm in a 1200 px preview) |
| Crown width | ~73 | photo |
| Body height (mouth to crown) | ~112 | photo |
| Handle diameter | ~18 | photo |
| Paint line on the handle | ~152 above the mouth | photo |
| Side loops: outer edge, top | ~25 from the centre line, ~135 above the mouth | photo |

All "photo" values are first guesses; `fit_silhouette.py` fits them (params.json) from the photo and four
renders of the scan through known cameras.

## Structure

- Body: a tapered box (rounded rectangle lofted from mouth to crown), 1.5 mm wall, open at the mouth,
  rounded shoulder at the crown.
- Handle: a tube from the crown to the top; red up to the paint line, black above (two parts, so the fit's
  dark channel can place the paint line).
- Loops: square-section strip, out from the handle and down to the crown, one each side.
- Clapper: rod and ball, on a node that swings from the crown.

## Unknowns (guessed, not sourced)

- The published depth (63.5) likely includes something other than the body; the front photo can't show
  depth. The side and low renders fit it.
- Wall thickness, the clapper's size and the folded seam down each narrow side (not modelled).

## Budget

Under 10k triangles, GLB under 500 KB.
