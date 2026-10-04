# Evidence

Where to find dimensions and views, and what each kind of source is good for. Read before collecting
references (workflow step 1).

## Sources and how to use them

- Manufacturer pages and manuals for dimensions; write each in `spec.md` with its source. Manuals carry the best numbers (overhangs, clearances, offsets). Some makers' sites refuse scripted requests; their regional mirrors often don't.
- Museums with open-access collections (Smithsonian Open Access, many others under CC0) publish photos, sizes and sometimes scans.
- Wikimedia Commons, for anything photographed in public: list a category with the API (`action=query&list=categorymembers&cmtitle=Category:<X>&cmtype=file`), fetch licence and author with `prop=imageinfo&iiprop=url|size|extmetadata`, and download at a standard thumbnail width (3840; other widths get HTTP 400). Record each file's licence in `refs/SOURCES.md`.
- Shops that sell it: each shoots different angles (Shopify stores list all images at `<product-url>.json`). These photos are for comparison only; don't publish them.
- Video: your own footage is best. Downloading from YouTube is against its terms of service unless the video's licence or its owner allows it; check before you do. Make contact sheets (`ffmpeg -vf "fps=48/<duration>,scale=320:-1,tile=8x6"`), then pull full-resolution frames at the useful timestamps. Check it is the same product: lookalikes, prototypes and modified ones are common.
- Label views by geometry, not by impression: a side view with the front pointing to the left of the frame shows the object's left side.
- Write down which surfaces no photo shows. They stay marked guesses.

## Lessons

- **Trust the numbers over your eye.** A front photo read as shot from above was shot from below: the dial's position inside the outline proved it.
- **A photo of the real object from where the viewer will be beats renders read for ratios.** The maker's renders showed a console in a white trim and a lid at its open thickness; one photo from the driver's seat of a real truck showed a satin top and a lid a quarter as tall.
- **Each photo shows a state.** Mirrors folded or not, suspension kneeling, a lid open, a door ajar: model the state the object is used in, and write down which state each photo shows. What changes between photos is a per-photo pose value in the fit, not a shape parameter.
- **Service and body repair manuals have orthographic, dimensioned drawings.** Check their scale with several labelled dimensions before using them (four labelled diagonals agreeing to 2 mm); a figure from a reader's protractor is not a source.
- **When published numbers disagree with each other** (track plus tyre width came out wider than the published width), write the conflict down and leave it; don't force one to fit.
- **Vet a third-party model's provenance before using it as a library part.** Free "CC-BY" uploads are often re-uploads or game rips (identical triangle counts across uploaders, game tags), and paid stock licences usually forbid shipping an extractable GLB.
- **Museum open-access sites often block scripted page requests**; their APIs, bulk metadata and image delivery services usually don't.
- **Tools that did not help:** monocular depth (Depth Anything V2 gave a smooth blob, relative only); image-to-3D (TRELLIS returned a flat disc after its background removal deleted a silver part). Don't use them for exact replicas.
- **Trademarks:** leave out logos and wordmarks. A distinctive product shape can itself be protected: don't publish replicas of trademarked designs without checking.
