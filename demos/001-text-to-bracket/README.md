# 001 — Text-to-Bracket

Turn `L-bracket, 4 M6 holes, 3mm steel` into a valid boundary-representation solid with real cylindrical holes. Inspect it in a desktop 3D viewer, change the prompt, and export STEP, STL and a parameter manifest.

## Supported prompts

```text
L-bracket, 4 M6 holes, 3mm steel
L-bracket, 4 M6 holes, 3mm steel, width 90mm
L-bracket, 6 M8 holes, 4mm aluminum, width 90mm, depth 50mm, height 60mm
```

This is a deterministic, constrained parser. It does not use an LLM, infer arbitrary designs, or support general natural-language CAD. Unsupported or ambiguous input is rejected.

- Width, depth and height default to 60, 40 and 40 mm. These are outer dimensions.
- Supported hole counts: 4, 6 and 8. Half are placed on each flange, in one evenly spaced row.
- Supported bolt designations: M3, M4, M5, M6, M8, M10 and M12. The explicit demo clearance diameters are 3.4, 4.5, 5.5, 6.6, 9, 11 and 13.5 mm respectively. They are not threaded holes.
- Thickness: 1–12 mm. Other dimensions: 10–300 mm, subject to hole spacing validation.
- Steel/aluminum are descriptive metadata; no material properties are assigned.
- The bracket has a sharp inside corner. It does not model bend radius, bend allowance, loads, tolerances or manufacturing constraints.
- STEP preserves solid geometry, not a Fusion/SolidWorks parametric feature tree. Edit the Python parameters or rerun a changed prompt to regenerate.

## Controls

Type a supported prompt and press Enter or **Generate solid**. Drag the part to orbit. Use the viewer's navigation to zoom. **Export STEP + STL** writes to `outputs/bracket/` relative to the current working directory. Invalid prompts clear the previous model and block export.

## Implementation

- `bracket.py`: validated parameters, prompt parsing, boolean solid construction, export and CLI.
- `studio.py`: interactive Matplotlib viewer and repeatable video capture.
- `test_bracket.py`: invalid input, solid validity, analytical volume, cylindrical hole count, bounding dimensions, and STEP round-trip checks.

The 3D preview is tessellated from the actual exported solid; it is not an illustrative stand-in.

## Technical references

- [build123d introductory examples](https://build123d.readthedocs.io/en/stable/introductory_examples.html)
- [build123d STEP and STL export](https://build123d.readthedocs.io/en/stable/import_export.html)

## Publishing

Suggested X copy is in `post.txt`. Attach [the demo MP4](../../assets/001-demo.mp4) when posting. The X post is a draft; publishing the repository does not publish to X.
