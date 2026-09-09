# X Demos

One working demo at a time: build it, test it, capture a short walkthrough, and share the code.

![Text-to-Bracket desktop preview](assets/001-text-to-bracket.png)

| Demo | What it does | State |
| --- | --- | --- |
| [001 — Text-to-Bracket](demos/001-text-to-bracket) | A constrained text prompt becomes an actual CAD solid, STEP and STL | Local implementation; publishing pending |

## Run demo 001

Python 3.11+ and a desktop environment are recommended. Dependency wheels must be available for your Python version and platform. The tested environment is macOS Intel with Python 3.14.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demos/001-text-to-bracket/studio.py
```

For a headless command-line export:

```sh
python demos/001-text-to-bracket/bracket.py "L-bracket, 4 M6 holes, 3mm steel"
```

Outputs go into `outputs/bracket/`. Import `bracket.step` into Fusion or SolidWorks. The STEP file contains solid geometry; the editable parameter logic lives in the Python source and JSON, not a native CAD feature timeline.

## Verify and capture

```sh
python -m unittest discover -s demos/001-text-to-bracket -v
python demos/001-text-to-bracket/studio.py --preview outputs/001-preview.png
python demos/001-text-to-bracket/studio.py --record outputs/001-text-to-bracket.mp4
```

Video generation requires FFmpeg on PATH. It captures a 24-second, 1600×900, 24 fps walkthrough from the application's own rendered viewport. The scripted sequence invokes the same parser, solid generator and export actions as the interactive app. It is an application-rendered walkthrough, not a desktop screen recording or a timing benchmark.

All six automated checks passed, including STEP re-import and preventing stale exports after prompt edits. `requirements-lock.txt` captures the complete tested environment; `requirements.txt` pins the direct dependencies.

No account, API key, or paid CAD license is required to run this demo. See the demo README for the supported prompt grammar and model assumptions.
