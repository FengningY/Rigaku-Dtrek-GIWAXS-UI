# Rigaku d*TREK GIWAXS UI

A small desktop application for processing individual Rigaku d*TREK `.img` GIWAXS frames. It is derived from the geometry and image-orientation workflow in `Rigaku Dtrek image conversion - Fengning_20241108.ipynb`.

Project updates: <https://github.com/FengningY/Rigaku-Dtrek-GIWAXS-UI>

The application deliberately has two operations only:

- **2D reciprocal-space reshape**: produces `I(Qxy, Qz)`.
- **1D sector line cut**: produces `I(Q)` for a selected chi sector.

There is no waterfall or time-series workflow in this application.

## Installation

Use a clean Python 3.9 Conda environment:

```powershell
conda create -n rigaku-giwaxs python=3.9.12 -y
conda activate rigaku-giwaxs
python -m pip install -r requirements.txt
python Rigaku_Dtrek_UI.py
```

## Geometry Defaults

The UI reads omega, wavelength, 2Theta, detector dimensions, and beam-y from the selected d*TREK header. The source notebook established the following defaults for the in-house configuration:

| Setting | Default | Notes |
| --- | ---: | --- |
| Pixel size | 100 µm | Fixed in the processing code. |
| Detector distance | 0.065 m | Can be overridden in the UI. |
| Beam centre x | 395.586 pixels | Can be overridden in the UI. |
| Beam centre y | d*TREK header | Can be overridden in the UI if required. |
| Image orientation | 180 degree rotation | Applied automatically, matching the notebook. |
| Sample orientation | 3 | Fixed to the original GIWAXS mapping. |

Validate the geometry on a known reference image before analysing an entire experiment. In particular, do not assume that the distance and beam-x defaults apply after detector repositioning.

## Using the UI

1. Select a d*TREK `.img` file and an output directory.
2. Check or override detector distance and beam centre x if the experiment geometry differs from the defaults.
3. Choose `2D reciprocal-space reshape` to inspect `Qxy/Qz` geometry or `1D sector line cut` to integrate a selected chi sector.
4. For a first-quadrant region (`Qxy > 0`, `Qz > 0`), a common initial line-cut sector is `chi centre = 45` and `chi width = 90`, covering 0–90 degrees. Confirm this on the reshape map before interpreting it.

Each figure is exported as PNG, PDF, and SVG. Reshape data are also saved as NPZ, while line cuts are saved as CSV.

## Data Policy

Raw `.img` files and generated results are excluded by `.gitignore`. Do not commit experimental data or in-house geometry information to a public repository without appropriate permission.
