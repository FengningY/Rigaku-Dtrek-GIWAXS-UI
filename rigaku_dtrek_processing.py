"""Core processing functions for Rigaku d*TREK GIWAXS .img files."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PLOT_FONT_SIZE = 20
plt.rcParams.update({
    "font.size": PLOT_FONT_SIZE,
    "axes.labelsize": PLOT_FONT_SIZE,
    "axes.titlesize": PLOT_FONT_SIZE,
    "xtick.labelsize": PLOT_FONT_SIZE,
    "ytick.labelsize": PLOT_FONT_SIZE,
    "legend.fontsize": PLOT_FONT_SIZE,
})

CMAP = copy(plt.cm.RdYlBu_r)
CMAP.set_bad(CMAP(0))


@dataclass(frozen=True)
class RigakuGeometry:
    """Geometry values used to build a pyFAI integrator from a d*TREK header."""

    distance_m: float | None = None
    beam_center_x_px: float | None = None
    beam_center_y_px: float | None = None
    pixel_size_m: float = 100e-6
    sample_orientation: int = 3
    polarization_factor: float = 0.0


def _header_numbers(header: dict, key: str, expected: int) -> list[float]:
    try:
        values = [float(value) for value in header[key].split()]
    except KeyError as error:
        raise ValueError(f"The d*TREK header does not contain '{key}'.") from error
    if len(values) < expected:
        raise ValueError(f"Expected {expected} values in d*TREK header '{key}', found {values}.")
    return values


def read_dtrek_image(path: str | Path) -> tuple[np.ndarray, dict]:
    """Read one d*TREK image and rotate it 180 degrees as in the source notebook."""
    try:
        import fabio
    except ImportError as error:
        raise ImportError("Install fabio to read Rigaku d*TREK .img files.") from error
    dtrek = fabio.open(str(path))
    image = np.ascontiguousarray(np.rot90(dtrek.data, 2), dtype=np.float32)
    if image.ndim != 2:
        raise ValueError(f"Expected a 2D detector image, received shape {image.shape}.")
    return image, dict(dtrek.header)


def create_processor(path: str | Path, geometry: RigakuGeometry) -> "RigakuProcessor":
    """Create a geometry-aware processor from one d*TREK image/header."""
    image, header = read_dtrek_image(path)
    return RigakuProcessor(image, header, geometry)


class RigakuProcessor:
    """Rigaku d*TREK geometry construction and GIWAXS transformations."""

    def __init__(self, image: np.ndarray, header: dict, geometry: RigakuGeometry):
        try:
            import pyFAI
            import sys
            import types

            # pygix imports pyFAI.opencl at startup. Disable this optional path
            # because it aborts in the tested legacy Windows software stack.
            opencl_disabled = types.ModuleType("pyFAI.opencl")
            opencl_disabled.ocl = None
            sys.modules["pyFAI.opencl"] = opencl_disabled
            from pyFAI.azimuthalIntegrator import AzimuthalIntegrator
            import pygix
        except ImportError as error:
            raise ImportError("Install pyFAI and pygix before processing Rigaku images.") from error

        self.image = image
        self.header = header
        self.geometry = geometry
        self._install_bbox_compatibility()

        omega, _, _ = _header_numbers(header, "CRYSTAL_GONIO_VALUES", 3)
        dimensions = _header_numbers(header, "PXD_DETECTOR_DIMENSIONS", 2)
        beam_position = _header_numbers(header, "PXD_SPATIAL_BEAM_POSITION", 2)
        wavelength_values = _header_numbers(header, "SOURCE_WAVELENGTH", 2)
        gonio_names = header.get("PXD_GONIO_NAMES", "").split()
        gonio_values = _header_numbers(header, "PXD_GONIO_VALUES", len(gonio_names))
        if "2Theta" not in gonio_names:
            raise ValueError("The d*TREK header does not contain a 2Theta value in PXD_GONIO_NAMES.")
        two_theta = gonio_values[gonio_names.index("2Theta")]
        distance = geometry.distance_m
        if distance is None and "Distance" in gonio_names:
            raw_distance = gonio_values[gonio_names.index("Distance")]
            distance = raw_distance / 1000.0 if 1 < raw_distance < 2000 else raw_distance
        if distance is None:
            distance = 0.065

        # The original notebook uses this header ordering after a 180 degree rotation.
        shape_x, shape_y = (int(dimensions[0]), int(dimensions[1]))
        beam_x = geometry.beam_center_x_px if geometry.beam_center_x_px is not None else beam_position[0]
        beam_y = geometry.beam_center_y_px if geometry.beam_center_y_px is not None else beam_position[1]
        detector = pyFAI.detectors.Detector(
            geometry.pixel_size_m,
            geometry.pixel_size_m,
            max_shape=(shape_x, shape_y),
        )
        self.ai = AzimuthalIntegrator(
            poni1=(shape_y - beam_y) * geometry.pixel_size_m,
            poni2=(shape_x - beam_x) * geometry.pixel_size_m,
            detector=detector,
            rot2=np.deg2rad(two_theta),
            wavelength=wavelength_values[1] * 1e-10,
            dist=distance,
        )
        self.pg = pygix.Transform()
        self.pg.load(self.ai)
        self.pg.incident_angle = omega
        self.pg.sample_orientation = geometry.sample_orientation
        self.metadata = {
            "incident_angle_degrees": omega,
            "two_theta_degrees": two_theta,
            "distance_m": distance,
            "beam_center_x_px": beam_x,
            "beam_center_y_px": beam_y,
            "wavelength_angstrom": wavelength_values[1],
        }

    @staticmethod
    def _install_bbox_compatibility() -> None:
        """Translate pygix snake_case BBox arguments for pyFAI 0.20."""
        from pyFAI.ext import splitBBox

        for name in ("histoBBox1d", "histoBBox2d"):
            original = getattr(splitBBox, name)
            if getattr(original, "_rigaku_dtrek_compat", False):
                continue

            def compatible(*args, _original=original, **kwargs):
                if "pos0_range" in kwargs:
                    kwargs["pos0Range"] = kwargs.pop("pos0_range")
                if "pos1_range" in kwargs:
                    kwargs["pos1Range"] = kwargs.pop("pos1_range")
                return _original(*args, **kwargs)

            compatible._rigaku_dtrek_compat = True
            setattr(splitBBox, name, compatible)

    def reshape(
        self,
        bins: int,
        qxy_range: tuple[float, float],
        qz_range: tuple[float, float],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Transform the current raw d*TREK frame to I(Qxy, Qz)."""
        return self.pg.transform_reciprocal(
            self.image,
            npt=(bins, bins),
            ip_range=qxy_range,
            op_range=qz_range,
            polarization_factor=self.geometry.polarization_factor,
            method="nearest",
            unit="A",
        )

    def line_cut(
        self,
        q_range: tuple[float, float],
        chi_center: float,
        chi_width: float,
        bins: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return q and intensity for a selected GIWAXS chi sector."""
        intensity, q = self.pg.profile_sector(
            self.image,
            bins,
            correctSolidAngle=True,
            method="bbox",
            radial_range=q_range,
            chi_pos=chi_center,
            chi_width=chi_width,
            unit="q_A^-1",
        )
        return np.asarray(q), np.asarray(intensity)


def save_figure(fig, output: str | Path, dpi: int = 300) -> list[Path]:
    """Save a figure as PNG, PDF, and SVG using one common file stem."""
    output = Path(output)
    stem = output.with_suffix("") if output.suffix else output
    paths = []
    for extension in (".png", ".pdf", ".svg"):
        path = stem.with_suffix(extension)
        kwargs = {"bbox_inches": "tight"}
        if extension == ".png":
            kwargs["dpi"] = dpi
        fig.savefig(path, **kwargs)
        paths.append(path)
    return paths


def plot_reshape(
    intensity: np.ndarray,
    qxy: np.ndarray,
    qz: np.ndarray,
    limits: tuple[float, float, float, float],
    vmin: float | None = None,
    vmax: float | None = None,
):
    """Create a standard reciprocal-space figure."""
    fig, ax = plt.subplots(figsize=(8, 5))
    image = ax.imshow(
        intensity,
        cmap=CMAP,
        extent=(qxy.min(), qxy.max(), qz.min(), qz.max()),
        vmin=vmin,
        vmax=vmax,
        aspect=1,
        origin="lower",
    )
    ax.set(xlabel="$Q_{xy}$ [Å⁻¹]", ylabel="$Q_z$ [Å⁻¹]")
    ax.set_xlim(limits[0], limits[1])
    ax.set_ylim(limits[2], limits[3])
    fig.colorbar(image, ax=ax, label="Intensity")
    return fig, ax


def save_line_cut(q: np.ndarray, intensity: np.ndarray, output: str | Path) -> None:
    """Write one line cut as a portable CSV file."""
    pd.DataFrame({"q_A-1": q, "intensity": intensity}).to_csv(output, index=False)
