#!/usr/bin/env python3

import argparse
import os
import pathlib
import shlex
import sys

import pcbnew


def tool_dia(val):
    rv = {}

    for kv in [i.strip() for i in val.split(',')]:
        kvt = [i.strip() for i in kv.split('=')]
        if len(kvt) == 1:
            rv[-1] = int(kvt[0])
        elif len(kvt) == 2:
            rv[int(kvt[0])] = int(kvt[1])
        else:
            raise ValueError(val)

    return rv


def grow_pads_skip(val):
    if len(val) == 0:
        return []
    return [i.strip() for i in val.split(',')]


parser = argparse.ArgumentParser(description='Export Gerber files from a Kicad '
                                 'PCB, for usage with CNC milling machines')
parser.add_argument('--list-pads', action='store_true',
                    help='list pad sizes and exit')
parser.add_argument('--tool-dia', metavar='DIA[,DIA=PAD_HOLE,...]', type=tool_dia,
                    help='drill bit diameter (in um, default: 800)', default="800")
parser.add_argument('--tool-dia-tolerance', metavar='PERC', type=int,
                    help='skip resizing any pads bigger or smaller than PERC percents '
                    'of the drill bit diameter (default 50)', default=50)
parser.add_argument('--keep-pad-size-ratio', action='store_true',
                    help='resize pads to keep size ratio when patching drill holes')
parser.add_argument('--grow-pads', metavar='PERC', type=int,
                    help='grow pads by the given percentage (default: 0, disabled)',
                    default=0)
parser.add_argument('--grow-pads-skip', metavar='REF[,REF...]', type=grow_pads_skip,
                    help='reference of pads to skip when growing', default='')
parser.add_argument('--output-dir', metavar='DIR', type=pathlib.Path,
                    help='output directory (default: ./gerber)', default='./gerber')
parser.add_argument('kicad_pcb', metavar='KICAD_PCB', type=pathlib.Path,
                    help='a Kicad PCB file')


def get_pad_reference(pad):
    mod = pad
    while mod is not None and mod.GetClass() != "MODULE":
        mod = mod.GetParent()

    if mod is None:
        raise RuntimeError('unable to find pad reference: %s' % pad)

    return mod.GetReference()


def patch_board(fileobj, tool_dia_map, tool_dia_tolerance, keep_pad_size_ratio,
                grow_pads, grow_pads_skip):
    board = pcbnew.LoadBoard(os.fspath(fileobj.resolve()))

    # iterate over pads
    for pad in board.GetPads():
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_STANDARD:
            continue

        orig_drill_size = pad.GetDrillSize()

        tool_dia = tool_dia_map.get(max(orig_drill_size) / 1000)
        if tool_dia is None:
            tool_dia = tool_dia_map.get(-1)
        if tool_dia is None:
            print('skipping pad without tool diameter: %s' % orig_drill_size)
            continue

        orig_drill_dia_max = tool_dia * (100 + tool_dia_tolerance) * 10
        orig_drill_dia_min = tool_dia * (100 - tool_dia_tolerance) * 10
        drill_size = pcbnew.wxSize(tool_dia * 1000, tool_dia * 1000)

        size = pad.GetSize()

        if orig_drill_size.x > orig_drill_dia_max or \
           orig_drill_size.x < orig_drill_dia_min or \
           orig_drill_size.y > orig_drill_dia_max or \
           orig_drill_size.y < orig_drill_dia_min:
            print('skipping drill hole resize: %s' % pad.GetDrillSize())

        else:
            # keep pad size ratio
            if keep_pad_size_ratio:
                ratio_x = drill_size.x / orig_drill_size.x
                ratio_y = drill_size.y / orig_drill_size.y
                size = pcbnew.wxSize(size.x * ratio_x, size.y * ratio_y)

            # validate drill size
            if drill_size.x > size.x or drill_size.y > size.y:
                raise RuntimeError('Invalid pad size: %s' % size)

            # fix drill size
            pad.SetDrillSize(drill_size)
            pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)

        # grow pad size
        if grow_pads:
            if get_pad_reference(pad) in grow_pads_skip:
                print('skipping pad that should not be grown: %s' % orig_drill_size)
            else:
                size = pcbnew.wxSize(size.x * (100 + grow_pads) / 100,
                                     size.y * (100 + grow_pads) / 100)
        pad.SetSize(size)

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

    with open(output_dir.joinpath('command.txt').resolve(), 'w') as fp:
        print(' '.join([shlex.quote(i) for i in sys.argv]), file=fp)


def list_pads(fileobj):
    board = pcbnew.LoadBoard(os.fspath(fileobj.resolve()))

    sizes = {}

    for pad in board.GetPads():
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_STANDARD:
            continue

        s = sizes.setdefault(max(pad.GetDrillSize()), set())
        s.add(get_pad_reference(pad))

    for size in sorted(sizes):
        print('%d: %s' % (size / 1000, ', '.join(sorted(sizes[size]))))


if __name__ == '__main__':
    args = parser.parse_args()

    if args.list_pads:
        list_pads(args.kicad_pcb)
    else:
        plot(args.output_dir, patch_board(args.kicad_pcb, args.tool_dia,
                                          args.tool_dia_tolerance,
                                          args.keep_pad_size_ratio,
                                          args.grow_pads, args.grow_pads_skip))
