"""Modern Python 3.12+ Rigaku d*TREK GIWAXS processing with pyFAI."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd


PLOT_FONT_SIZE = 20
plt.rcParams.update({
    "font.size": PLOT_FONT_SIZE,
    "axes.labelsize": PLOT_FONT_SIZE,
    "axes.titlesize": PLOT_FONT_SIZE,
    "xtick.labelsize": PLOT_FONT_SIZE,
    "ytick.labelsize": PLOT_FONT_SIZE,
})

CMAP = copy(plt.cm.RdYlBu_r)
CMAP.set_bad(CMAP(0))


@dataclass(frozen=True)
class RigakuGeometry:
    """Fixed detector and GI settings following the original d*TREK notebook."""

    pixel_size_m: float = 100e-6
    sample_orientation: int = 3
    polarization_factor: float = 0.0


def _header_numbers(header: dict, key: str, expected: int) -> list[float]:
    try:
        values = [float(value) for value in header[key].split()]
    except KeyError as error:
        raise ValueError(f"The d*TREK header does not contain '{key}'.") from error
    if len(values) < expected:
        raise ValueError(f"Expected {expected} values in '{key}', found {values}.")
    return values


def read_dtrek_image(path: str | Path) -> tuple[np.ndarray, dict]:
    """Read and 180-degree rotate a Rigaku d*TREK detector image."""
    try:
        import fabio
    except ImportError as error:
        raise ImportError("Install FabIO to open d*TREK .img files.") from error
    image = fabio.open(str(path))
    data = np.ascontiguousarray(np.rot90(image.data, 2), dtype=np.float32)
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D detector image, received shape {data.shape}.")
    return data, dict(image.header)


class RigakuProcessor:
    """Build a modern pyFAI GI integrator from a Rigaku d*TREK header."""

    def __init__(self, image: np.ndarray, header: dict, geometry: RigakuGeometry | None = None):
        try:
            import pyFAI
            from pyFAI.integrator.fiber import FiberIntegrator
        except ImportError as error:
            raise ImportError("Install pyFAI>=2024.5 before processing Rigaku images.") from error

        self.image = image
        self.header = header
        self.geometry = geometry or RigakuGeometry()
        omega, _, _ = _header_numbers(header, "CRYSTAL_GONIO_VALUES", 3)
        dimensions = _header_numbers(header, "PXD_DETECTOR_DIMENSIONS", 2)
        beam_x, beam_y = _header_numbers(header, "PXD_SPATIAL_BEAM_POSITION", 2)
        wavelengths = _header_numbers(header, "SOURCE_WAVELENGTH", 2)
        gonio_names = header.get("PXD_GONIO_NAMES", "").split()
        gonio_values = _header_numbers(header, "PXD_GONIO_VALUES", len(gonio_names))
        if "2Theta" not in gonio_names:
            raise ValueError("The d*TREK header has no 2Theta entry.")
        two_theta = gonio_values[gonio_names.index("2Theta")]
        distance = 0.065
        if "Distance" in gonio_names:
            raw_distance = gonio_values[gonio_names.index("Distance")]
            distance = raw_distance / 1000.0 if 1 < raw_distance < 2000 else raw_distance

        # Header dimensions follow the notebook's x, y ordering after rotation.
        shape_x, shape_y = (int(dimensions[0]), int(dimensions[1]))
        detector = pyFAI.detectors.Detector(
            self.geometry.pixel_size_m,
            self.geometry.pixel_size_m,
            max_shape=(shape_x, shape_y),
        )
        self.integrator = FiberIntegrator(
            dist=distance,
            poni1=(shape_y - beam_y) * self.geometry.pixel_size_m,
            poni2=(shape_x - beam_x) * self.geometry.pixel_size_m,
            rot2=np.deg2rad(two_theta),
            detector=detector,
            wavelength=wavelengths[1] * 1e-10,
        )
        self.metadata = {
            "incident_angle_degrees": omega,
            "two_theta_degrees": two_theta,
            "distance_m": distance,
            "beam_center_x_px": beam_x,
            "beam_center_y_px": beam_y,
            "wavelength_angstrom": wavelengths[1],
            "image_rotation_degrees": 180,
        }

    def _options(self) -> dict[str, object]:
        return {
            "incident_angle": self.metadata["incident_angle_degrees"],
            "sample_orientation": self.geometry.sample_orientation,
            "angle_unit": "deg",
            "correctSolidAngle": True,
            "polarization_factor": self.geometry.polarization_factor,
            "method": ("no", "histogram", "cython"),
        }

    def reshape(self, bins: int, qxy_range: tuple[float, float], qz_range: tuple[float, float]):
        """Return I(Qxy, Qz) in inverse Angstrom."""
        result = self.integrator.integrate2d_grazing_incidence(
            self.image,
            npt_ip=bins,
            unit_ip="qip_A^-1",
            ip_range=qxy_range,
            npt_oop=bins,
            unit_oop="qoop_A^-1",
            oop_range=qz_range,
            **self._options(),
        )
        return np.asarray(result.intensity), np.asarray(result.inplane), np.asarray(result.outofplane)

    def line_cut(self, q_range: tuple[float, float], chi_center: float, chi_width: float, bins: int):
        """Return I(Q) over the selected GI polar-angle sector."""
        chi_range = (chi_center - chi_width / 2, chi_center + chi_width / 2)
        result = self.integrator.integrate1d_polar(
            data=self.image,
            npt_ip=bins,
            ip_range=q_range,
            npt_oop=max(180, int(abs(chi_width) * 2)),
            oop_range=chi_range,
            radial_unit="A^-1",
            radial_integration=False,
            **self._options(),
        )
        return np.asarray(result.integrated), np.asarray(result.intensity)


def create_processor(path: str | Path) -> RigakuProcessor:
    image, header = read_dtrek_image(path)
    return RigakuProcessor(image, header)


def save_figure(figure, output: str | Path, dpi: int = 300) -> None:
    stem = Path(output).with_suffix("")
    for suffix in (".png", ".pdf", ".svg"):
        options = {"bbox_inches": "tight"}
        if suffix == ".png":
            options["dpi"] = dpi
        figure.savefig(stem.with_suffix(suffix), **options)


def plot_reshape(
    intensity: np.ndarray,
    qxy: np.ndarray,
    qz: np.ndarray,
    limits: tuple[float, float, float, float],
    scale: str,
    vmin: float | None,
    vmax: float | None,
):
    figure, axis = plt.subplots(figsize=(8, 5))
    options: dict[str, object] = {}
    if scale == "logarithmic":
        positive = intensity[np.isfinite(intensity) & (intensity > 0)]
        if positive.size == 0:
            raise ValueError("Logarithmic display requires at least one positive intensity value.")
        low = float(positive.min()) if vmin is None else vmin
        high = float(positive.max()) if vmax is None else vmax
        if low <= 0 or high <= low:
            raise ValueError("For logarithmic display, use 0 < vmin < vmax.")
        options["norm"] = LogNorm(vmin=low, vmax=high)
        intensity = np.ma.masked_less_equal(intensity, 0)
    else:
        options.update(vmin=vmin, vmax=vmax)
    image = axis.imshow(
        intensity,
        cmap=CMAP,
        origin="lower",
        extent=(qxy.min(), qxy.max(), qz.min(), qz.max()),
        aspect=1,
        **options,
    )
    axis.set(xlabel="$Q_{xy}$ [Angstrom$^{-1}$]", ylabel="$Q_z$ [Angstrom$^{-1}$]")
    axis.set_xlim(limits[0], limits[1])
    axis.set_ylim(limits[2], limits[3])
    figure.colorbar(image, ax=axis, label="Intensity")
    return figure, axis


def save_line_cut(q: np.ndarray, intensity: np.ndarray, output: str | Path) -> None:
    pd.DataFrame({"q_A-1": q, "intensity": intensity}).to_csv(output, index=False)
