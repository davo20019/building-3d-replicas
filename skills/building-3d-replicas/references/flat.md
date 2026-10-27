# Paintings and other flat objects

A painting on panel or canvas, a drawing, a document, a map, a textile: objects whose shape is almost a
rectangle and whose realism is almost all in their surface. The worked example is the Mona Lisa (a poplar
panel, from the C2RMF scan). Read with evidence.md; the workflow is the same, but the photo is the texture.

## Contents

- Evidence: the scan, the sizes, the licence
- Straightening the scan onto the object
- Surface: relief, varnish and roughness from the scan
- The parts nobody photographs
- Texture budget
- How it is shown

## Evidence: the scan, the sizes, the licence

- **A faithful scan of a public-domain 2D work is public domain** in the US (Bridgeman v. Corel) and the EU
  (DSM Directive, art. 14). Wikimedia Commons hosts many museum-lab scans at full resolution; prefer the
  original upload to a "retouched" or "restored" derivative, which a contributor cropped, relevelled or
  repainted.
- **Choose a scan of the whole object**, edges included: the bare margins, the wear and the ridge of paint
  left by the original frame (the "barbe") are part of the object, and they give you the outline to
  straighten on.
- **The holding museum's catalogue entry beats an encyclopedia for sizes**, and the scan settles a conflict:
  its pixel ratio is a measurement. The Mona Lisa's scan gave 0.6772 against the Louvre's 0.6725 (794 x 534 mm)
  and Wikipedia's 0.688 (77 x 53 cm); its two pixel scales agreed to 0.7 %.
- **"Free" museum image sites are often non-commercial only.** The Louvre's collection images are free for
  listed private uses and otherwise licensed through its photo agency. Take numbers from them; use the images
  only to compare; ship only what is public domain or openly licensed.
- **Conservation papers carry the structure**: thickness, warp, cracks, repairs, the frame and its history.
  Each number goes in spec.md with its source.

## Straightening the scan onto the object

- Big scans are mosaics, slightly skewed. Find the object's edges where it meets the background (a colour
  difference such as R - B for wood on grey cloth), fit a line to each edge over its middle 90 % with a robust
  fit (the corners are worn), and take the corners from the lines' intersections. Then one perspective warp to
  the published size.
- Worn edges leave background inside the rectangle: inpaint it from the object next to it, only within a
  thin band at the edges, and record how many pixels were filled.
- Make texture sizes powers of two even when the object's ratio isn't: the UVs carry the ratio.

## Surface: relief, varnish and roughness from the scan

- **Relief can be read from the scan, but it is inferred, not measured.** Craquelure and wood grain are thin
  lines darker than their surroundings: (local blur - fine blur) / local blur, so a crack in a dark robe
  counts as much as one in the sky. Turn that into a height and a normal map. Anything wider than about a
  millimetre is the image itself, not relief. Mark the depth as a guess.
- **Varnish is a clear coat over satin paint.** Let the coat carry the shine and keep the paint's own
  reflection low (F0 about a quarter of a dielectric's), or a low light makes a grey haze across dark areas.
  Roughness: rougher in the cracks, matte on bare wood.
- **Raking light is the test.** A lamp a few degrees off the surface (15 degrees still reaches it) shows every
  crack throwing a shadow and the warp as a slow change in shine. If the relief is wrong, it shows there.

## The parts nobody photographs

The back, the edges and the frame usually have no shippable photo. Build them as they are made from the
published structure (the panel's thickness and warp, cross-grain keys, linings, the support frame and its
bars) and mark positions and sizes as estimates. A frame with no measured drawing gets a period stand-in,
kept quiet so it doesn't pass as a copy, and the card says so.

- **Measure a warp from what the edges rest on, not from the corners.** A cupped panel's most forward edge
  point touches the frame's straight rebate and its corners stand back. Measured from its corners, the
  Mona Lisa's top and bottom edges came 3.5 mm through the frame's front and flickered in the headset.

## Texture budget

Work from what the headset can resolve, not from the scan. A Quest-class headset resolves about 25 px per
degree: 0.21 mm on the object at 30 cm, 0.42 mm at 60 cm. So:

| Texture across a 534 mm panel | mm per px | Enough for |
|---|---|---|
| 2048 | 0.26 | 60 cm and beyond |
| 4096 | 0.13 | as close as the headset can focus |

Load the small one at start and the large one when the viewer comes within reach. Use KTX2 UASTC with
Zstandard: ETC1S bands soft gradients like sfumato. Mind host limits per file (Cloudflare: 25 MiB); raise
UASTC's RDO level or tile the texture.

## How it is shown

How the owner displays the object is part of what people recognise: the wall colour, the case, the glass,
the light, the barriers. Museums' press releases and the casework makers' project pages give these with
numbers (the Mona Lisa's case: 2.2 x 4.6 x 0.6 m, anti-reflective laminated glass, lights in its front
shelf; the wall "a very dense shade of blue"). Build the display from those, without the museum's name or
logo in the scene.
