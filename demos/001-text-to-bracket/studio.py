"""Desktop preview and reproducible video capture of the actual CAD viewport."""
import argparse
from pathlib import Path
import textwrap

from bracket import DEFAULT_PROMPT, build, export, parse_prompt

BG = "#101b22"
PANEL = "#172730"
WHITE = "#eff6f4"
MUTED = "#90aaa9"
ACCENT = "#b7f36c"


class Studio:
    def __init__(self):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, TextBox
        self.plt = plt
        plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": WHITE, "font.size": 11})
        self.fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
        self.fig.canvas.manager.set_window_title("Text-to-Bracket | Demo 001")
        self.fig.text(.045, .938, "FORM / 001", color=ACCENT, size=13, weight="bold")
        self.fig.text(.045, .861, "Text to bracket.", size=35, weight="bold")
        self.fig.text(.045, .818, "A small prompt. A real CAD solid.", color=MUTED, size=15)
        self.fig.text(.75, .94, "LOCAL CAD LAB   /   DEMO 001", size=10, color=MUTED)
        self.fig.text(.045, .712, "01  /  DESCRIBE YOUR PART", size=10, color=ACCENT)
        prompt_ax = self.fig.add_axes([.045, .63, .415, .065])
        self.prompt = TextBox(prompt_ax, "", initial=DEFAULT_PROMPT, color=PANEL, hovercolor="#213540")
        self.prompt.text_disp.set_color(WHITE)
        self.prompt.text_disp.set_fontsize(11)
        self.prompt.on_submit(lambda _: self.generate())
        self.generate_button = Button(self.fig.add_axes([.045, .545, .20, .055]), "Generate solid", color=ACCENT, hovercolor="#d0ff96")
        self.generate_button.label.set_color(BG)
        self.generate_button.label.set_weight("bold")
        self.generate_button.on_clicked(self.generate)
        self.export_button = Button(self.fig.add_axes([.26, .545, .20, .055]), "Export STEP + STL", color=PANEL, hovercolor="#213540")
        self.export_button.label.set_color(WHITE)
        self.export_button.on_clicked(self.save)
        self.fig.text(.045, .477, "02  /  RESOLVED PARAMETERS", size=10, color=ACCENT)
        self.details = self.fig.text(.045, .42, "Waiting for a prompt.", size=16, linespacing=1.9, va="top")
        self.notes = self.fig.text(.045, .18, "Defaults: 60 × 40 × 40 mm. Holes split across both flanges.\nM6 means Ø6.6 mm clearance, not tapped threads.", size=10, color=MUTED, linespacing=1.7)
        self.status = self.fig.text(.045, .09, "Ready to build.", color=ACCENT, size=11)
        self.fig.text(.045, .038, "CONSTRAINED PROMPT PARSER  /  NO API KEY  /  EDITABLE PYTHON PARAMETERS", color=MUTED, size=9)
        self.fig.text(.57, .13, "DRAG TO ORBIT  ·  SCROLL TO ZOOM", color=MUTED, size=9)
        self.fig.text(.57, .095, "Sharp-corner concept · material is metadata only", color=MUTED, size=9)
        self.fig.text(.57, .065, "STEP geometry · Python parameters · no native Fusion timeline", color=MUTED, size=9)
        self.ax = self.fig.add_axes([.49, .17, .50, .66], projection="3d", facecolor=BG)
        self.part = self.params = None
        self.caption = self.fig.text(.55, .855, "03  /  SOLID PREVIEW", color=ACCENT, size=10)
        self.ax.set_axis_off()

    def generate(self, _=None):
        try:
            p = parse_prompt(self.prompt.text)
            shape = build(p)
        except Exception as exc:
            self.status.set_text(textwrap.fill(str(exc), 64))
            self.status.set_color("#ffa89d")
            # Invalidate export so an old part is never silently exported for a bad prompt.
            self.part = self.params = None
            self.ax.clear()
            self.ax.set_axis_off()
            self.details.set_text("Check the prompt and try again.")
            self.fig.canvas.draw_idle()
            return False
        self.params, self.part = p, shape
        self.details.set_text(f"{p.width:g} × {p.depth:g} × {p.height:g} mm\n{p.thickness:g} mm {p.material}  /  {p.holes} × M{p.bolt}\nØ{p.diameter:g} mm clearance holes")
        self.status.set_text(f"Valid solid  /  {shape.volume:,.0f} mm³  /  ready to export")
        self.status.set_color(ACCENT)
        self.draw_part()
        self.fig.canvas.draw_idle()
        return True

    def draw_part(self):
        import numpy as np
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        vertices, triangles = self.part.tessellate(0.08, 0.15)
        points = np.array([tuple(v) for v in vertices])
        faces = points[np.array(triangles)]
        self.ax.clear()
        self.ax.set_axis_off()
        # Use orientation-independent lighting for two-sided tessellated CAD faces.
        # This keeps coplanar triangles visually continuous in the painter renderer.
        normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
        light = np.array([.25, .45, .85])
        light /= np.linalg.norm(light)
        intensity = .42 + .58 * np.abs(normals @ light)
        colors = intensity[:, None] * np.array([.66, .78, .79])
        mesh = Poly3DCollection(faces, facecolors=colors, linewidths=0,
                                antialiased=False, zsort="average")
        self.ax.add_collection3d(mesh)
        # Kernel edges draw the exact holes and silhouette without mesh triangulation noise.
        for edge in self.part.edges():
            samples = np.array([tuple(edge.position_at(i / 80)) for i in range(81)])
            self.ax.plot(samples[:, 0], samples[:, 1], samples[:, 2], color="#47727c", linewidth=.65, alpha=.75)
        p = self.params
        extent = max(p.width, p.depth, p.height)
        for coordinate, size in zip(("x", "y", "z"), (p.width, p.depth, p.height)):
            getattr(self.ax, f"set_{coordinate}lim")(size / 2 - extent * .55, size / 2 + extent * .55)
        self.ax.set_box_aspect((1, 1, 1))
        self.ax.view_init(elev=24, azim=55)
        self.ax.set_proj_type("ortho")

    def save(self, _=None, destination="outputs/bracket"):
        if self.part is None:
            self.status.set_text("Generate a valid part before exporting.")
            self.fig.canvas.draw_idle()
            return False
        # Text edits that have not been submitted must not export the preceding geometry.
        try:
            if parse_prompt(self.prompt.text) != self.params:
                if not self.generate():
                    return False
            export(self.params, self.part, destination)
        except Exception as exc:
            self.status.set_text(textwrap.fill(f"Export failed: {exc}", 64))
            self.status.set_color("#ffa89d")
            self.fig.canvas.draw_idle()
            return False
        self.status.set_text("Exported: bracket.step + bracket.stl + parameters.json")
        self.status.set_color(ACCENT)
        self.fig.canvas.draw_idle()
        return True

    def record(self, path):
        """Capture this application's rendered frames; not a desktop screen recording."""
        from matplotlib.animation import FFMpegWriter
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = FFMpegWriter(fps=24, codec="libx264", bitrate=3500,
                             extra_args=["-pix_fmt", "yuv420p", "-movflags", "+faststart"])
        # Drive the same TextBox, generator, viewport and exporter used interactively.
        self.prompt.eventson = False
        self.prompt.set_val("")
        self.status.set_text("Start with a bracket specification.")
        with writer.saving(self.fig, str(path), 100):
            for frame in range(24 * 24):
                seconds = frame / 24
                if seconds < 3:
                    self.prompt.set_val(DEFAULT_PROMPT[:int(len(DEFAULT_PROMPT) * min(seconds / 2.4, 1))])
                if frame == 72:
                    if not self.generate():
                        raise RuntimeError("First demo generation failed")
                if 3 <= seconds < 11:
                    self.ax.view_init(elev=24, azim=55 + 18 * (seconds - 3))
                if frame == 264:
                    self.caption.set_text("04  /  CHANGE ONE PARAMETER")
                    self.prompt.set_val(DEFAULT_PROMPT + ", width 90mm")
                    if not self.generate():
                        raise RuntimeError("Variant generation failed")
                if 11 <= seconds < 19:
                    self.ax.view_init(elev=26, azim=55 + 14 * (seconds - 11))
                if frame == 456:
                    if not self.save(destination=path.parent / "video-variant"):
                        raise RuntimeError("Demo export failed")
                    self.caption.set_text("05  /  TAKE THE SOLID INTO YOUR CAD TOOL")
                    self.ax.view_init(elev=24, azim=55)
                writer.grab_frame(facecolor=BG)
                if frame % 120 == 0:
                    print(f"Video: {frame // 24}/24 seconds", flush=True)
        self.prompt.eventson = True
        self.fig.savefig(path.with_suffix(".png"), facecolor=BG)
        print(f"Saved {path.resolve()}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", metavar="MP4")
    parser.add_argument("--preview", metavar="PNG")
    args = parser.parse_args()
    if args.record or args.preview:
        import matplotlib
        matplotlib.use("Agg")
    app = Studio()
    if args.record:
        app.record(args.record)
    else:
        app.generate()
        if args.preview:
            Path(args.preview).parent.mkdir(parents=True, exist_ok=True)
            app.fig.savefig(args.preview, facecolor=BG)
        else:
            app.plt.show()


if __name__ == "__main__":
    main()
