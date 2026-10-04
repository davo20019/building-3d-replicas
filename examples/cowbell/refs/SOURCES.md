# Sources

Everything here is from the Smithsonian's Open Access programme and released under
[CC0](https://creativecommons.org/publicdomain/zero/1.0/): no permission, fee or attribution needed.
Credited anyway, as good practice. `fetch_refs.sh` downloads them; they are not stored in git.

| File | What | Source | Licence |
|---|---|---|---|
| nmah-2018_0174_01.jpg | Museum photo, front, from above on white (3001 x 4000) | National Museum of American History, image NMAH-JN2020-00328, object 2018.0174.01, gift of Milton Torres | CC0 |
| scan/nmah-2018_0174_01-cowbell-150k.glb | 3D scan, 150k triangles, metres, glTF y-up | Smithsonian 3D Digitization, 3d.si.edu, package 80c485f9-c7db-4d46-aa1c-a57565cd7baf | CC0 |
| scan/scan_*.png | The scan rendered through the known cameras in scan/views.json (scan_views.py) | made here from the scan | CC0 |

Record: https://n2t.net/ark:/65665/ng49ca746b4-520f-704b-e053-15f76fa0b4fa

The scan is the answer key. The model is built from the photo, the published size and the scan's renders
as if they were photos; the scan's mesh itself is used only by `check/scan.json` to grade the result.
