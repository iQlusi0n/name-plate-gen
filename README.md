# nameplate

Generates an office-door name plate as STL and OpenSCAD: a 254 × 50.75 × 1.5 mm
black plate with white Noto Sans lettering raised 0.85 mm on top. The lettering
reproduces the MakerWorld sign-maker preview (same font, faux-bold stroke growth,
size scale and vertical placement).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and the Noto Sans font
(`fonts-noto-core` on Debian/Ubuntu).

```sh
uv sync
```

## Usage

```sh
uv run nameplate "Jane Doe"                       # size 96, output in cwd
uv run nameplate "Dr. J. Doe" --font-size 64 --out-dir out
uv run nameplate --help
```

Outputs, per run:

| file                | content                                                   |
| ------------------- | --------------------------------------------------------- |
| `<name>.scad`       | parametric OpenSCAD model, `color("black")` / `color("white")` |
| `<name>.stl`        | plate and lettering unioned into one watertight body      |
| `<name>_plate.stl`  | plate only – load as the black part in the slicer         |
| `<name>_text.stl`   | lettering only – load as the white part                   |

STL carries no colour; use the two split files for multi-colour prints.

`--font-size` is in MakerWorld sign-maker units (96 ≈ 20.2 mm em, 14.4 mm
capitals). Sizes that would overflow the plate are clamped with a warning.
Plate dimensions and lettering height are overridable (`--width`, `--height`,
`--thickness`, `--raise`).

## Development

```sh
uv run ruff check src
uv run ruff format src
```
