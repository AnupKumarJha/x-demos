"""Exploded gripper assembly with a live pack-aware bill of materials."""
import argparse
from pathlib import Path

import numpy as np
from bom import load, validate, calculate, export_bom, money
from geometry import build, export_assembly

BG = '#101f29'
PANEL = '#203541'
TEXT = '#f2f5ed'
MUTED = '#9bb1bb'
ACCENT = '#c4f589'


class Studio:
    def __init__(self, assembly_path=None, catalog_path=None):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Button, TextBox
        from matplotlib.colors import to_rgb
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        self.plt = plt
        self.assembly, self.catalog = load(assembly_path, catalog_path)
        self.nodes = validate(self.assembly, self.catalog)
        self.result = None
        self.explosion = 0
        self.visible = False
        plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': TEXT})
        self.fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
        self.fig.canvas.manager.set_window_title('Assembly-to-BOM | Demo 004')
        self.fig.text(.045, .944, 'FORM / 004', color=ACCENT, size=13, weight='bold')
        self.fig.text(.045, .865, 'Your CAD model looks finished.', size=34, weight='bold')
        self.subtitle = self.fig.text(.045, .811, 'Your shopping cart disagrees.', color=MUTED, size=19)
        self.fig.text(.76, .944, 'LOCAL CAD LAB / DEMO 004', color=MUTED, size=10)
        self.caption = self.fig.text(.045, .738, '01 / ONE CONCEPT GRIPPER', color=ACCENT, size=10)
        self.fig.text(.53, .738, '02 / THE PARTS YOU NEED', color=ACCENT, size=10)
        self.ax = self.fig.add_axes([.015, .245, .50, .49], projection='3d', facecolor=BG)
        self.ax.set_axis_off()
        self.ax.set_proj_type('ortho')
        self.ax.set_box_aspect((1, 1, 1), zoom=1.6)
        self.ax.view_init(elev=22, azim=-63)
        self.meshes = []
        all_colors = []
        model = build(self.assembly, self.catalog)
        for node, shape in zip(self.nodes, model.children):
            vertices, triangles = shape.tessellate(.2, .4)
            points = np.array([tuple(v) for v in vertices])
            faces = points[np.array(triangles)]
            normals = np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])
            normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
            light = np.array([.3, -.45, .84])
            brightness = .45 + .55*np.abs(normals@light)
            color = np.array(to_rgb(self.catalog['parts'][node['sku']]['color']))
            all_colors.append(brightness[:, None]*color)
            self.meshes.append((faces, np.array(node['explode'])))
        # Sort triangles across every component, avoiding whole-object painter artifacts.
        self.mesh_artist = Poly3DCollection(np.concatenate([f for f, _ in self.meshes]),
                                           facecolors=np.concatenate(all_colors), linewidths=0,
                                           antialiased=False, zsort='average')
        self.ax.add_collection3d(self.mesh_artist)
        self.table_artists = []
        self.table_hint = self.fig.text(.53, .58, 'Looks like one thing.\nHow many parts is it?',
                                        size=25, weight='bold', linespacing=1.6)
        self.total = self.fig.text(.53, .279, '', size=30, weight='bold', color=ACCENT)
        self.total_note = self.fig.text(.53, .242, '', size=10, color=MUTED)
        self.fig.text(.045, .239, 'Concept geometry · one assembly shown at every batch size', color=MUTED, size=9)
        self.batch = TextBox(self.fig.add_axes([.125, .151, .075, .048]), 'Build qty  ', initial='1',
                             color=PANEL, hovercolor='#36515e')
        self.batch.label.set_color(MUTED)
        self.batch.text_disp.set_color(TEXT)
        self.batch.on_submit(lambda _: self.reveal())
        self.buttons = []
        for x, w, label, action, color in [
            (.245, .19, 'Reveal parts list', self.reveal, ACCENT),
            (.46, .23, 'Assemble / explode', self.toggle, PANEL),
            (.72, .24, 'Export BOM + STEP', self.save, PANEL)]:
            button = Button(self.fig.add_axes([x, .151, w, .048]), label, color=color, hovercolor='#739b99')
            button.label.set_color(BG if color == ACCENT else TEXT)
            button.on_clicked(action)
            self.buttons.append(button)
        self.status = self.fig.text(.045, .096, 'Start with the assembly. Find out what is inside.', color=ACCENT, size=12)
        self.fig.text(.045, .038, 'SAMPLE USD PRICES · NO TAX / SHIPPING / LABOR · SIMPLIFIED GEOMETRY · NOT A VALIDATED GRIPPER DESIGN', color=MUTED, size=9)
        self.move(0)

    def move(self, amount):
        self.explosion = amount
        self.mesh_artist.set_verts(np.concatenate([faces+amount*offset for faces, offset in self.meshes]))
        radius = 47+amount*48
        self.ax.set_xlim(-radius, radius)
        self.ax.set_ylim(-radius, radius)
        self.ax.set_zlim(28-radius, 28+radius)

    def draw_table(self):
        for artist in self.table_artists:
            artist.remove()
        self.table_artists = []
        self.table_hint.set_visible(False)
        def label(x, y, value, color=TEXT, size=12, **kwargs):
            artist = self.fig.text(x, y, value, color=color, size=size, **kwargs)
            self.table_artists.append(artist)
        for x, name, align in [(.53, 'PART', 'left'), (.795, 'NEED', 'right'),
                               (.865, 'PACKS', 'right'), (.962, 'COST', 'right')]:
            label(x, .674, name, MUTED, 10, ha=align)
        for index, row in enumerate(self.result['rows']):
            y = .618-index*.046
            label(.53, y, row['name'], self.catalog['parts'][row['sku']]['color'], 12)
            label(.795, y, str(row['required']), ha='right')
            label(.865, y, str(row['packs']), ha='right')
            label(.962, y, money(row['line_total_cents']), ha='right')
        self.total.set_text(money(self.result['total_cents']))
        batch = self.result['batch']
        spare = sum(row['spare'] for row in self.result['rows'])
        self.total_note.set_text(f'Sample purchase estimate / {batch} gripper(s) / {spare} spare pieces')

    def reveal(self, _=None):
        try:
            batch = int(self.batch.text)
            self.result = calculate(self.assembly, self.catalog, batch)
        except (ValueError, TypeError) as exc:
            self.result = None
            for artist in self.table_artists:
                artist.remove()
            self.table_artists = []
            self.total.set_text('')
            self.total_note.set_text('')
            self.status.set_text(str(exc))
            self.status.set_color('#ffb29b')
            self.fig.canvas.draw_idle()
            return False
        self.visible = True
        self.draw_table()
        self.caption.set_text('01 / THE SAME ASSEMBLY, PULLED APART')
        self.status.set_text(f"{self.result['component_instances']} part instances → {len(self.result['rows'])} unique purchase lines. Repeats counted by SKU.")
        self.status.set_color(ACCENT)
        self.move(1)
        self.fig.canvas.draw_idle()
        return True

    def toggle(self, _=None):
        self.move(0 if self.explosion > .5 else 1)
        self.fig.canvas.draw_idle()

    def save(self, _=None, destination='outputs/assembly-bom'):
        if not self.reveal():
            return False
        try:
            export_bom(self.assembly, self.catalog, self.result['batch'], destination)
            export_assembly(self.assembly, self.catalog, destination)
        except Exception as exc:
            self.status.set_text(f'Export failed: {exc}')
            self.status.set_color('#ffb29b')
            return False
        self.status.set_text('Exported bom.csv + bom.json + gripper.step. Nothing ordered.')
        self.fig.canvas.draw_idle()
        return True

    def record(self, path):
        from matplotlib.animation import FFMpegWriter
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.batch.eventson = False
        writer = FFMpegWriter(fps=24, codec='libx264', bitrate=3500,
                             extra_args=['-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
        with writer.saving(self.fig, str(path), 100):
            for frame in range(24*24):
                seconds = frame/24
                if seconds < 3:
                    self.ax.view_init(elev=22, azim=-63+seconds*8)
                if 3 <= seconds < 6:
                    t = (seconds-3)/3
                    self.move(t*t*(3-2*t))
                    self.caption.set_text('01 / WAIT. THERE ARE 22 PIECES IN HERE.')
                if frame == 144:
                    if not self.reveal():
                        raise RuntimeError('BOM generation failed')
                    self.subtitle.set_text('22 pieces. Six purchase lines. One parts list.')
                if frame == 240:
                    self.status.set_text('Need 8 bolts? The sample catalog sells packs of 20. Buy 1 pack; keep 12 spares.')
                if frame == 336:
                    self.batch.set_val('10')
                    if not self.reveal():
                        raise RuntimeError('Batch update failed')
                    self.subtitle.set_text('Now make ten. The shopping list catches up.')
                    self.status.set_text('80 bolts → 4 packs. 80 nuts → 4 packs. No leftover fasteners in this batch.')
                if frame == 480:
                    if not self.save(destination=path.parent/'004-export'):
                        raise RuntimeError('Export failed')
                writer.grab_frame(facecolor=BG)
                if frame % 120 == 0:
                    print(f'Video: {seconds:g}/24 seconds', flush=True)
        self.batch.eventson = True
        self.fig.savefig(path.with_suffix('.png'), facecolor=BG)
        print(f'Saved {path}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', type=Path)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    if args.preview or args.record:
        import matplotlib
        matplotlib.use('Agg')
    app = Studio(args.assembly, args.catalog)
    if args.record:
        app.record(args.record)
    elif args.preview:
        app.reveal()
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        app.fig.savefig(args.preview, facecolor=BG)
    else:
        app.plt.show()


if __name__ == '__main__':
    main()
