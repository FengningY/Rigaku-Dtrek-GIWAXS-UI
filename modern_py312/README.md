# Rigaku d*TREK GIWAXS UI: Modern Python 3.12+

This folder contains the modern edition of the Rigaku d*TREK GIWAXS desktop UI. The legacy Python 3.9/Gooey/pygix application in the parent folder is retained for reproducibility.

## Modern Stack

- Windows 64-bit CPython 3.12 or later.
- Built-in Tkinter desktop UI; no Gooey, wxPython, Qt, or Conda is required.
- Current pyFAI `FiberIntegrator` replaces pygix for grazing-incidence conversion.
- Current FabIO reads the Rigaku `.img` image and d*TREK header.
- The header automatically supplies incident angle, beam centre, 2Theta, detector distance, wavelength, and detector dimensions.

The tested CPython 3.12.13 package versions are recorded in `requirements_py312.txt`: NumPy 2.5.1, SciPy 1.18.0, pandas 3.0.3, Matplotlib 3.11.1, h5py 3.16.0, FabIO 2024.9.0, and pyFAI 2026.5.0.

## Installation

1. Install 64-bit Python 3.12 or later from <https://www.python.org/downloads/windows/> and select **Add Python to PATH**.
2. Open PowerShell in this `modern_py312` folder.
3. Create a local environment and install the tested packages:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements_py312.txt
```

4. Verify the stack:

```powershell
.\.venv\Scripts\python.exe -c "import pyFAI, fabio, numpy; print(pyFAI.version)"
```

5. Run the UI:

```powershell
.\.venv\Scripts\python.exe Rigaku_modern_UI.py
```

After installation, double-click `Launch_Rigaku_Modern.bat`. Create a desktop shortcut to that launcher for one-click use.

## Analysis Workflow

1. Select one `.img` file and an output folder.
2. Choose 2D reshape or 1D sector line cut.
3. For reshape, choose `linear` or `logarithmic` colour display and specify q limits.
4. Run the analysis. The output console lists all geometry values read from the d*TREK header.

Each result creates PNG, PDF, SVG, numerical NPZ or CSV data, and a matching JSON configuration file. Validate the first modern pyFAI result against a known reference image before using it for quantitative comparison with the legacy pygix workflow.
