# kicad-export-gerber-mill

A script to export Gerber files from a Kicad PCB for usage with CNC milling machines.


## How to run

The script requires Python 3 and Kicad/Pcbnew with Python support. It should be run from command line:

    $ ./kicad-export-gerber-mill.py --tool-dia 800 --output-dir ./gerber mypcb.kicad_pcb

The arguments used in the example are the default values and can be ommited. Tool diameter is in `um`, not `mm`. Please run `./kicad-export-gerber-mill.py --help` for details.


## Script actions

When running the script, it will:

- Load the board from file
- Patch any PTH pads' drill hole to circular, with the configured tool diameter.
- Validate vias' drill hole diameter against the configured tool diameter.
- Export bottom copper layer Gerber, relative to auxiliar origin axis.
- Export outline layer Gerber, relative to auxiliar origin axis.
- Export Excellon drill files (PTH and NPTH), relative to auxiliar origin axis.

It is recommended to validate the output files with a Gerber viewer. The script won't change the original Kicad PCB file.


## Limitations

- The script will try to change the drill hole size of the pads, as allowed by their copper size. This is not always possible, e.g. when the pad size is smaller than the configured tool diameter, or the pad size is too close to the drill hole size. For the same reason, vias can't be automatically fixed, and the script will just validate their drill hole sizes.
