# cowbell, round-1

## Sizes (mm)

| Object | Expected | Measured | OK |
|---|---|---|---|
| _all | [88.9, 266.7, None] | [88.9, 266.68, 56.66] | yes |

## Budget

| What | Value | Limit | OK |
|---|---|---|---|
| triangles | 1772 | 10000 | yes |
| GLB KB | 18 | 500 | yes |
| largest texture px | 0 | 1024 | yes |

## Fit per photo

| Photo | File | IoU | Outline error (mm) | Landmark error (mm) |
|---|---|---|---|---|
| museum | refs/nmah-2018_0174_01.jpg | 0.965 | 0.659 | 0.0 |
| scan_front | refs/scan/scan_front.png | 0.9452 | 1.027 | 0.256 |
| scan_low | refs/scan/scan_low.png | 0.9634 | 0.662 | 0.0 |
| scan_quarter | refs/scan/scan_quarter.png | 0.939 | 1.128 | 0.0 |
| scan_side | refs/scan/scan_side.png | 0.9685 | 0.409 | 0.0 |

Automatic checks: PASS

## Differences from the reference

- Shapes match in every pair; the remaining differences are in REPORT.md section 5 (crown weld, side seams, mouth flare, hand-bent loops, colour by eye).
- The front and three-quarter cameras look down 8 to 16 degrees more steeply than the true ones (REPORT.md section 4).
