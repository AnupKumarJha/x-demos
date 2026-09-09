"""Bare drawing → automatic dimensions → geometry edit, with an interactive viewer."""
import argparse
from dataclasses import replace
from pathlib import Path
import textwrap

from drawing import SAMPLE, PAPER, load, render, export

BG = '#11232a'
TEXT = '#f4f4e9'
MUTED = '#abc0bd'
ACCENT = '#c5f48b'


class Studio:
    def __init__(self, source=SAMPLE):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, TextBox
        self.plt = plt
        self.base = load(source)
        self.plate = self.base
        self.stage = 0
        plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT})
        self.fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
        self.fig.canvas.manager.set_window_title('Auto-Dimension | Demo 003')
        self.fig.text(.045, .941, 'FORM / 003', color=ACCENT, size=13, weight='bold')
        self.fig.text(.045, .86, 'Drawing it was the fun part.', color=TEXT, size=35, weight='bold')
        self.subtitle = self.fig.text(.045, .807, 'Now let the geometry handle the numbers.', color=MUTED, size=17)
        self.fig.text(.75, .941, 'LOCAL DRAWING LAB / DEMO 003', color=MUTED, size=10)
        self.fig.text(.065, .744, 'BEFORE / JUST THE GEOMETRY', color=MUTED, size=10)
        self.caption = self.fig.text(.475, .744, 'AFTER / WAITING FOR DIMENSIONS', color=ACCENT, size=10)
        self.left = self.fig.add_axes([.045, .265, .39, .44], facecolor=PAPER)
        self.right = self.fig.add_axes([.46, .265, .50, .44], facecolor=PAPER)
        self.fig.text(.065, .236, 'Stepped plate · 2 holes · top view', color=MUTED, size=10)
        self.fig.text(.475, .236, 'Dimensions come from coordinates, not typed labels.', color=MUTED, size=10)
        self.width = TextBox(self.fig.add_axes([.14, .147, .11, .048]), 'Width (mm)  ',
                             initial=str(self.base.width), color='#28414a', hovercolor='#36545d')
        self.width.label.set_color(MUTED)
        self.width.text_disp.set_color(TEXT)
        self.width.on_submit(lambda _: self.generate())
        self.buttons = []
        for x, w, label, callback, color in [
            (.29, .20, 'Add dimensions', self.generate, ACCENT),
            (.515, .18, 'Hide dimensions', self.hide, '#28414a'),
            (.72, .24, 'Export SVG + PNG + JSON', self.save, '#28414a')]:
            button = Button(self.fig.add_axes([x, .147, w, .048]), label, color=color, hovercolor='#7cb1a4')
            button.label.set_color(BG if color == ACCENT else TEXT)
            button.on_clicked(callback)
            self.buttons.append(button)
        self.status = self.fig.text(.045, .093, 'The shape is there. The measurements are not.', color=ACCENT, size=12)
        self.fig.text(.045, .037, 'REFERENCE DIMENSIONS · SIMPLE STEPPED PLATES · NO API KEY · NOT A MANUFACTURING RELEASE', color=MUTED, size=9)
        self.draw()

    def draw(self):
        if self.plate is not None:
            render(self.left, self.plate, 0)
            render(self.right, self.plate, self.stage)
        self.fig.canvas.draw_idle()

    def generate(self, _=None):
        try:
            self.plate = replace(self.base, width=float(self.width.text)).validate()
            self.stage = 3
            self.caption.set_text('AFTER / DIMENSIONS COMPUTED FROM GEOMETRY')
            self.status.set_text(f'{self.plate.width:g} mm wide. Edge sizes, hole positions and diameters updated.')
            self.status.set_color(ACCENT)
            self.draw()
            return True
        except Exception as exc:
            self.plate = None
            for ax in (self.left, self.right):
                ax.clear()
                ax.set_axis_off()
            self.status.set_text(textwrap.fill(str(exc), 110))
            self.status.set_color('#ffaf9d')
            self.fig.canvas.draw_idle()
            return False

    def hide(self, _=None):
        if self.generate():
            self.stage = 0
            self.caption.set_text('AFTER / WAITING FOR DIMENSIONS')
            self.status.set_text('Dimensions hidden. Geometry is unchanged.')
            self.draw()

    def save(self, _=None, destination='outputs/auto-dimension'):
        if not self.generate():
            return False
        try:
            export(self.plate, destination)
        except Exception as exc:
            self.status.set_text(f'Export failed: {exc}')
            return False
        self.status.set_text('Exported drawing.svg + drawing.png + plate.json + dimensions.json')
        self.fig.canvas.draw_idle()
        return True

    def record(self, path):
        from matplotlib.animation import FFMpegWriter
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.width.eventson = False
        writer = FFMpegWriter(fps=24, codec='libx264', bitrate=3500,
                             extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
        with writer.saving(self.fig, str(path), 100):
            for frame in range(24*20):
                if frame == 48:
                    self.stage = 1
                    self.caption.set_text('01 / OVERALL WIDTH + HEIGHT')
                    self.status.set_text('Start with the outside dimensions.')
                    self.draw()
                if frame == 96:
                    self.stage = 2
                    self.caption.set_text('02 / LOCATE THE STEP')
                    self.status.set_text('The step gets its own dimensions.')
                    self.draw()
                if frame == 144:
                    if not self.generate():
                        raise RuntimeError('Dimension generation failed')
                    self.caption.set_text('03 / HOLE CENTERS + DIAMETER')
                    self.status.set_text('And the holes: where they go, and how big they are.')
                if frame == 240:
                    self.width.set_val('120')
                    if not self.generate():
                        raise RuntimeError('Width edit failed')
                    self.caption.set_text('04 / STRETCH IT. THE NUMBERS FOLLOW.')
                    self.subtitle.set_text('100 → 120 mm. No retyping the dimensions.')
                    self.status.set_text('Width: 100 → 120. Right hole center: 80 → 100. Inset stays 20 mm.')
                if frame == 360:
                    if not self.save(destination=path.parent/'003-export'):
                        raise RuntimeError('Drawing export failed')
                    self.caption.set_text('05 / TAKE THE DRAWING WITH YOU')
                writer.grab_frame(facecolor=BG)
                if frame % 120 == 0:
                    print(f'Video: {frame//24}/20 seconds', flush=True)
        self.width.eventson = True
        self.fig.savefig(path.with_suffix('.png'), facecolor=BG)
        print(f'Saved {path}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, default=SAMPLE)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.preview or args.record:
        import matplotlib
        matplotlib.use('Agg')
    app = Studio(args.input)
    if args.record:
        app.record(args.record)
    elif args.preview:
        app.generate()
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        app.fig.savefig(args.preview, facecolor=BG)
    else:
        app.plt.show()


if __name__ == '__main__':
    main()
