# ui/analyze_chart.py
# Matplotlib alapú Analyze grafikon – scatter / box / bar / idősort

import numpy as np

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib

matplotlib.use("Qt5Agg")

from config.settings import PALETTE


class AnalyzeChart(QWidget):
    """
    Interaktív grafikon a kiválasztott metrikához.
    Támogatott típusok: scatter, box, bar, time_series
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib figure – Tobii sötét stílus
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.fig.patch.set_facecolor(PALETTE['bg_card'])

        self.ax = self.fig.add_subplot(111)
        self._apply_axes_style()

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet(f"background-color: {PALETTE['bg_card']};")
        layout.addWidget(self.canvas)

        # Alapból üres
        self._draw_empty("Válassz metrikát és rögzítéseket")

    # ------------------------------------------------------------
    def _apply_axes_style(self):
        p = PALETTE
        self.ax.set_facecolor(p['bg_card'])
        for spine in self.ax.spines.values():
            spine.set_color(p['border'])
        self.ax.tick_params(colors=p['text_secondary'], labelsize=9)
        self.ax.xaxis.label.set_color(p['text_secondary'])
        self.ax.yaxis.label.set_color(p['text_secondary'])
        self.ax.title.set_color(p['text_primary'])
        self.ax.grid(True, color=p['border'], linestyle=':', linewidth=0.5, alpha=0.6)

    # ------------------------------------------------------------
    def _draw_empty(self, msg: str):
        self.ax.clear()
        self._apply_axes_style()
        self.ax.text(0.5, 0.5, msg,
                     ha='center', va='center',
                     color=PALETTE['text_muted'], fontsize=11,
                     transform=self.ax.transAxes)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw_idle()

    # ------------------------------------------------------------
    # FŐ RAJZOLÓ
    # ------------------------------------------------------------
    def plot(self, data: dict, chart_type: str = "scatter",
             ref_line: float = None):
        """
        data: Analyzer.collect() visszatérési értéke
        chart_type: "scatter" | "box" | "bar" | "time_series"
        ref_line: referencia vonal (pl. 720 ms)
        """
        is_3d = chart_type == "3d_surface"
        self.fig.clear()
        self.ax = self.fig.add_subplot(111, projection="3d" if is_3d else None)
        self.ax.clear()
        self._apply_axes_style()

        groups = data.get("groups", [])
        if not groups:
            self._draw_empty("Nincs megjeleníthető adat")
            return

        unit = data.get("unit", "")
        ylabel = f"{data.get('metric_label', '')} ({unit})" if unit else data.get('metric_label', '')
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(data.get('metric_label', ''), loc='left', fontsize=11, pad=12)

        color = data.get("color", PALETTE['accent_primary'])
        names = [g["name"] for g in groups]
        x = np.arange(len(names))

        if chart_type == "3d_surface":
            self._plot_3d(groups, color)
            self.fig.tight_layout()
            self.canvas.draw_idle()
            return
        if chart_type == "scatter":
            self._plot_scatter(groups, x, color)
        elif chart_type == "box":
            self._plot_box(groups, x, color)
        elif chart_type == "bar":
            self._plot_bar(groups, x, color)
        elif chart_type == "time_series":
            self._plot_time_series(groups, x, color)

        # X tengely feliratok
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(names, rotation=0, ha='center', fontsize=9)

        # Referencia vonal
        if ref_line is not None:
            self.ax.axhline(ref_line, color=PALETTE['accent_warning'],
                            linewidth=1, linestyle='--', alpha=0.7,
                            label=f"Referencia: {ref_line:.0f}")

        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ------------------------------------------------------------
    def _plot_scatter(self, groups, x, color):
        rng = np.random.default_rng(42)
        for i, g in enumerate(groups):
            vals = np.array(g["values"])
            jitter = rng.uniform(-0.18, 0.18, size=len(vals))
            self.ax.scatter(
                x[i] + jitter, vals,
                s=32, alpha=0.85,
                color=color, edgecolors='white', linewidths=0.5
            )
            # Átlag vonal
            self.ax.hlines(
                g["mean"], x[i] - 0.3, x[i] + 0.3,
                colors=PALETTE['text_primary'], linewidths=1.5
            )
            # Medián
            self.ax.hlines(
                g["median"], x[i] - 0.25, x[i] + 0.25,
                colors=PALETTE['accent_warning'], linewidths=1, linestyles='--'
            )

    def _plot_box(self, groups, x, color):
        data = [g["values"] for g in groups]
        bp = self.ax.boxplot(
            data, positions=x, widths=0.55, patch_artist=True,
            boxprops=dict(facecolor=color, alpha=0.35, edgecolor=color, linewidth=1.2),
            medianprops=dict(color=PALETTE['accent_warning'], linewidth=1.8),
            whiskerprops=dict(color=PALETTE['border_light']),
            capprops=dict(color=PALETTE['border_light']),
            flierprops=dict(marker='o', markerfacecolor=PALETTE['accent_danger'],
                            markersize=4, markeredgecolor='none')
        )

    def _plot_bar(self, groups, x, color):
        means = [g["mean"] for g in groups]
        stds = [g["std"] for g in groups]
        self.ax.bar(
            x, means, width=0.55, color=color, alpha=0.75,
            edgecolor=color, linewidth=1.2, yerr=stds, capsize=4,
            error_kw=dict(ecolor=PALETTE['text_secondary'], lw=1)
        )
        # Érték feliratok
        for i, m in enumerate(means):
            self.ax.text(x[i], m, f"{m:.1f}", ha='center', va='bottom',
                         color=PALETTE['text_primary'], fontsize=8)

    def _plot_time_series(self, groups, x, color):
        for g in groups:
            vals = g["values"]
            xx = np.arange(len(vals))
            self.ax.plot(xx, vals, color=color, linewidth=1.5, label=g["name"])
            self.ax.scatter(xx, vals, s=18, color=color, alpha=0.7)
        if len(groups) > 1:
            self.ax.legend(frameon=False, labelcolor=PALETTE['text_secondary'],
                           fontsize=8)

    def _plot_3d(self, groups, color):
        self.ax.set_xlabel("Csoport")
        self.ax.set_ylabel("Minta")
        self.ax.set_zlabel("Érték")
        for group_index, group in enumerate(groups):
            values = np.asarray(group["values"], dtype=float)
            sample_index = np.arange(len(values))
            self.ax.plot(
                np.full(len(values), group_index),
                sample_index,
                values,
                color=color,
                linewidth=2.0,
                alpha=0.9,
            )
            self.ax.scatter(
                np.full(len(values), group_index),
                sample_index,
                values,
                color=color,
                s=18,
                alpha=0.75,
            )
        self.ax.set_xticks(np.arange(len(groups)))
        self.ax.set_xticklabels([g["name"] for g in groups], rotation=15, ha="right")
        self.ax.view_init(elev=25, azim=-55)

    # ------------------------------------------------------------
    def save_png(self, path: str):
        try:
            self.fig.savefig(path, dpi=200, facecolor=PALETTE['bg_card'])
            return True
        except Exception as e:
            print(f"[CHART] PNG mentés hiba: {e}")
            return False

    def save_svg(self, path: str):
        try:
            self.fig.savefig(path, format='svg', facecolor=PALETTE['bg_card'])
            return True
        except Exception as e:
            print(f"[CHART] SVG mentés hiba: {e}")
            return False