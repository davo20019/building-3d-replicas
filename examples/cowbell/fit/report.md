# Silhouette fit

| Photo | IoU before | Outline before (mm) | IoU after | Outline after (mm) | Landmark (mm) | Dark IoU | Camera pitch/yaw/roll | Distance (mm) | Camera height (mm) | Ride offset (mm) |
|---|---|---|---|---|---|---|---|---|---|---|
| museum | 0.9473 | 1.01 | 0.9650 | 0.66 | 0.00 | 0.748 -> 0.753 | [3.5, -5.6, 0.7] | 579 | 163 | 0 |
| scan_front | 0.9387 | 1.17 | 0.9452 | 1.03 | 0.26 | 0.766 -> 0.742 | [22.9, -7.6, 0.2] | 716 | 406 | 0 |
| scan_side | 0.9357 | 0.87 | 0.9685 | 0.41 | 0.00 | 0.893 -> 0.905 | [7.1, -90.9, 0.1] | 714 | 216 | 0 |
| scan_quarter | 0.9384 | 1.15 | 0.9390 | 1.13 | 0.00 | 0.864 -> 0.875 | [9.7, -55.5, 0.1] | 628 | 234 | 0 |
| scan_low | 0.9594 | 0.73 | 0.9634 | 0.66 | 0.00 | 0.897 -> 0.873 | [-15.0, -62.3, 2.7] | 815 | -83 | 0 |

Fitted: {"mouth_d": 56.66, "crown_w": 69.28, "crown_d": 33.86, "body_h": 107.0, "corner_r": 3.56, "shoulder_r": 11.39, "handle_d": 18.33, "paint_y": 149.1, "loop_out": 24.9, "loop_top": 134.97, "loop_rise": 0.5, "loop_w": 18.34}
