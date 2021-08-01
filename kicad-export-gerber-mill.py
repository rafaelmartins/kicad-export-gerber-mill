#!/usr/bin/env python3

import argparse
import os
import pathlib
import pcbnew

parser = argparse.ArgumentParser(description='Export Gerber files from a Kicad '
                                 'PCB, for usage with CNC milling machines')
parser.add_argument('--tool-dia', metavar='DIA', type=int,
                    help='drill bit diameter (in um, default: 800)', default=800)
parser.add_argument('--output-dir', metavar='DIR', type=pathlib.Path,
                    help='output directory (default: ./gerber)', default='./gerber')
parser.add_argument('kicad_pcb', metavar='KICAD_PCB', type=pathlib.Path,
                    help='a Kicad PCB file')


def patch_board(fileobj, tool_dia):
    board = pcbnew.LoadBoard(os.fspath(fileobj.resolve()))

    drill_size = pcbnew.wxSize(tool_dia * 1000, tool_dia * 1000)

    # iterate over pads
    for pad in board.GetPads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_STANDARD:

            # validate pad size
            size = pad.GetSize()
            if drill_size.x > size.x or drill_size.y > size.y:
                raise RuntimeError('Invalid pad size: %s' % size)

            # fix pad size
            pad.SetDrillSize(drill_size)
            pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)

    # iterate over vias
    for via in board.GetTracks():
        if type(via) is not pcbnew.VIA:
            continue

        size = via.GetDrillValue()
        if size != drill_size.x:
            raise RuntimeError('Invalid via size: %s' % size)

    return board


def plot(output_dir, board):
    dir = os.fspath(output_dir.resolve())

    controller = pcbnew.PLOT_CONTROLLER(board)
    options = controller.GetPlotOptions()

    options.SetAutoScale(False)
    options.SetCreateGerberJobFile(False)
    options.SetDrillMarksType(pcbnew.PCB_PLOT_PARAMS.NO_DRILL_SHAPE);
    options.SetExcludeEdgeLayer(True)
    options.SetLineWidth(pcbnew.FromMM(0.1))
    options.SetMirror(False)
    options.SetOutputDirectory(dir)
    options.SetPlotFrameRef(False)
    options.SetScale(1.0)
    options.SetSkipPlotNPTH_Pads(True)
    options.SetUseAuxOrigin(True)
    options.SetUseGerberAttributes(False)
    options.SetUseGerberProtelExtensions(False)

    controller.SetLayer(pcbnew.B_Cu)
    controller.OpenPlotfile("B_Cu", pcbnew.PLOT_FORMAT_GERBER, "Bottom Layer")
    controller.PlotLayer()

    controller.SetLayer(pcbnew.Edge_Cuts)
    controller.OpenPlotfile("Edge_Cuts", pcbnew.PLOT_FORMAT_GERBER, "Outline")
    controller.PlotLayer()

    exc = pcbnew.EXCELLON_WRITER(board)
    exc.SetOptions(False, False, board.GetAuxOrigin(), False)
    exc.SetFormat(True)
    exc.CreateDrillandMapFilesSet(dir, True, False);

    controller.ClosePlot()

    new_pcb = output_dir.joinpath(pathlib.Path(board.GetFileName()).name)
    pcbnew.SaveBoard(os.fspath(new_pcb.resolve()), board)


if __name__ == '__main__':
    args = parser.parse_args()
    plot(args.output_dir, patch_board(args.kicad_pcb, args.tool_dia))
