# kicad-export-gerber-mill

A script to export Gerber files from a Kicad PCB for usage with CNC milling machines.


## How to run

The script requires Python 3 and Kicad/Pcbnew with Python support. It should be run from command line:

    $ ./kicad-export-gerber-mill.py \
          --tool-dia 800 \
          --tool-dia-tolerance 50 \
          --grow-pads 0 \
          --output-dir ./gerber \
          mypcb.kicad_pcb

The arguments used in the example are the default values and can be ommited. Tool diameter is in `um`, not `mm`. Please run `./kicad-export-gerber-mill.py --help` for details and other arguments.

It is also possible to list the drill sizes used by the PCB using the following command:

    $ ./kicad-export-gerber-mill.py \
          --list-pads \
          mypcb.kicad_pcb


## Script actions

When running the script, it will:

- Load the board from file
- Patch any PTH pads' drill hole to circular, with the configured tool diameter, if they are into the tolerance of the configured tool diameter.
- Grow PTH pads, if configured.
- Validate vias' drill hole diameter against the configured tool diameter.
- Export bottom copper layer Gerber, relative to auxiliar origin axis.
- Export outline layer Gerber, relative to auxiliar origin axis.
- Export Excellon drill files (PTH and NPTH), relative to auxiliar origin axis.
- Save a copy of patched Kicad PCB file.
- Save a `command.txt` file with the command-line arguments passed when invoking the script.

It is recommended to validate the output files with a Gerber viewer and/or the exported Kicad PCB file. The script won't change the original Kicad PCB file.


## Limitations

- Vias can't be automatically fixed, and the script will just validate their drill hole sizes.
