"""Interactive image-to-solid viewer and repeatable application-rendered video."""
import argparse
from pathlib import Path
import textwrap

import numpy as np
from sketch import SAMPLE, trace, build, export

BG = '#0c1821'
PANEL = '#192b36'
TEXT = '#eef5f4'
MUTED = '#95adb8'
ACCENT = '#b9f478'


class Studio:
    def __init__(self, image=SAMPLE):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, TextBox
        self.plt = plt
        self.path = Path(image)
        self.part = None
        self.points = None
        self.signature = None
        plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT, 'font.size': 11})
        self.fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
        self.fig.canvas.manager.set_window_title('Sketch-to-3D | Demo 002')
        self.fig.text(.045, .94, 'FORM / 002', color=ACCENT, size=13, weight='bold')
        self.fig.text(.045, .864, 'Sketch. Trace. Make it solid.', size=34, weight='bold')
        self.fig.text(.045, .815, 'One closed outline → an editable extrusion → STEP + STL', color=MUTED, size=15)
        self.fig.text(.77, .94, 'LOCAL CAD LAB  /  DEMO 002', color=MUTED, size=10)
        self.input_label = self.fig.text(.045, .76, '01 / INPUT IMAGE', color=ACCENT, size=10)
        self.output_label = self.fig.text(.51, .76, '02 / ACTUAL CAD SOLID', color=ACCENT, size=10)
        self.image_ax = self.fig.add_axes([.045, .30, .40, .425], facecolor=PANEL)
        self.ax = self.fig.add_axes([.48, .26, .49, .48], projection='3d', facecolor=BG)
        self.image_ax.set_axis_off()
        self.ax.set_axis_off()
        self.image_note = self.fig.text(.045, .276, '', color=MUTED, size=10)
        self.details = self.fig.text(.52, .267, 'A flat outline becomes a real solid.', color=MUTED, size=12)
        self.fields = {}
        for x, name, value in [(.095, 'Width', '80'), (.262, 'Depth', '8'), (.448, 'Threshold', '120')]:
            box = TextBox(self.fig.add_axes([x, .188, .075, .047]), name+'  ', initial=value,
                          color=PANEL, hovercolor='#26404d')
            box.label.set_color(MUTED)
            box.label.set_fontsize(10)
            box.text_disp.set_color(TEXT)
            box.on_submit(lambda _: self.generate())
            self.fields[name] = box
        self.buttons = []
        for x, width, label, callback, color in [
            (.555, .13, 'Open image', self.open_image, PANEL),
            (.696, .115, 'Build solid', self.generate, ACCENT),
            (.823, .14, 'Export files', self.save, PANEL)]:
            button = Button(self.fig.add_axes([x, .188, width, .047]), label, color=color, hovercolor='#65948d')
            button.label.set_color(BG if color == ACCENT else TEXT)
            button.on_clicked(callback)
            self.buttons.append(button)
        self.status = self.fig.text(.045, .117, 'Ready.', color=ACCENT, size=12)
        self.fig.text(.045, .063, 'WIDTH + DEPTH IN MM  /  DARK CLOSED OUTLINES ON LIGHT PAPER  /  NO API KEY', color=MUTED, size=9)
        self.fig.text(.045, .035, '2.5D extrusion · no perspective reconstruction · editable JSON profile, not a native CAD feature tree', color=MUTED, size=9)
        self.fig.text(.73, .117, 'DRAG THE SOLID TO ORBIT', color=MUTED, size=9)

    def current_signature(self):
        stat = self.path.stat()
        return (str(self.path.resolve()), stat.st_mtime_ns, stat.st_size,
                *(self.fields[key].text for key in ('Width', 'Depth', 'Threshold')))

    def invalidate(self, message):
        self.part = self.points = self.signature = None
        self.ax.clear()
        self.ax.set_axis_off()
        self.details.set_text('No exportable solid. Check the image and settings.')
        self.status.set_text(textwrap.fill(str(message), 90))
        self.status.set_color('#ffaba0')
        self.fig.canvas.draw_idle()
        return False

    def generate(self, _=None):
        try:
            self.image_ax.clear()
            self.image_ax.set_axis_off()
            width, depth, threshold = (float(self.fields[key].text) for key in ('Width', 'Depth', 'Threshold'))
            im, pixels, points = trace(self.path, width, threshold)
            self.image_ax.imshow(im)
            ring = np.vstack((pixels, pixels[0]))
            self.image_ax.plot(ring[:, 0], ring[:, 1], color='#168888', lw=1.6)
            self.image_ax.scatter(pixels[:, 0], pixels[:, 1], s=9, color='#168888')
            self.part = build(points, depth)
            self.points, self.depth = points, depth
            self.signature = self.current_signature()
            self.image_note.set_text('Bundled synthetic sketch · teal = extracted boundary' if self.path == SAMPLE
                                     else self.path.name + ' · teal = extracted boundary')
            self.draw_part()
            self.details.set_text(f'{width:g} mm wide  /  {depth:g} mm deep  /  {len(points)} profile vertices')
            self.status.set_text(f'One valid solid · {self.part.volume:,.0f} mm³ · ready to export')
            self.status.set_color(ACCENT)
            self.fig.canvas.draw_idle()
            return True
        except Exception as exc:
            return self.invalidate(exc)

    def draw_part(self):
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        vertices, triangles = self.part.tessellate(.08, .15)
        points = np.array([tuple(v) for v in vertices])
        faces = points[np.array(triangles)]
        normals = np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
        light = np.array([.2, .45, .87])
        brightness = .4 + .6 * np.abs(normals @ (light / np.linalg.norm(light)))
        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.add_collection3d(Poly3DCollection(faces, facecolors=brightness[:, None] * [.63, .80, .86],
                                                 linewidths=0, antialiased=False))
        for edge in self.part.edges():
            v = np.array([tuple(edge.position_at(t)) for t in (0, 1)])
            self.ax.plot(*v.T, color='#48717f', linewidth=.8)
        low, high = points.min(axis=0), points.max(axis=0)
        center = (low+high)/2
        extent = max(high-low) * .55
        for axis, value in zip('xyz', center):
            getattr(self.ax, f'set_{axis}lim')(value-extent, value+extent)
        self.ax.set_box_aspect((1, 1, 1))
        self.ax.set_proj_type('ortho')
        self.ax.view_init(elev=35, azim=-62)

    def open_image(self, _=None):
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        path = filedialog.askopenfilename(title='Choose one closed outline',
                                         filetypes=[('Sketch images', '*.png *.jpg *.jpeg *.webp')])
        root.destroy()
        if path:
            self.path = Path(path)
            self.generate()

    def save(self, _=None, destination='outputs/sketch-to-3d'):
        try:
            if self.part is None or self.current_signature() != self.signature:
                if not self.generate():
                    return False
            export(self.part, self.points, self.depth, destination, self.path.name)
            self.status.set_text('Exported  model.step  +  model.stl  +  profile.json')
            self.status.set_color(ACCENT)
            self.fig.canvas.draw_idle()
            return True
        except Exception as exc:
            return self.invalidate(exc)

    def record(self, path):
        from matplotlib.animation import FFMpegWriter
        from PIL import Image
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.image_ax.imshow(Image.open(self.path))
        self.image_note.set_text('Bundled synthetic sketch · one closed outline')
        self.status.set_text('Start with a sketch image. Set the real-world width.')
        self.fields['Depth'].eventson = False
        writer = FFMpegWriter(fps=24, codec='libx264', bitrate=3500,
                             extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
        with writer.saving(self.fig, str(path), 100):
            for frame in range(24 * 22):
                seconds = frame / 24
                if frame == 72:
                    if not self.generate():
                        raise RuntimeError('Initial solid generation failed')
                    self.output_label.set_text('02 / TRACE THE IMAGE. EXTRUDE THE PROFILE.')
                if 3 <= seconds < 10:
                    self.ax.view_init(elev=35, azim=-62 + 8*(seconds-3))
                if frame == 240:
                    self.fields['Depth'].set_val('24')
                    if not self.generate():
                        raise RuntimeError('Depth edit failed')
                    self.output_label.set_text('03 / EDIT DEPTH: 8 mm → 24 mm')
                if 10 <= seconds < 17:
                    self.ax.view_init(elev=35, azim=-62 + 10*(seconds-10))
                if frame == 408:
                    if not self.save(destination=path.parent/'002-export'):
                        raise RuntimeError('Export failed')
                    self.output_label.set_text('04 / STEP + STL + EDITABLE PROFILE')
                    self.ax.view_init(elev=35, azim=-62)
                writer.grab_frame(facecolor=BG)
                if frame % 120 == 0:
                    print(f'Video: {seconds:g}/22 seconds', flush=True)
        self.fields['Depth'].eventson = True
        self.fig.savefig(path.with_suffix('.png'), facecolor=BG)
        print(f'Saved {path}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', type=Path, default=SAMPLE)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.preview or args.record:
        import matplotlib
        matplotlib.use('Agg')
    app = Studio(args.image)
    if args.record:
        app.record(args.record)
    else:
        if not app.generate():
            raise SystemExit('Unable to generate solid')
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            app.fig.savefig(args.preview, facecolor=BG)
        else:
            app.plt.show()


if __name__ == '__main__':
    main()
