"""Review round for a model folder: renders, measures, compares with the reference photos.
  .venv/bin/python scripts/review.py <model>

Reads <model>/review.json (glb, ref photo with its centre in px and px per mm, expected sizes, budget) and
writes <model>/review/round-N/: sheet.png and report.md (sizes against expectations, budget, the fit per
photo). Every photo fitted by fit_silhouette.py (fit/<photo>/camera.json, or the older single
fit/camera.json) gets a pair on the sheet: the photo next to the model rendered through its solved camera.
Look at sheet.png, write what differs under "Differences" in report.md, fix, run again.

expectMm: {object name: [x, y, z] mm}; "_all" is the whole model's bounding box. Sizes are compared sorted
unless "expectAxes": true, which compares x, y, z in order (needed when two sizes are close).
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

model = Path(sys.argv[1]).resolve()
cfg = json.loads((model / 'review.json').read_text())
rounds = sorted((model / 'review').glob('round-*'), key=lambda p: int(p.name.split('-')[1]))
out = model / 'review' / f'round-{int(rounds[-1].name.split("-")[1]) + 1 if rounds else 1}'
out.mkdir(parents=True)
glb = model / cfg['glb']

cams = sorted((model / 'fit').glob('*/camera.json')) or [c for c in [model / 'fit' / 'camera.json'] if c.exists()]
r = subprocess.run(['blender', '-b', '--factory-startup', '--python', str(Path(__file__).with_name('render_views.py')),
                    '--', str(glb), str(out), str(model / 'review.json')] + [str(c) for c in cams], capture_output=True, text=True)
if r.returncode:
    sys.exit(r.stdout[-3000:] + r.stderr[-3000:])

S = 800
font = ImageFont.load_default(size=22)
tiles = []
if 'ref' in cfg:                                                # reference cropped to the same physical frame as the front render
    ref = Image.open(model / cfg['ref']).convert('RGB')
    cx, cy = cfg['refCentrePx']
    half = cfg['frontFrameMm'] * cfg['refPxPerMm'] / 2
    tiles.append((ref.crop((round(cx - half), round(cy - half), round(cx + half), round(cy + half))).resize((S, S)), 'reference'))
fit_rows = []
for cj in cams:
    # Like for like: the photo and the model through the photo's solved camera, cropped to the part.
    c = json.loads(cj.read_text())
    name = c.get('name', 'main')
    photo = Image.open(model / c['photo']).convert('RGB')
    render = Image.open(out / f'photo_{name}.png').convert('RGB').resize(photo.size)
    mask = Image.open(cj.parent / 'target.png').resize(photo.size)
    x0, y0, x1, y1 = mask.getbbox()
    m = round(0.06 * max(x1 - x0, y1 - y0)); w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    box = (x0 - m, y0 - m, x1 + m, y1 + m)
    k = S / max(w, h)
    size = (round(w * k), round(h * k))
    tiles.append((photo.crop(box).resize(size), f'{name}: photo'))
    tiles.append((render.crop(box).resize(size), f'{name}: model through its camera (IoU {c["iou"]}, outline {c["outlineErrorMm"]} mm)'))
    fit_rows.append(f'| {name} | {c["photo"]} | {c["iou"]} | {c["outlineErrorMm"]} | {c.get("landmarkErrorMm", "")} |')
for v, label in (('front', 'render: front'), ('three_quarter', 'render: three quarter'), ('side', 'render: side')):
    tiles.append((Image.open(out / f'{v}.png').convert('RGB').resize((S, S)), label))

cols = 2
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * S, rows * (S + 30)), 'white')
d = ImageDraw.Draw(sheet)
for i, (im, label) in enumerate(tiles):
    x, y = (i % cols) * S, (i // cols) * (S + 30)
    sheet.paste(im, (x, y + 30))
    d.text((x + 8, y + 4), label, fill='black', font=font)
sheet.save(out / 'sheet.png')

m = json.loads((out / 'measure.json').read_text())
lines = [f'# {model.name}, {out.name}', '', '## Sizes (mm)', '', '| Object | Expected | Measured | OK |', '|---|---|---|---|']
ok_all = True
tol = cfg['toleranceMm']
for name, exp in cfg['expectMm'].items():
    got = m['sizesMm'].get(name)
    if got is None:
        ok = False
    elif cfg.get('expectAxes'):
        ok = all(e is None or abs(g - e) <= tol for g, e in zip(got, exp))
    else:
        ok = all(abs(sorted(got)[i] - sorted(exp)[i]) <= tol for i in range(3))
    ok_all &= ok
    lines.append(f'| {name} | {exp} | {got} | {"yes" if ok else "NO"} |')
b = cfg['budget']
kb = glb.stat().st_size / 1024
tex = max((max(Image.open(p).size) for p in (model / 'parts').glob('*.png')), default=0)
checks = [('triangles', m['triangles'], b['triangles']), ('GLB KB', round(kb), b['glbKB']), ('largest texture px', tex, b['texturePx'])]
lines += ['', '## Budget', '', '| What | Value | Limit | OK |', '|---|---|---|---|']
for what, v, lim in checks:
    ok_all &= v <= lim
    lines.append(f'| {what} | {v} | {lim} | {"yes" if v <= lim else "NO"} |')
if fit_rows:
    lines += ['', '## Fit per photo', '', '| Photo | File | IoU | Outline error (mm) | Landmark error (mm) |', '|---|---|---|---|---|'] + fit_rows
lines += ['', f'Automatic checks: {"PASS" if ok_all else "FAIL"}', '', '## Differences from the reference', '', '- (fill in after looking at sheet.png)', '']
(out / 'report.md').write_text('\n'.join(lines))
print((out / 'report.md').read_text())
print('sheet:', out / 'sheet.png')
