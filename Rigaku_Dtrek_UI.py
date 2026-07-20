"""Simple desktop UI for Rigaku d*TREK GIWAXS reshape and line-cut analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

# Gooey is wxPython based; use the matching backend before importing pyplot.
matplotlib.use("WXAgg")
import matplotlib.pyplot as plt

from rigaku_dtrek_processing import (
    RigakuGeometry,
    create_processor,
    plot_reshape,
    save_figure,
    save_line_cut,
)

PROJECT_URL = "https://github.com/FengningY/Rigaku-Dtrek-GIWAXS-UI"

try:
    from gooey import Gooey, GooeyParser
except ImportError:
    Gooey = None
    GooeyParser = argparse.ArgumentParser


def chooser(widget: str) -> dict[str, str]:
    return {"widget": widget} if Gooey is not None else {}


def build_parser() -> argparse.ArgumentParser:
    parser = GooeyParser(description="Rigaku d*TREK GIWAXS reshape and line-cut analysis")
    parser.add_argument("action", choices=("2D reciprocal-space reshape", "1D sector line cut"))

    files = parser.add_argument_group("1. Input and output")
    files.add_argument("--image-file", required=True, **chooser("FileChooser"), help="Rigaku d*TREK .img image file.")
    files.add_argument("--output-dir", required=True, **chooser("DirChooser"), help="Directory for figures and CSV/NPZ data.")

    analysis = parser.add_argument_group("2. Analysis settings")
    analysis.add_argument("--reshape-bins", type=int, default=600, help="Number of q-space bins in each direction.")
    analysis.add_argument("--qxy-min", type=float, default=-2.5, help="Qxy lower limit (Å^-1).")
    analysis.add_argument("--qxy-max", type=float, default=2.5, help="Qxy upper limit (Å^-1).")
    analysis.add_argument("--qz-min", type=float, default=0.0, help="Qz lower limit (Å^-1).")
    analysis.add_argument("--qz-max", type=float, default=5.0, help="Qz upper limit (Å^-1).")
    analysis.add_argument("--display-vmin", type=float, default=None, help="Optional fixed colour-scale minimum.")
    analysis.add_argument("--display-vmax", type=float, default=None, help="Optional fixed colour-scale maximum.")
    analysis.add_argument(
        "--display-scale",
        choices=("linear", "logarithmic"),
        default="linear",
        help="Colour scale for the 2D reshape. Use logarithmic to reveal weak scattering features.",
    )
    analysis.add_argument("--q-min", type=float, default=0.01, help="Line-cut q lower limit (Å^-1).")
    analysis.add_argument("--q-max", type=float, default=2.5, help="Line-cut q upper limit (Å^-1).")
    analysis.add_argument("--chi-center", type=float, default=0.0, help="Line-cut chi sector centre (degrees).")
    analysis.add_argument("--chi-width", type=float, default=180.0, help="Line-cut chi sector width (degrees).")
    analysis.add_argument("--line-cut-bins", type=int, default=3000, help="Number of q bins for the line cut.")
    return parser


def processor_from_args(args: argparse.Namespace):
    return create_processor(args.image_file, RigakuGeometry())


def save_config(
    stem: Path,
    args: argparse.Namespace,
    processor,
    analysis_settings: dict[str, object],
) -> Path:
    """Write geometry and analysis settings next to each result."""
    config = {
        "input_image": str(Path(args.image_file).resolve()),
        "analysis": args.action,
        "geometry_from_dtrek_header": processor.metadata,
        "processing": {
            "pixel_size_m": processor.geometry.pixel_size_m,
            "sample_orientation": processor.geometry.sample_orientation,
            "polarization_factor": processor.geometry.polarization_factor,
            "image_rotation_degrees": 180,
        },
        "analysis_settings": analysis_settings,
    }
    config_path = stem.with_name(f"{stem.name}_config.json")
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def run_reshape(args: argparse.Namespace, output_dir: Path) -> None:
    processor = processor_from_args(args)
    print(f"d*TREK geometry read from header: {processor.metadata}")
    qxy_range = (args.qxy_min, args.qxy_max)
    qz_range = (args.qz_min, args.qz_max)
    intensity, qxy, qz = processor.reshape(args.reshape_bins, qxy_range, qz_range)
    stem = output_dir / f"{Path(args.image_file).stem}_qspace"
    import numpy as np
    np.savez_compressed(stem.with_suffix(".npz"), intensity=intensity, qxy=qxy, qz=qz)
    figure, _ = plot_reshape(
        intensity,
        qxy,
        qz,
        limits=(*qxy_range, *qz_range),
        vmin=args.display_vmin,
        vmax=args.display_vmax,
        scale=args.display_scale,
    )
    save_figure(figure, stem, dpi=300)
    config_path = save_config(
        stem,
        args,
        processor,
        {
            "reshape_bins": args.reshape_bins,
            "qxy_range_A-1": list(qxy_range),
            "qz_range_A-1": list(qz_range),
            "display_vmin": args.display_vmin,
            "display_vmax": args.display_vmax,
            "display_scale": args.display_scale,
        },
    )
    print(
        f"Saved q-space figure as PNG, PDF and SVG: {stem}\n"
        f"Saved numerical NPZ: {stem.with_suffix('.npz')}\n"
        f"Saved analysis config: {config_path}"
    )
    plt.show()


def run_line_cut(args: argparse.Namespace, output_dir: Path) -> None:
    processor = processor_from_args(args)
    print(f"d*TREK geometry read from header: {processor.metadata}")
    q, intensity = processor.line_cut(
        (args.q_min, args.q_max), args.chi_center, args.chi_width, args.line_cut_bins
    )
    stem = output_dir / f"{Path(args.image_file).stem}_line_cut"
    save_line_cut(q, intensity, stem.with_suffix(".csv"))
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.plot(q, intensity, linewidth=1)
    axis.set(xlabel="$Q$ [Å⁻¹]", ylabel="Intensity", title="Rigaku GIWAXS sector line cut")
    save_figure(figure, stem, dpi=300)
    config_path = save_config(
        stem,
        args,
        processor,
        {
            "q_range_A-1": [args.q_min, args.q_max],
            "chi_center_degrees": args.chi_center,
            "chi_width_degrees": args.chi_width,
            "line_cut_bins": args.line_cut_bins,
        },
    )
    print(
        f"Saved line-cut CSV: {stem.with_suffix('.csv')}\n"
        f"Saved figure as PNG, PDF and SVG: {stem}\n"
        f"Saved analysis config: {config_path}"
    )
    plt.show()


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.action == "2D reciprocal-space reshape":
        run_reshape(args, output_dir)
    else:
        run_line_cut(args, output_dir)


if __name__ == "__main__":
    if Gooey is None:
        main()
    else:
        @Gooey(
            program_name="Rigaku d*TREK GIWAXS",
            program_description=(
                "Simple reciprocal-space reshape and sector line-cut analysis. "
                f"Updates: {PROJECT_URL}"
            ),
            navigation="TABBED",
            default_size=(850, 680),
            required_cols=1,
            optional_cols=1,
        )
        def gui_main() -> None:
            main()

        gui_main()
