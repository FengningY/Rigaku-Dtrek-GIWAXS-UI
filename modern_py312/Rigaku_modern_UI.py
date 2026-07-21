"""Tkinter desktop UI for modern Python 3.12+ Rigaku d*TREK GIWAXS analysis."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import numpy as np

from rigaku_modern_processing import create_processor, plot_reshape, save_figure, save_line_cut


PROJECT_URL = "https://github.com/FengningY/Rigaku-Dtrek-GIWAXS-UI"


class RigakuModernApp(ttk.Frame):
    def __init__(self, root: tk.Tk):
        super().__init__(root, padding=12)
        self.root = root
        self.grid(sticky="nsew")
        root.title("Rigaku d*TREK GIWAXS | Modern Python 3.12+")
        root.minsize(790, 560)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.vars = self._variables()
        self._build()

    def _variables(self):
        return {
            "action": tk.StringVar(value="2D reciprocal-space reshape"),
            "image_file": tk.StringVar(),
            "output_dir": tk.StringVar(),
            "reshape_bins": tk.StringVar(value="600"),
            "qxy_min": tk.StringVar(value="-2.5"),
            "qxy_max": tk.StringVar(value="2.5"),
            "qz_min": tk.StringVar(value="0.0"),
            "qz_max": tk.StringVar(value="5.0"),
            "display_scale": tk.StringVar(value="linear"),
            "display_vmin": tk.StringVar(),
            "display_vmax": tk.StringVar(),
            "q_min": tk.StringVar(value="0.01"),
            "q_max": tk.StringVar(value="2.5"),
            "chi_center": tk.StringVar(value="0.0"),
            "chi_width": tk.StringVar(value="180.0"),
            "line_cut_bins": tk.StringVar(value="3000"),
            "show_plots": tk.BooleanVar(value=True),
        }

    def _build(self):
        ttk.Label(self, text=f"GitHub updates: {PROJECT_URL}").grid(row=0, column=0, sticky="w", pady=(0, 8))
        tabs = ttk.Notebook(self)
        tabs.grid(row=1, column=0, sticky="nsew")
        input_tab = ttk.Frame(tabs, padding=12)
        analysis_tab = ttk.Frame(tabs, padding=12)
        tabs.add(input_tab, text="Input")
        tabs.add(analysis_tab, text="Analysis")
        self._combo(input_tab, 0, "Operation", "action", ("2D reciprocal-space reshape", "1D sector line cut"))
        self._path(input_tab, 1, "Rigaku d*TREK .img", "image_file", False)
        self._path(input_tab, 2, "Output folder", "output_dir", True)
        ttk.Label(input_tab, text="Beam centre, distance, wavelength, 2Theta, and incident angle are read automatically from the .img header.", wraplength=650).grid(row=3, column=1, sticky="w", pady=(12, 0))

        self._entry(analysis_tab, 0, "Reshape bins", "reshape_bins")
        self._entry(analysis_tab, 1, "Qxy min / max", "qxy_min", "qxy_max")
        self._entry(analysis_tab, 2, "Qz min / max", "qz_min", "qz_max")
        self._combo(analysis_tab, 3, "Display scale", "display_scale", ("linear", "logarithmic"))
        self._entry(analysis_tab, 4, "Display vmin / vmax (optional)", "display_vmin", "display_vmax")
        ttk.Separator(analysis_tab).grid(row=5, column=0, columnspan=3, sticky="ew", pady=8)
        self._entry(analysis_tab, 6, "Line-cut Q min / max", "q_min", "q_max")
        self._entry(analysis_tab, 7, "Chi centre / width", "chi_center", "chi_width")
        self._entry(analysis_tab, 8, "Line-cut bins", "line_cut_bins")

        footer = ttk.Frame(self)
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(footer, text="Run analysis", command=self.run).pack(side="left")
        ttk.Checkbutton(footer, text="Show plot window", variable=self.vars["show_plots"]).pack(side="left", padx=8)
        ttk.Button(footer, text="Open output folder", command=self.open_output).pack(side="right")
        self.log = tk.Text(self, height=8, state="disabled", wrap="word")
        self.log.grid(row=3, column=0, sticky="nsew", pady=(10, 0))

    def _entry(self, parent, row, label, key, key2=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(parent, textvariable=self.vars[key], width=28).grid(row=row, column=1, sticky="w", pady=5)
        if key2:
            ttk.Entry(parent, textvariable=self.vars[key2], width=28).grid(row=row, column=2, sticky="w", padx=(8, 0), pady=5)

    def _combo(self, parent, row, label, key, values):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(parent, textvariable=self.vars[key], values=values, state="readonly", width=48).grid(row=row, column=1, columnspan=2, sticky="w", pady=5)

    def _path(self, parent, row, label, key, folder):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Entry(parent, textvariable=self.vars[key], width=58).grid(row=row, column=1, sticky="ew", pady=5)
        ttk.Button(parent, text="Browse", command=lambda: self.choose(key, folder)).grid(row=row, column=2, padx=(8, 0), pady=5)

    def choose(self, key, folder):
        path = filedialog.askdirectory() if folder else filedialog.askopenfilename(filetypes=[("Rigaku image", "*.img"), ("All files", "*.*")])
        if path:
            self.vars[key].set(path)

    def message(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    @staticmethod
    def optional_float(value: str):
        return None if not value.strip() else float(value)

    def write_config(self, output: Path, processor, settings: dict):
        config = {
            "input_image": str(Path(self.vars["image_file"].get()).resolve()),
            "geometry_from_dtrek_header": processor.metadata,
            "processing": {"sample_orientation": 3, "polarization_factor": 0.0},
            "analysis_settings": settings,
            "project_url": PROJECT_URL,
        }
        path = output.with_name(f"{output.name}_config.json")
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path

    def run(self):
        try:
            image_path = Path(self.vars["image_file"].get())
            output_dir = Path(self.vars["output_dir"].get())
            if not image_path.is_file():
                raise ValueError("Choose an existing Rigaku .img file.")
            if not self.vars["output_dir"].get().strip():
                raise ValueError("Choose an output folder.")
            output_dir.mkdir(parents=True, exist_ok=True)
            processor = create_processor(image_path)
            self.message(f"d*TREK geometry: {processor.metadata}")
            if self.vars["action"].get() == "2D reciprocal-space reshape":
                self.run_reshape(processor, output_dir, image_path.stem)
            else:
                self.run_line_cut(processor, output_dir, image_path.stem)
        except Exception as error:
            self.message(f"ERROR: {error}")
            messagebox.showerror("Analysis failed", str(error))

    def run_reshape(self, processor, output_dir: Path, stem_name: str):
        qxy = (float(self.vars["qxy_min"].get()), float(self.vars["qxy_max"].get()))
        qz = (float(self.vars["qz_min"].get()), float(self.vars["qz_max"].get()))
        bins = int(self.vars["reshape_bins"].get())
        intensity, qxy_axis, qz_axis = processor.reshape(bins, qxy, qz)
        output = output_dir / f"{stem_name}_qspace"
        np.savez_compressed(output.with_suffix(".npz"), intensity=intensity, qxy=qxy_axis, qz=qz_axis)
        figure, _ = plot_reshape(intensity, qxy_axis, qz_axis, (*qxy, *qz), self.vars["display_scale"].get(), self.optional_float(self.vars["display_vmin"].get()), self.optional_float(self.vars["display_vmax"].get()))
        save_figure(figure, output)
        config = self.write_config(output, processor, {"reshape_bins": bins, "qxy_range_A-1": qxy, "qz_range_A-1": qz, "display_scale": self.vars["display_scale"].get()})
        self.message(f"Saved PNG/PDF/SVG/NPZ: {output}; config: {config}")
        self.show(figure)

    def run_line_cut(self, processor, output_dir: Path, stem_name: str):
        q_range = (float(self.vars["q_min"].get()), float(self.vars["q_max"].get()))
        center = float(self.vars["chi_center"].get())
        width = float(self.vars["chi_width"].get())
        bins = int(self.vars["line_cut_bins"].get())
        q, intensity = processor.line_cut(q_range, center, width, bins)
        output = output_dir / f"{stem_name}_line_cut"
        save_line_cut(q, intensity, output.with_suffix(".csv"))
        figure, axis = plt.subplots(figsize=(8, 5))
        axis.plot(q, intensity)
        axis.set(xlabel="$Q$ [Angstrom$^{-1}$]", ylabel="Intensity", title="Rigaku GIWAXS sector line cut")
        save_figure(figure, output)
        config = self.write_config(output, processor, {"q_range_A-1": q_range, "chi_center_degrees": center, "chi_width_degrees": width, "line_cut_bins": bins})
        self.message(f"Saved PNG/PDF/SVG/CSV: {output}; config: {config}")
        self.show(figure)

    def show(self, figure):
        if self.vars["show_plots"].get():
            figure.show()
        else:
            plt.close(figure)

    def open_output(self):
        path = self.vars["output_dir"].get().strip()
        if path and Path(path).is_dir():
            os.startfile(path)


def main():
    root = tk.Tk()
    RigakuModernApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
