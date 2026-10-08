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

### Parameters

| option              | default | meaning                                                    |
| ------------------- | ------- | ---------------------------------------------------------- |
| `--plate-width`     | 254     | plate X, mm                                                |
| `--plate-height`    | 50.75   | plate Y, mm                                                |
| `--plate-thickness` | 1.5     | plate Z, mm                                                |
| `--text-height`     | 0.85    | how far the lettering is raised above the plate, mm        |
| `--text-stroke`     | em/64   | extra stroke thickness per side, mm (`0` = plain Regular)  |
| `--font-size`       | 96      | MakerWorld sign-maker units (96 ≈ 20.2 mm em, 14.4 mm caps) |

Sizes that would overflow the plate (6 mm margin) are clamped with a warning.
The default stroke reproduces MakerWorld's faux-bold rendering of Noto Sans.

```sh
uv run nameplate "Jane Doe" --plate-width 200 --plate-height 40 --text-height 1.2
```

### Screw relief channel (opt-in)

If the door holder's screw head protrudes and rubs the back of the plate, pass
`--channel` to cut a full-length channel in the underside (open at both ends so
the plate slides in). The cross-section is a trapezoid with 45° walls so the
sides are self-supporting; only the flat roof is a short bridge. The head gets
0.4 mm side clearance at its own height, so the opening at the surface is
`diameter + 0.8 + 2 × protrusion` wide. Depth is `protrusion + 0.2 mm`, rounded
up to whole layers (`--layer-height`, default 0.2).

```sh
uv run nameplate "Jane Doe" --channel --screw-diameter 5.8 --screw-offset 22 --screw-height 0.7
```

| option             | default | meaning                                               |
| ------------------ | ------- | ----------------------------------------------------- |
| `--screw-diameter` | 5.8     | screw head diameter, mm                               |
| `--screw-offset`   | 22      | bottom edge of the head from the plate's bottom edge  |
| `--screw-height`   | 0.7     | how far the head protrudes from the holder, mm        |
| `--layer-height`   | 0.2     | print layer height, for snapping the channel depth    |
| `--channel`        | off     | cut the channel                                       |

Those defaults give an 8.0 mm opening narrowing to a 6.0 mm roof, 1.0 mm deep,
at 20.9–28.9 mm from the bottom edge, leaving a 0.5 mm web. Print text side up:
the walls are 45° overhangs and the roof a 6 mm bridge on layer 6, no supports.
The generator refuses channels that would leave less than 0.4 mm of plate.

## Development

```sh
uv run ruff check src
uv run ruff format src
```
