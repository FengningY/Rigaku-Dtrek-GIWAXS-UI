# Rigaku d*TREK GIWAXS UI

A desktop application for basic analysis of individual Rigaku d*TREK `.img` GIWAXS frames. It provides two focused operations:

- **2D reciprocal-space reshape**: creates an `I(Qxy, Qz)` map.
- **1D sector line cut**: creates an `I(Q)` profile from a selected azimuthal sector.

The geometry and image-orientation workflow follows `Rigaku Dtrek image conversion - Fengning_20241108.ipynb`. This application is intentionally limited to individual-frame analysis. It does not include time-series or waterfall processing.

Project updates and source code: <https://github.com/FengningY/Rigaku-Dtrek-GIWAXS-UI>

## Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Starting the application](#starting-the-application)
4. [Input image and automatic geometry](#input-image-and-automatic-geometry)
5. [2D reciprocal-space reshape](#2d-reciprocal-space-reshape)
6. [1D sector line cut](#1d-sector-line-cut)
7. [Output files and configuration record](#output-files-and-configuration-record)
8. [Recommended workflow](#recommended-workflow)
9. [Troubleshooting](#troubleshooting)
10. [Desktop one-click launcher](#desktop-one-click-launcher)

## Requirements

The tested environment is Windows with CPython 3.9. The exact package versions are pinned in `requirements.txt` because legacy `pyFAI` and `pygix` releases must be compatible with each other.

- Windows 10 or Windows 11
- Miniconda or Anaconda
- Python 3.9
- Rigaku d*TREK detector files with the `.img` extension

Do not upgrade NumPy, pyFAI, or pygix independently unless the full software stack is tested again.

## Installation

Open **Anaconda Prompt** or PowerShell and go to the folder containing this repository. Quote any Windows path that contains spaces:

```powershell
cd "C:\path\to\Rigaku_Dtrek_UI"
```

Create and activate a dedicated environment:

```powershell
conda create -n rigaku-giwaxs python=3.9.12 -y
conda activate rigaku-giwaxs
python -m pip install -r requirements.txt
```

Check that the essential packages can be imported:

```powershell
python -c "import numpy, fabio, pyFAI, pygix; print('Environment is ready.')"
```

## Starting the application

Activate the environment every time before launching the program:

```powershell
conda activate rigaku-giwaxs
cd "C:\path\to\Rigaku_Dtrek_UI"
python Rigaku_Dtrek_UI.py
```

The Gooey desktop window will open. Select an analysis operation from the first control, then complete the input and analysis settings. The console output reports the geometry read from the selected image header and lists every saved output path.

## Desktop one-click launcher

After the one-time installation, use `Launch_Rigaku_Dtrek_GIWAXS_UI.bat` to open the UI without manually activating Conda. The launcher searches common Miniconda, Anaconda, and Miniforge installation folders, then starts the `rigaku-giwaxs` environment created in the installation section.

To create a desktop icon in Windows:

1. Open this project folder in File Explorer.
2. Right-click `Launch_Rigaku_Dtrek_GIWAXS_UI.bat`.
3. Select **Show more options** if necessary, then select **Send to > Desktop (create shortcut)**.
4. Double-click the desktop shortcut to open the UI.

Optionally, right-click the shortcut, select **Properties**, and change **Run** to **Minimized**. If the project folder is moved or renamed, create a new shortcut because the old one points to its previous location.

## Input image and automatic geometry

Select one Rigaku d*TREK `.img` file and an output directory. The application automatically rotates the raw image by 180 degrees before transforming it, matching the source notebook.

No manual beam centre, incident angle, wavelength, detector distance, or 2Theta input is required. The following quantities are read from the d*TREK header:

| Physical quantity | Header field | Used by the application |
| --- | --- | --- |
| Incident angle (omega) | `CRYSTAL_GONIO_VALUES` | Yes |
| Beam centre x/y | `PXD_SPATIAL_BEAM_POSITION` | Yes |
| Detector dimensions | `PXD_DETECTOR_DIMENSIONS` | Yes |
| 2Theta | `PXD_GONIO_NAMES` and `PXD_GONIO_VALUES` | Yes |
| Detector distance | `PXD_GONIO_NAMES` and `PXD_GONIO_VALUES` | Yes |
| Wavelength | `SOURCE_WAVELENGTH` | Yes |

The detector pixel size is fixed at `100 um`, sample orientation is fixed at `3`, and the polarization factor is `0.0`, following the original notebook. If the header does not contain a usable detector distance, the program uses a `0.065 m` fallback. Always inspect the generated config file and validate a known reference image before analysing a full experiment, especially after moving the detector.

## 2D reciprocal-space reshape

Choose **2D reciprocal-space reshape** to create a reciprocal-space map. The result is displayed with `Qxy` on the horizontal axis and `Qz` on the vertical axis.

### Parameters

| UI field | Meaning | Initial value |
| --- | --- | --- |
| Reshape bins | Number of output pixels along both q axes. Larger values produce a finer map but take longer. | 600 |
| Qxy min / max | Horizontal reciprocal-space limits in `A^-1`. | -2.5 / 2.5 |
| Qz min / max | Vertical reciprocal-space limits in `A^-1`. | 0.0 / 5.0 |
| Display vmin / vmax | Optional fixed lower and upper colour limits. Leave blank for automatic limits. | Blank |
| Display scale | Colour scale for the displayed map: `linear` or `logarithmic`. | linear |

### Display scale

Use **linear** when comparing absolute intensity contrast between maps. Use **logarithmic** to reveal weak scattering features near strong peaks. Logarithmic display masks zero and negative values because their logarithm is undefined. It changes only the figure display; the NPZ file always contains the original calculated intensity values.

For reproducible comparisons between several maps, enter the same valid `Display vmin` and `Display vmax` values for every frame. In logarithmic mode, `Display vmin` must be greater than zero.

## 1D sector line cut

Choose **1D sector line cut** to integrate intensity over an azimuthal sector and obtain an `I(Q)` profile. First make a 2D reshape to confirm which angular sector contains the feature of interest.

### Parameters

| UI field | Meaning | Initial value |
| --- | --- | --- |
| Q min / max | Radial integration range in `A^-1`. | 0.01 / 2.5 |
| Chi centre | Centre of the azimuthal integration sector, in degrees. | 0 |
| Chi width | Full angular width of the sector, in degrees. | 180 |
| Line-cut bins | Number of q points in the exported profile. | 3000 |

For a feature confined to the first quadrant of a reshape map (`Qxy > 0`, `Qz > 0`), a useful starting sector is `Chi centre = 45` and `Chi width = 90`. This covers approximately 0 to 90 degrees. Verify the convention against the reshape map before assigning a physical orientation.

## Output files and configuration record

All results are written to the selected output directory, using the input image name as the prefix.

For a file named `PbIBr_2angle.img`, the 2D operation produces:

```text
PbIBr_2angle_qspace.png
PbIBr_2angle_qspace.pdf
PbIBr_2angle_qspace.svg
PbIBr_2angle_qspace.npz
PbIBr_2angle_qspace_config.json
```

The NPZ file contains arrays named `intensity`, `qxy`, and `qz`. The 1D operation produces PNG, PDF, SVG, CSV, and a matching configuration file with the `_line_cut` prefix. The CSV columns are `q_A-1` and `intensity`.

Each `_config.json` file is a permanent record of the result settings. It contains:

- Absolute input-image path.
- Selected analysis operation.
- Header-derived incident angle, 2Theta, distance, beam centre, and wavelength.
- Pixel size, sample orientation, polarization factor, and image rotation.
- Reshape q limits, display scale, colour limits, and bin count; or line-cut q range, chi sector, and bin count.

Keep the config JSON together with any figure used in a report or publication so the conversion can be reproduced.

## Recommended workflow

1. Create a new output folder for one sample or measurement condition.
2. Run a 2D reshape using the default q ranges and `linear` display.
3. Confirm that the q-space orientation and peak positions are physically reasonable.
4. Switch to `logarithmic` display if weak features are hidden by strong peaks.
5. Adjust the q limits and bin count only after confirming the geometry.
6. Identify the angular sector of interest from the reshape map.
7. Run a 1D sector line cut using the desired q range, chi centre, and chi width.
8. Archive the PNG/PDF/SVG figure, numerical NPZ or CSV data, and matching config JSON together.

## Troubleshooting

### The command cannot change to a directory with spaces

Quote the full path:

```powershell
cd "C:\Users\name\OneDrive\Documents\Daily plan"
```

### The GUI does not open or a package import fails

Confirm that the correct Conda environment is active and reinstall the pinned packages:

```powershell
conda activate rigaku-giwaxs
python -m pip install --force-reinstall -r requirements.txt
```

### NumPy or Matplotlib reports a binary compatibility error

This usually indicates that NumPy was upgraded beyond the pinned legacy stack. Recreate the environment with Python 3.9 and install `requirements.txt` again. Do not mix packages from a different Conda environment.

### The program reports that a header field is missing

The selected file may not be a standard d*TREK `.img` file, or the acquisition header may be incomplete. Check the file and its acquisition settings. The program requires the header fields listed in the automatic-geometry table.

### Logarithmic display fails

The transformed map contains no positive finite intensity, or the selected `Display vmin` is zero or negative. Use linear display first, or leave both display-limit fields blank so valid limits are chosen automatically.

### The q-space image has an unexpected orientation or peak position

Do not interpret the result until the header geometry has been checked. Inspect the matching `_config.json`, verify the detector distance, beam centre, incident angle, and wavelength against the experiment log, then validate using a known reference sample.

## Data Policy

Raw `.img` files and generated results are excluded by `.gitignore`. Do not commit experimental data or in-house geometry information to a public repository without appropriate permission.
